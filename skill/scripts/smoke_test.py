#!/usr/bin/env python3
"""冒烟测试 —— 一键校验 MCP 连接与只读工具可用性。

只做**只读**检查，不会领券、不会下单、不写入任何数据。

用法:
    python smoke_test.py                 # 联机跑无参只读工具
    python smoke_test.py --offline       # 只检查环境与文件，不联网
    python smoke_test.py --tools now-time-info query-my-account
    python smoke_test.py --json          # 机器可读输出

检查内容:
    1. 环境变量 MCD_MCP_TOKEN 是否就绪（只报「已设置/未设置」，绝不打印值）
    2. 关键文件是否齐全（SKILL.md / ledger.py / mcp_call.py / references 等）
    3. ledger.py 能否正常建库并出报告（本地自检）
    4. 逐个调用只读工具，判断响应格式（JSON 包裹 vs Markdown 文本）

范围说明:
    本脚本只自动测**无需参数**的只读工具。
    另有 4 个只读工具需要门店上下文（storeCode 等），无法在冒烟测试中盲调，
    已通过真实调用单独验证（2026-10-11），见 references/tools-ordering.md：
        query-nearby-stores / query-meals / query-store-coupons / calculate-price
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)

# 已实测的「无参」只读工具（写操作如 auto-bind-coupons / create-order 一律不测）
# 注：需门店上下文的 4 个工具见模块 docstring「范围说明」，不列入此处以免盲调报错。
READ_ONLY_TOOLS = [
    "now-time-info",
    "campaign-calendar",
    "available-coupons",
    "query-my-coupons",
    "query-my-account",
    "delivery-query-addresses",
]

REQUIRED_FILES = [
    "SKILL.md",
    "scripts/mcp_call.py",
    "scripts/ledger.py",
    "scripts/smoke_test.py",
    "references/tools.md",
    "references/tools-meta.md",
    "references/tools-coupon.md",
    "references/tools-ordering.md",
    "references/tools-delivery.md",
    "references/flows.md",
    "references/pricing-rules.md",
    "references/errors-faq.md",
    "references/compliance.md",
    "assets/report-template.html",
    "assets/report-sample.html",
]


def _ok(v):
    return "✅" if v else "❌"


def check_env():
    token = os.environ.get("MCD_MCP_TOKEN", "")
    return {"token_set": bool(token), "token_len": len(token)}


def check_files():
    rows = []
    for rel in REQUIRED_FILES:
        p = os.path.join(SKILL_ROOT, rel)
        exists = os.path.isfile(p)
        size = os.path.getsize(p) if exists else 0
        rows.append({"file": rel, "exists": exists, "size": size, "nonempty": size > 0})
    return rows


def check_ledger():
    """本地自检：临时库 init + report 能否跑通。"""
    tmp = os.path.join(SKILL_ROOT, "data", "_smoke_test.db")
    py = sys.executable
    ledger = os.path.join(HERE, "ledger.py")
    try:
        r1 = subprocess.run([py, ledger, "init", "--db", tmp],
                            capture_output=True, text=True, timeout=30)
        r2 = subprocess.run([py, ledger, "report", "--db", tmp],
                            capture_output=True, text=True, timeout=30)
        ok = r1.returncode == 0 and r2.returncode == 0
        return {"ok": ok, "report_has_saved": "累计省下" in (r2.stdout or "")}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _extract_text(result):
    """从 MCP tools/call 结果中取出文本载荷。"""
    if not isinstance(result, dict):
        return ""
    content = result.get("content")
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        if parts:
            return "\n".join(parts)
    if "data" in result or "success" in result:
        return json.dumps(result, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)


def detect_shape(text):
    """判断响应格式：JSON 包裹 / Markdown 文本 / 空。"""
    s = (text or "").strip()
    if not s:
        return "empty"
    if s.startswith("{"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and ("success" in obj or "data" in obj):
                return "json"
            return "json"
        except json.JSONDecodeError:
            pass
    return "markdown"


def call_tool(tool, args=None):
    sys.path.insert(0, HERE)
    import mcp_call  # noqa: E402
    res = mcp_call.call(tool, args or {})
    text = _extract_text(res)
    shape = detect_shape(text)
    error = None
    if isinstance(res, dict) and res.get("ok") is False:
        error = res.get("message") or res.get("error_code")
    return {"tool": tool, "shape": shape,
            "chars": len(text), "error": error,
            "preview": (text or "")[:80].replace("\n", " ")}


def main():
    p = argparse.ArgumentParser(description="麦当劳 MCP 只读冒烟测试")
    p.add_argument("--offline", action="store_true", help="跳过联网，仅做本地自检")
    p.add_argument("--tools", nargs="*", default=None, help="指定要测的工具（默认全部无参只读工具）")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")
    a = p.parse_args()

    report = {"env": check_env(), "files": check_files(), "ledger": check_ledger()}
    tools = a.tools or READ_ONLY_TOOLS

    if not a.offline and report["env"]["token_set"]:
        report["tools"] = [call_tool(t) for t in tools]
    elif not a.offline:
        report["tools"] = []
        report["skip_reason"] = "未设置 MCD_MCP_TOKEN，已跳过联网检查（本地自检已执行）"
    else:
        report["tools"] = []
        report["skip_reason"] = "offline 模式，已跳过联网检查"

    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    # 人类可读
    e = report["env"]
    print(f"{_ok(e['token_set'])} 环境变量 MCD_MCP_TOKEN：{'已设置（长度 %d）' % e['token_len'] if e['token_set'] else '未设置（联网检查将跳过）'}")
    print()
    print("关键文件：")
    for f in report["files"]:
        print(f"  {_ok(f['nonempty'])} {f['file']:<32} {f['size']} bytes")
    print()
    lg = report["ledger"]
    print(f"{_ok(lg.get('ok'))} ledger.py 本地自检：{'通过' if lg.get('ok') else lg.get('error', '失败')}")
    if lg.get("ok"):
        print(f"    └ 报告含「累计省下」：{'是' if lg.get('report_has_saved') else '否'}")
    print()
    if report.get("tools"):
        print("只读工具调用：")
        for t in report["tools"]:
            flag = _ok(not t["error"])
            print(f"  {flag} {t['tool']:<20} 格式={t['shape']:<9} {t['chars']:>5} 字符"
                  + (f"  错误={t['error']}" if t["error"] else ""))
    else:
        print(f"ℹ️  {report.get('skip_reason', '')}")
    print()
    passed = (
        report["ledger"].get("ok")
        and all(f["nonempty"] for f in report["files"])
        and all(not t["error"] for t in report.get("tools", []))
    )
    print("结果：", "🎉 全部通过" if passed else "⚠️ 存在失败项，见上")


if __name__ == "__main__":
    main()
