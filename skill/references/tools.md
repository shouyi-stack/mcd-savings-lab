# 工具总览（tools · 索引）

> 本文件是**工具文档的索引**：响应格式分流总表 + 工具全景 + 通用注意点。
> 字段级明细已按业务域拆到子文件，见下方**导航**。
> 原则：**只记真实调用验证过的字段**；未实测的标 ⬜，不写死假设。
> 首次记录：2026-10-10 ｜ 最后更新：2026-10-11（按业务域拆分）

---

## 一、两种响应格式（最重要）

实测发现，麦当劳 MCP 的工具返回**两种格式**，解析逻辑必须区分处理：

| 格式 | 特征 | 已实测工具 |
|---|---|---|
| **JSON 包裹** | `{success, code, message, datetime, traceId, data}` | `now-time-info`、`query-my-account`、`query-nearby-stores`、`query-meals`、`query-store-coupons`、`calculate-price`、`delivery-query-addresses` |
| **Markdown 文本** | 纯 Markdown（含标题/列表，图片为内嵌 `<img>` 标签） | `campaign-calendar`、`available-coupons`、`query-my-coupons` |

> 📌 规律：**营销 / 券包类**工具返回 Markdown（给人看）；**点餐 / 算价类**工具返回 JSON（给机器算）。
> 顶层统一带 `datetime`（服务器时间，`yyyy-MM-dd HH:mm:ss`）与 `traceId`。
> `traceId` 仅用于排障，**绝不写入任何产物**。

> 📌 含义：对 Markdown 类工具，脚本/工作流**不能假设有 JSON 字段**；需按文本渲染或正则提取。

---

## 二、工具全景表

编号与子文件内的章节号一致，便于交叉查找。

| # | 工具 | 业务域 | 响应格式 | 实测状态 |
|---|---|---|---|---|
| 1 | `now-time-info` | 基础（时间） | JSON | ✅ 2026-10-10 |
| 2 | `query-my-account` | 账户（积分） | JSON | ✅ 2026-10-10 |
| 3 | `campaign-calendar` | 营销 | Markdown | ✅ 2026-10-10 |
| 4 | `available-coupons` | 券（可领） | Markdown | ✅ 2026-10-10 |
| 5 | `query-my-coupons` | 券（已拥有） | Markdown | ✅ 2026-10-10 |
| 6 | `query-nearby-stores` | 点餐（到店定位） | JSON | ✅ 2026-10-11 |
| 7 | `query-meals` | 点餐（菜单） | JSON | ✅ 2026-10-11 |
| 8 | `query-store-coupons` | 点餐（门店券） | JSON | ✅ 2026-10-11 |
| 9 | `calculate-price` | 算价 | JSON | ✅ 2026-10-11 |
| 10 | `delivery-query-addresses` | 外送（地址） | JSON | ✅ 2026-10-11 |
| 11 | `delivery-query-stores` | 外送（门店） | JSON | ⚠️ 部分（仅失败路径） |
| 12 | `delivery-create-address` | 外送（建地址） | ⬜ | ⬜ 未实测（写操作） |
| — | `auto-bind-coupons` | 券（领券） | ⬜ | ⬜ 未实测（**写操作**） |

> ✅ = 真实调用验证过；⚠️ = 部分验证；⬜ = 未实测。
> **写操作**（`auto-bind-coupons`、`delivery-create-address`、下单类）一律**先确认后调用**。

---

## 三、导航（按业务域）

| 子文件 | 收录工具 | 内容 |
|---|---|---|
| `tools-meta.md` | `now-time-info`、`query-my-account` | 基础与账户：时间上下文、积分账户 |
| `tools-coupon.md` | `campaign-calendar`、`available-coupons`、`query-my-coupons` | 券与营销（均 Markdown）+ 券 ID 从哪来 |
| `tools-ordering.md` | `query-nearby-stores`、`query-meals`、`query-store-coupons`、`calculate-price` | 到店「定位 → 菜单 → 券 → 算价」核心链路 |
| `tools-delivery.md` | `delivery-query-addresses`、`delivery-query-stores`、`delivery-create-address` | 外送链路 + 外送专属错误码 |
| `flows.md` | — | 四条标准链路的正常路径 + 失败路径 |
| `pricing-rules.md` | — | 算价规则、金额单位、同名不同义坑点 |
| `errors-faq.md` | — | 错误码速查 + 常见问题 |
| `compliance.md` | — | 合规红线与提交前自查清单 |

---

## 四、通用注意点（所有工具共享）

1. **限流**：服务端 **600 次 / 分钟 / Token**。批量 / 循环调用一律**串行**，间隔 **≥150ms**（`mcp_call.py` 已内置节流）。
2. **Token**：只从环境变量 `MCD_MCP_TOKEN` 读取，**禁止写入文件或日志**。
3. **隐私**：`accountId`、券明细、手机号、真实地址等个人信息**只做本地分析**；不入公开产物、不打日志。
4. **写操作需确认**：`auto-bind-coupons`、`delivery-create-address`、下单类操作，必须先复述清单、待用户确认。
5. **降级优先**：任何失败都给出**可用的替代路径**，而非只说「不支持」。
6. **`traceId` 不入产物**：仅用于排障。
