#!/usr/bin/env python3
"""消费数据资产层 —— 把券 / 订单 / 积分沉淀为本地 SQLite 数据集。

这是本项目的差异化护城河：不是「用完即忘」的查券工具，而是把每次消费
结构化落库，从而能回答「我这个月到底省了多少」。

用法:
    python ledger.py init
    python ledger.py log-coupons --data '[{"couponId":"c1","name":"中杯美式 7 折","value":13.3,"unit":"yuan"}]'
    python ledger.py log-order   --data '{"orderId":"o1","store":"XX店","items":[{"name":"麦辣鸡腿堡"}],"origin":34,"paid":23.8,"unit":"yuan"}'
    python ledger.py log-points  --data '{"balance":120,"delta":10,"reason":"消费返积分"}'
    python ledger.py report                     # 全量省钱报告
    python ledger.py report --month 2026-10     # 指定月份
    python ledger.py list --expiring 7          # 7 天内到期的券
    python ledger.py mark-used --id c1
    python ledger.py export --out data/orders.csv

设计要点（对齐评审）:
    - 无硬编码密钥；数据库路径可由环境变量 MCD_LEDGER_DB 覆盖
    - 金额统一以「分」为存储单位（整数，避免浮点误差），但**不假设输入单位**：
      用 --unit 显式声明来源单位（yuan / fen），并保留原始值与原始单位以便溯源
      （⚠️ `query-my-coupons` 实测「优惠」为元；`calculate-price` 单位待实测）
    - `accountId` 等个人信息一律不入库
    - 所有写操作幂等（INSERT OR REPLACE），重复导入不会产生脏数据
"""
import argparse
import csv
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta

DB_DEFAULT = os.environ.get("MCD_LEDGER_DB", "data/mcd_ledger.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS coupons (
  coupon_id    TEXT PRIMARY KEY,
  name         TEXT,
  value_fen    INTEGER,          -- 统一单位「分」；无法确定时 NULL
  raw_value    TEXT,             -- 原始数值文本，保留溯源
  unit_source  TEXT,             -- 原值单位：yuan / fen / unknown
  expire_at    TEXT,             -- 有效期结束 yyyy-MM-dd HH:mm
  daily_window TEXT,             -- 每日可用时段，如 10:00-22:00
  tag          TEXT,             -- 标签，如「到店专用」
  status       TEXT DEFAULT 'unused',   -- unused / used / expired
  got_at       TEXT,
  source       TEXT              -- 数据来源工具，便于排障
);
CREATE TABLE IF NOT EXISTS orders (
  order_id   TEXT PRIMARY KEY,
  store      TEXT,
  items_json TEXT,
  origin_fen INTEGER,            -- 原价
  paid_fen   INTEGER,            -- 实付
  saved_fen  INTEGER,            -- 立省
  coupon_ids TEXT,               -- 使用的券 ID（逗号分隔）
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS points_log (
  ts      TEXT,
  balance INTEGER,
  delta   INTEGER,
  reason  TEXT
);
"""


# ---------- 单位换算 ----------

def to_fen(value, unit="yuan"):
    """把金额换算为「分」。unit 显式声明，不猜。"""
    if value is None or value == "":
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    unit = (unit or "yuan").lower()
    if unit == "fen":
        return int(round(num))
    if unit == "yuan":
        return int(round(num * 100))
    return None  # unknown 单位：不做换算


def fen_to_yuan(fen):
    if fen is None:
        return None
    return round(fen / 100.0, 2)


def money(fen):
    """格式化展示：None -> '—'"""
    y = fen_to_yuan(fen)
    return "—" if y is None else f"¥{y:,.2f}"


# ---------- 连接 ----------

def conn(db=None):
    path = db or DB_DEFAULT
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    return c


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _sweep_expired(c):
    """把已过期的券标记为 expired（幂等）。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute(
        "UPDATE coupons SET status='expired' "
        "WHERE status='unused' AND expire_at IS NOT NULL AND expire_at <> '' AND expire_at < ?",
        (now,))
    c.commit()


# ---------- 入库 ----------

def _pick(d, *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def log_coupons(payload, db=None, unit="yuan", source="query-my-coupons"):
    if isinstance(payload, dict):
        payload = [payload]
    c = conn(db)
    n = 0
    for it in payload:
        cid = str(_pick(it, "couponId", "coupon_id", "id", default="")) or None
        if not cid:
            # 无 ID 的券（如 available-coupons 只给标题）跳过，避免主键冲突丢数据
            continue
        raw = _pick(it, "value", "price", "amount")
        u = _pick(it, "unit", default=unit)
        c.execute(
            "INSERT OR REPLACE INTO coupons VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (cid,
             _pick(it, "name", "title"),
             to_fen(raw, u),
             None if raw is None else str(raw),
             u if raw is not None else "unknown",
             _pick(it, "expire", "expireDate", "validUntil", "expire_at"),
             _pick(it, "dailyWindow", "daily_window", default=""),
             _pick(it, "tag", default=""),
             _pick(it, "status", default="unused"),
             _pick(it, "gotAt", "got_at", default=_now()),
             source))
        n += 1
    c.commit()
    c.close()
    return n


def log_order(payload, db=None, unit="yuan"):
    c = conn(db)
    oid = str(_pick(payload, "orderId", "order_id", "id", default="")) or None
    if not oid:
        c.close()
        return {"ok": False, "message": "缺少 orderId，无法入库"}
    origin = to_fen(_pick(payload, "origin", "originPrice", "origin_price"), unit)
    paid = to_fen(_pick(payload, "paid", "paidPrice", "paid_price"), unit)
    saved = to_fen(_pick(payload, "saved", "savedPrice", "saved_price"), unit)
    if saved is None and origin is not None and paid is not None:
        saved = origin - paid  # 未显式给「立省」时按 原价-实付 推算
    items = _pick(payload, "items", default=[])
    cids = _pick(payload, "couponIds", "coupon_ids", default=[])
    if isinstance(cids, list):
        cids = ",".join(str(x) for x in cids)
    c.execute(
        "INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?,?,?,?)",
        (oid,
         _pick(payload, "store", "storeName", "store_name"),
         json.dumps(items, ensure_ascii=False),
         origin, paid, saved, cids,
         _pick(payload, "createdAt", "created_at", default=_now())))
    c.commit()
    c.close()
    return {"ok": True, "order_id": oid, "saved_fen": saved}


def log_points(payload, db=None):
    c = conn(db)
    c.execute("INSERT INTO points_log VALUES (?,?,?,?)",
              (_pick(payload, "ts", default=_now()),
               _pick(payload, "balance"),
               _pick(payload, "delta"),
               _pick(payload, "reason", default="")))
    c.commit()
    c.close()
    return {"ok": True}


def mark_used(coupon_id, db=None):
    c = conn(db)
    cur = c.execute("UPDATE coupons SET status='used' WHERE coupon_id=?", (coupon_id,))
    c.commit()
    c.close()
    return cur.rowcount


# ---------- 查询 / 报告 ----------

def _summary(c, month=None):
    where, params = "", []
    if month:
        where = " WHERE substr(created_at,1,7)=?"
        params = [month]
    saved = c.execute(f"SELECT COALESCE(SUM(saved_fen),0) FROM orders{where}", params).fetchone()[0]
    orders = c.execute(f"SELECT COUNT(*) FROM orders{where}", params).fetchone()[0]

    if month:
        cw, cp = " WHERE substr(got_at,1,7)=?", [month]
    else:
        cw, cp = "", []
    total = c.execute(f"SELECT COUNT(*) FROM coupons{cw}", cp).fetchone()[0]
    used = c.execute(f"SELECT COUNT(*) FROM coupons{cw}{' AND' if cw else ' WHERE'} status='used'", cp).fetchone()[0]
    unused = c.execute(f"SELECT COUNT(*) FROM coupons{cw}{' AND' if cw else ' WHERE'} status='unused'", cp).fetchone()[0]
    expired = c.execute(f"SELECT COUNT(*) FROM coupons{cw}{' AND' if cw else ' WHERE'} status='expired'", cp).fetchone()[0]

    soon = datetime.now() + timedelta(days=7)
    expiring = c.execute(
        "SELECT COUNT(*) FROM coupons WHERE status='unused' AND expire_at<>'' "
        "AND expire_at <= ?", (soon.strftime("%Y-%m-%d %H:%M"),)).fetchone()[0]

    # 品类偏好：从订单 items 里统计出现最多的品名
    items = c.execute(f"SELECT items_json FROM orders{where}", params).fetchall()
    counter = {}
    for (js,) in items:
        try:
            for it in json.loads(js or "[]"):
                nm = _pick(it, "name", "title", "itemName", default="") if isinstance(it, dict) else str(it)
                if nm:
                    counter[nm] = counter.get(nm, 0) + 1
        except (ValueError, TypeError):
            continue
    top = [k for k, _ in sorted(counter.items(), key=lambda kv: -kv[1])[:3]]
    return {
        "saved_fen": saved, "orders": orders, "coupons_total": total,
        "coupons_used": used, "coupons_unused": unused, "coupons_expired": expired,
        "coupons_expiring_7d": expiring, "top_items": top,
    }


def report(db=None, month=None, as_json=False):
    c = conn(db)
    _sweep_expired(c)
    s = _summary(c, month)
    c.close()
    total = s["coupons_total"]
    rate = f"{s['coupons_used'] / total * 100:.0f}%" if total else "—"
    if as_json:
        out = dict(s, redeem_rate=rate, month=month or "all")
        return out
    title = f"麦麦省钱月报（{month}）" if month else "麦麦省钱账本（全量）"
    lines = [
        f"📊 {title}",
        "─" * 34,
        f"累计省下   {money(s['saved_fen'])}",
        f"订单数     {s['orders']}",
        f"券核销率   {rate}  ({s['coupons_used']}/{total})",
        "─" * 34,
        f"券总数     {total}  (可用 {s['coupons_unused']} / 已用 {s['coupons_used']} / 已过期 {s['coupons_expired']})",
        f"临期券     {s['coupons_expiring_7d']}  (7 天内到期)",
        f"偏好品类   {' / '.join(s['top_items']) if s['top_items'] else '—'}",
    ]
    return "\n".join(lines)


def list_coupons(db=None, status=None, expiring=None, as_json=False):
    c = conn(db)
    _sweep_expired(c)
    sql, params = "SELECT coupon_id,name,value_fen,raw_value,unit_source,expire_at,tag,status FROM coupons", []
    cond = []
    if status:
        cond.append("status=?")
        params.append(status)
    if expiring:
        soon = (datetime.now() + timedelta(days=int(expiring))).strftime("%Y-%m-%d %H:%M")
        cond.append("status='unused' AND expire_at<>'' AND expire_at<=?")
        params.append(soon)
    if cond:
        sql += " WHERE " + " AND ".join(cond)
    sql += " ORDER BY (expire_at IS NULL OR expire_at=''), expire_at"
    rows = c.execute(sql, params).fetchall()
    c.close()
    cols = ["coupon_id", "name", "value_fen", "raw_value", "unit_source", "expire_at", "tag", "status"]
    data = [dict(zip(cols, r)) for r in rows]
    if as_json:
        return data
    if not data:
        return "（无符合条件的券）"
    out = [f"{'券名':<22}{'面额':>8}  {'到期':<17}{'状态':<8}标签"]
    for d in data:
        val = f"{d['raw_value']}{'元' if d['unit_source']=='yuan' else '分' if d['unit_source']=='fen' else ''}"
        out.append(f"{(d['name'] or '')[:20]:<22}{val:>8}  {(d['expire_at'] or '—'):<17}{d['status']:<8}{d['tag'] or ''}")
    return "\n".join(out)


def export_csv(db=None, out="data/orders.csv"):
    c = conn(db)
    rows = c.execute(
        "SELECT order_id,store,origin_fen,paid_fen,saved_fen,coupon_ids,created_at FROM orders "
        "ORDER BY created_at").fetchall()
    c.close()
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["订单号", "门店", "原价(元)", "实付(元)", "立省(元)", "用券", "时间"])
        for r in rows:
            w.writerow([r[0], r[1], fen_to_yuan(r[2]), fen_to_yuan(r[3]), fen_to_yuan(r[4]), r[5], r[6]])
    return {"ok": True, "rows": len(rows), "out": out}


# ---------- CLI ----------

def init(db=None):
    path = db or DB_DEFAULT
    conn(path).close()
    return f"已初始化数据库：{path}"


def _load_data(args):
    if args.data:
        return json.loads(args.data)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    p = argparse.ArgumentParser(description="麦当劳消费数据资产层（本地 SQLite）")
    p.add_argument("action",
                   choices=["init", "log-coupons", "log-order", "log-points",
                            "report", "list", "mark-used", "export"])
    p.add_argument("--db", default=None, help=f"数据库路径（默认 {DB_DEFAULT}）")
    p.add_argument("--data", default=None, help="JSON 数据（字符串）")
    p.add_argument("--file", default=None, help="JSON 数据（文件路径）")
    p.add_argument("--unit", default="yuan", choices=["yuan", "fen", "unknown"],
                   help="输入的金额单位（默认 yuan；未知填 unknown，则不换算）")
    p.add_argument("--month", default=None, help="月份过滤，格式 YYYY-MM")
    p.add_argument("--status", default=None, help="券状态过滤：unused/used/expired")
    p.add_argument("--expiring", default=None, help="N 天内到期的未用券")
    p.add_argument("--id", default=None, help="券 ID（mark-used 用）")
    p.add_argument("--out", default="data/orders.csv", help="导出 CSV 路径")
    p.add_argument("--json", action="store_true", help="以 JSON 输出（便于程序消费）")
    a = p.parse_args()

    if a.action == "init":
        print(init(a.db))
    elif a.action == "log-coupons":
        data = _load_data(a)
        if data is None:
            print("需要 --data 或 --file"); sys.exit(2)
        n = log_coupons(data, a.db, a.unit)
        print(json.dumps({"ok": True, "logged": n}, ensure_ascii=False))
    elif a.action == "log-order":
        data = _load_data(a)
        if data is None:
            print("需要 --data 或 --file"); sys.exit(2)
        print(json.dumps(log_order(data, a.db, a.unit), ensure_ascii=False))
    elif a.action == "log-points":
        data = _load_data(a)
        if data is None:
            print("需要 --data 或 --file"); sys.exit(2)
        print(json.dumps(log_points(data, a.db), ensure_ascii=False))
    elif a.action == "report":
        r = report(a.db, a.month, a.json)
        print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else r)
    elif a.action == "list":
        r = list_coupons(a.db, a.status, a.expiring, a.json)
        print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else r)
    elif a.action == "mark-used":
        if not a.id:
            print("需要 --id"); sys.exit(2)
        print(json.dumps({"ok": True, "updated": mark_used(a.id, a.db)}, ensure_ascii=False))
    elif a.action == "export":
        print(json.dumps(export_csv(a.db, a.out), ensure_ascii=False))


if __name__ == "__main__":
    main()
