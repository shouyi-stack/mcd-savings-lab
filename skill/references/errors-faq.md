# 错误码与常见问题（errors-faq）

> 排障速查：先查**错误码表**，再看**FAQ**。
> 原则：只列**真实遇到过**的错误码；未遇到的标「⬜ 未遇到」。
> 最后更新：2026-10-11

---

## 一、错误码速查

### 1. HTTP / 传输层

| 码 | 含义 | 处理 |
|---|---|---|
| `401` | Token 无效或已过期 | 提示用户到 <https://open.mcd.cn/mcp> 控制台**重新激活**并更新 `MCD_MCP_TOKEN`，**不报错退出** |
| `403` | 鉴权失败 | 检查 `Authorization` 请求头是否为 `Bearer <token>` 格式 |
| `429` | 触发限流（**600 次 / 分钟 / Token**） | 暂停并退避重试（间隔 ≥150ms），提示用户稍后再试 |
| — | 网络不可达 / 响应解析失败 | 转友好提示，不抛栈；建议稍后重试 |

### 2. 业务错误码（响应体 `code` 字段）

| 码 | message | 触发场景 | 处理 |
|---|---|---|---|
| `200` | 请求成功 | 正常 | — |
| `600020` | 配送地址不存在 | `delivery-query-stores` 传入无效 / 非本账号的 `addressId` | 回到 `delivery-query-addresses` 重新取 `addressId` |
| `600048` | 外送场景下，beType=2/5/6 时必传 beCode | 外送场景漏传 `beCode` | 先走 `delivery-query-stores` 取 `beCode` |
| `600050` | 收藏餐厅列表为空，请您提供城市+关键词进行搜索 | `query-nearby-stores` 用 `searchType=1`（收藏）且无收藏 | 自动降级 `searchType=2` + 追问城市 / 地标 |

> 业务错误码均为**已实测**（2026-10-10 ~ 10-11）。详见 `tools-ordering.md` / `tools-delivery.md`。

### 3. 降级原则

> 任何失败都**给出可用的替代路径**，而不是只说「不支持」。
> 例：收藏为空 → 降级搜索；多组合 429 → 降级为单组合试算并在回复中说明原因。

---

## 二、常见问题（FAQ）

**1. 券领了，下单却用不了？**
`query-my-coupons` 只返回「**你拥有的**券」，**不校验门店 / 渠道**。下单前要用 `query-store-coupons` 查**当前门店实际可用**的券。

**2. 为什么我的积分是 0？**
`query-my-account` 返回可用 / 累计积分；新号或未消费常为 `0`，可直接如实播报，不必「解释成异常」。

**3. 算价需要先准备什么？**
到店自取（`beType=1`）只需 `storeCode`（来自 `query-nearby-stores`）。
**外送**（`orderType=2`）还需先有**配送地址** → `delivery-query-addresses` 取 `addressId` → `delivery-query-stores` 取 `beCode`。没有地址就先 `delivery-create-address`（**写操作，需确认**）。

**4. `available-coupons` 里有券，但拿不到券 ID 和面额？**
该工具只返回**标题 / 状态 / 图片**。面额相关走 `query-my-coupons`（给「用券后价格」，**不是面额**）；券 ID / 券码**只有** `query-store-coupons` 给。

**5. 菜单价和算价对不上？**
两者**单位不同**：菜单价是**元**（`"33.5"`），算价是**分**（`3350`）——差 100 倍。比对前先统一到分。详见 `pricing-rules.md` §1。

**6. 「省了多少」怎么算才对？**
- 「比单点省多少」→ 用**菜单划线价** `query-meals.originalPrice`（元）− 实付。
- 「券再省多少」→ 用**算价的 `discount`**（分）。
- ⚠️ 算价的 `originalPrice` 是「叠券前小计」，**不是**划线价；`discount` **只反映券的优惠，不含套餐折扣**。

**7. 我的消费数据会被上传吗？**
不会。数据落在**本地** `data/`（已 gitignore），仓库不含个人信息；`accountId` 一律不入库。

**8. 能帮我直接付款吗？**
不能。**仅生成订单，支付由用户本人完成**。领券 / 下单等写操作都会先复述清单，等你确认。

---

## 相关文件

- 工具总览 → `tools.md`
- 各工具字段与实测状态 → `tools-meta.md` / `tools-coupon.md` / `tools-ordering.md` / `tools-delivery.md`
- 标准链路与失败路径 → `flows.md`
- 算价规则与单位 → `pricing-rules.md`
- 合规红线 → `compliance.md`
