---
name: mcd-savings-lab
description: >
  麦麦省钱精算局。当用户提到麦当劳优惠券、领券、查券、券到期、点餐、麦乐送、外送到家、
  门店菜单、算价、凑单、怎么点最省、积分兑换、积分抽奖、当月活动、餐品热量营养时使用。
  通过麦当劳官方 MCP 完成查券、领券、菜单浏览、多组合价格试算与最优省钱方案推荐，
  并把每次消费沉淀为本地可分析的消费数据集。一句话领券、一键算价、自动记账——
  不是「查券工具」，而是「帮你把券花在对的地方、并让你看清自己省了多少」的消费账本。
agent_created: true
---

# 麦麦省钱精算局

## 30 秒上手

直接把需求发过来即可，无需记工具名。典型开场白：

- 「帮我领券」→ 一键领光可领券，并按价值排序
- 「30 块想吃麦当劳，怎么点最省」→ 输出 Top3 省钱方案
- 「我有哪些券快过期了」→ 临期券预警
- 「这个月我在麦当劳省了多少钱」→ 生成省钱月报

## 工作流（6 步）

1. **确认时间上下文** — 调 `now-time-info`（返回 JSON 包裹），拿到服务器年月日，供后续按日期查活动/券。
2. **领券** — `available-coupons`（返回 **Markdown 列表**）→ `auto-bind-coupons`（**写操作，需用户确认**）→ `query-my-coupons`（Markdown）→ 写入本地账本。
3. **点餐定位** — `delivery-query-addresses` 取 `storeCode` / `beCode` / `addressId` → `query-meals`（门店菜单）→ `query-store-coupons`（门店可用券）。
4. **试算比价** — 对 2~3 套组合分别调 `calculate-price`，比较优惠金额，输出最优方案。
5. **落库** — 把本次决策写入本地账本（`scripts/ledger.py`）。
6. **下单** — **高风险动作**：必须先复述完整清单与实付金额，待用户二次确认后才执行。

> 每条链路的详细步骤与**失败路径**见 `references/flows.md`。

## ✅ 擅长处理

1. 券的查询 / 领取 / 到期管理
2. 点餐组合的价格试算与最优推荐
3. 个人消费数据的结构化沉淀与月度分析
4. 活动日历、附近门店与积分账户的查询播报

## ⚠️ 需要条件

1. 算价 / 下单需先有配送地址（无地址时先走 `delivery-create-address`）
2. 历史订单分析需账号已有历史数据
3. 门店可用券判断需先定位门店（`storeCode` / `beCode`）
4. 营养信息仅为官方成分数据呈现，不含医疗建议

## ❌ 超出范围

1. 代替用户完成支付 → 仅生成订单，支付由用户本人完成
2. 修改账号 / 密码等凭证 → 引导用户到官方渠道
3. 医疗 / 营养诊断 → 说明仅为官方数据呈现，建议咨询专业人士
4. 跨品牌价格对比 → 只服务麦当劳官方数据

## 硬性约束（Gotchas）

1. **响应有两种格式**：JSON 包裹（`now-time-info`、`query-my-account`、`query-nearby-stores`、`query-meals`、`query-store-coupons`、`calculate-price`、`delivery-query-addresses`）与 **Markdown 文本**（`campaign-calendar`、`available-coupons`、`query-my-coupons`）。规律：**营销/券包类给 Markdown，点餐/算价类给 JSON**。
2. **金额单位差 100 倍（已实测）**：`query-meals` 菜单价是**元**（`"33.5"`），`calculate-price` 算价是**分**（`3350`）。跨工具比对前先统一到分；例外：算价响应里的 `realDiscount` 是元。
3. **同名不同义**：算价的 `originalPrice` 是「叠券前小计」（≠ 菜单的划线价），所以 `discount` **只反映券的优惠，不含套餐本身折扣**。
4. **券 ID 只有 `query-store-coupons` 给** —— `available-coupons`（无 ID）、`query-my-coupons`（只有用券后价格）都给不了；叠券算价必须靠它。
5. `calculate-price` / `create-order` 必须传 `storeCode` + `orderType` + `beType` + `items`；到店自取**不需要** `addressId`，`beCode` 仅 `beType=5/2/6` 时传。
6. 批量试算须**串行节流**（间隔 ≥150ms），否则触发 429。
7. Token 只从环境变量 `MCD_MCP_TOKEN` 读取，**禁止写入文件或日志**。
8. `auto-bind-coupons` 与下单均为**写操作**，必须二次确认后才执行。
9. `accountId`、券明细等个人信息**只做本地分析**，不入公开产物、不打日志。
10. 绝不做跨品牌价格对比，绝不用「薅秃」「吃垮」等措辞。

## 常见问题（FAQ）

1. **券领了，下单却用不了？** — `query-my-coupons` 只返回「拥有的券」，不校验门店/渠道；下单前用 `query-store-coupons` 查当前门店可用券。
2. **为什么我的积分是 0？** — `query-my-account` 返回可用/累计积分；新号或未消费常为 0，可直接如实播报。
3. **算价需要先准备什么？** — 需要一个配送地址；没有就先 `delivery-create-address`。
4. **`available-coupons` 里有券，但拿不到券 ID 和面额？** — 该工具只返回标题/状态/图片；面额相关请走 `query-my-coupons`。
5. **我的消费数据会被上传吗？** — 不会。数据落在本地 `data/`（已 gitignore），仓库不含个人信息。
6. **能帮我直接付款吗？** — 不能。仅生成订单，支付由用户本人完成。

## 参考文件

| 文件 | 内容 |
|---|---|
| `references/tools.md` | 已实测工具的字段与响应格式（只记验证过的） |
| `references/flows.md` | 三条链路的标准步骤与失败路径 |
| `references/pricing-rules.md` | 算价规则与坑点 |
| `references/compliance.md` | 合规红线速查 |
| `scripts/mcp_call.py` | MCP 统一调用封装（含节流与友好错误） |
| `scripts/ledger.py` | 本地消费数据资产层（SQLite） |
