# MCP 集成说明

## 1. 使用的 MCP Server

| 项目 | 值 |
|---|---|
| Server 名称 | 麦当劳中国官方 MCP Server（`mcd-mcp`） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 认证方式 | `Authorization: Bearer <MCP_TOKEN>` |
| 限流 | 600 次 / 分钟 / Token |

## 2. 实际调用的 Tool

> 本表随开发进度更新：截至 **2026-10-11** 已实测 10 个只读工具——`now-time-info`、`campaign-calendar`、
> `available-coupons`、`query-my-coupons`、`query-my-account`、`query-nearby-stores`、`query-meals`、
> `query-store-coupons`、`calculate-price`、`delivery-query-addresses`（均只读）；其余工具逐项验证后改为 ✅，
> 未跑通的标 ❌ 并说明原因。字段级明细与响应格式（JSON / Markdown）见 `skill/references/tools.md`。

| Tool | 用途 | 是否实测 |
|---|---|---|
| `now-time-info` | 获取当前时间上下文 | ✅ 实测（2026-10-10） |
| `campaign-calendar` | 当月营销活动日历 | ✅ 实测（2026-10-10，返回 Markdown） |
| `available-coupons` | 查询可领取券 | ✅ 实测（2026-10-10，返回 Markdown） |
| `auto-bind-coupons` | 一键领取全部券 | ⬜ 待实测（写操作，需确认） |
| `query-my-coupons` | 查询我的券包 | ✅ 实测（2026-10-10，返回 Markdown） |
| `query-my-account` | 查询积分账户 | ✅ 实测（2026-10-10） |
| `query-nearby-stores` | 查询到店门店（取 `storeCode`） | ✅ 实测（2026-10-11，5 家门店） |
| `delivery-query-addresses` | 查询配送地址 | ✅ 实测（2026-10-11，仅地址，**不含 storeCode**） |
| `query-meals` | 查询门店菜单 | ✅ 实测（2026-10-11，15 分类 / 约 130 品） |
| `query-store-coupons` | 查询门店可用券（**含券 ID/券码**） | ✅ 实测（2026-10-11，返回 2 张） |
| `calculate-price` | 商品价格试算 | ✅ 实测（2026-10-11，含叠券验证） |

## 3. 核心调用流程

### 流程一：一键领券
```
now-time-info
  → available-coupons
  → auto-bind-coupons
  → query-my-coupons
  → 写入本地账本（ledger.py）
```

### 流程二：最优组合试算（到店自取，2026-10-11 已实测）
```
now-time-info            → 时间上下文（判断券是否在有效期）
  → query-nearby-stores  → 取 storeCode（收藏为空则降级 searchType=2 + 城市/关键词）
  → query-meals          → 取可售餐品（productCode + 菜单价）
  → query-store-coupons  → 取门店可用券（couponId / couponCode）
  → calculate-price ×N   → 对 N 套组合分别算价（可叠券）
  → 统一到「分」比较 price / discount → 输出 Top3 省钱方案
```

### 流程三：消费沉淀与月报
```
order-list / query-order  → 取历史/当前订单
  → ledger.py log-order   → 落库
  → ledger.py report      → 输出累计省下 / 券核销率
  → 填充 report-template  → 生成省钱月报
```

## 4. 关键实现细节

- **响应格式分流**：工具返回两种格式，解析必须分流——JSON 包裹（`now-time-info`、`query-my-account`、`query-nearby-stores`、`query-meals`、`query-store-coupons`、`calculate-price`、`delivery-query-addresses`）与 Markdown 文本（`campaign-calendar`、`available-coupons`、`query-my-coupons`）。规律：**营销/券包类给 Markdown，点餐/算价类给 JSON**。详见 `references/tools.md`。
- **金额单位（✅ 已实测闭环）**：
  - `calculate-price` 全部价格字段 = **分**（`3350` = ¥33.50）；**例外**：`enjoyed`/`enjoyable.realDiscount` = **元**。
  - `query-meals` 的 `currentPrice` / `originalPrice` = **元**（字符串，如 `"33.5"`）。
  - `query-my-coupons` 的「优惠」= **元**。
  - ⚠️ **盈亏就在这 100 倍上**：菜单是元、算价是分，跨工具比对前必须先统一到分。
- **算价传参**：`calculate-price` 必须传 `storeCode` + `orderType` + `beType` + `items[]`；`items` 为对象数组。
  - ⚠️ 到店自取（`beType=1`）**不需要** `addressId`（旧版本本文档曾误记为三元组，已更正）；`beCode` 仅在 `beType=5/2/6` 时传。
  - 叠券：把 `query-store-coupons` 返回的 `couponId` + `couponCode` 塞进对应 `items[]` 项。
  - 两个**同名不同义**字段：算价的 `originalPrice` = 叠券前小计（≠ 菜单划线价），故 `discount` **只反映券的优惠**。
- **限流保护**：批量试算串行执行，调用间隔 ≥150ms，避免触发 429
- **错误降级**：401 → 提示重新激活 Token；429 → 提示降低频率
- **隐私边界**：`accountId`、券明细等个人数据只做本地分析，不写日志、不入公开产物。

## 5. 业务价值

1. **降低决策成本**：把复杂的券+套餐+积分规则，收敛成一句自然语言
2. **避免券浪费**：自动领券 + 临期提醒，提升券核销率
3. **沉淀消费数据资产**：把散落的消费记录结构化为可分析的数据集
4. **可复用架构**：`mcp_call.py` 可抽象为通用 Streamable HTTP MCP 调用器
