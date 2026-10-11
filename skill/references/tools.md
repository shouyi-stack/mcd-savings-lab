# 工具速查（只记录实测过的）

> 原则：只写经**真实调用**验证过的工具与字段；未实测的工具不写入本文件（对应执行手册 Day 2 要求）。
> 首次记录：2026-10-10 ｜ 最后更新：2026-10-11（新增 5 个「点餐与算价」链路工具）

## ⚠️ 两种响应格式（重要）

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

## 1. `now-time-info` — 获取当前时间信息

- **用途**：获取服务器当前时间上下文；在不知道当前时间、或需按日期查询活动/券时使用。
- **参数**：无。
- **返回格式**：JSON 包裹。
- **实测状态**：✅ 2026-10-10。

**data 字段**

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `timestamp` | int | 1791613662966 | 毫秒级时间戳 |
| `datetime` | string | 2026-10-10T14:27:42.966 | ISO 格式时间 |
| `formatted` | string | 2026-10-10 14:27:42 | 格式化时间 |
| `date` | string | 2026-10-10 | 日期（yyyy-MM-dd） |
| `year` / `month` / `day` | int | 2026 / 10 / 10 | 年 / 月 / 日 |
| `dayOfWeek` | string | SATURDAY | 星期（英文大写） |
| `timezone` | string | GMT+08:00 | 时区 ID |
| `offset` | string | +08:00 | 时区偏移 |
| `utc` | string | 2026-10-10T06:27:42.967Z | UTC 时间 |

---

## 2. `campaign-calendar` — 当月营销活动日历

- **用途**：查看进行中 / 即将到来的营销活动（品鉴会、主题派对、联名周边等）。
- **参数**：`specifiedDate`（可选，`yyyy-MM-dd`）。传入则以该日为锚点返回前后各一个有活动的日子；不传默认返回当月全部活动。
- **返回格式**：**Markdown 文本**。
- **实测状态**：✅ 2026-10-10（不传参，返回当月活动列表）。

**文本结构**

```
### 当前时间：<日期时间>
### 活动列表：
#### <日期> 往期回顾 / 今日 / （未来日期无前缀）
- **活动标题**：…
  **活动内容介绍**：…（多行文案，含 emoji）
  **活动图片介绍**：<img src="…" …>
```

**注意点**

- 活动按日期分段，前缀有「往期回顾 / 今日」等；图片是内嵌 HTML `<img>`，非结构化 URL 字段。
- 返回为人类可读文案（含营销 emoji），**不适合直接机器解析**；需提取时用「活动标题」行做锚点。

---

## 3. `available-coupons` — 查询可领取券

- **用途**：查询用户当前可领取的「麦麦省」优惠券列表。
- **参数**：无。
- **返回格式**：**Markdown 文本**。
- **实测状态**：✅ 2026-10-10（返回 6 张可领券）。

**文本结构**

```
### 麦麦省优惠券列表：
- 优惠券标题：<名称>
  状态：可领取
  优惠券图片：<img src="…" …>
```

**注意点**

- **不返回券 ID、面额、门槛等结构化字段**，仅有标题 / 状态 / 图片 —— 需要券 ID 或面额时需另寻工具（如 `query-my-coupons`）。
- 同名券可能重复出现（不同活动来源）。

---

## 4. `query-my-coupons` — 查询我的券包

- **用途**：查看用户卡包中**已拥有**的券（非门店可用校验，门店可用请用 `query-store-coupons`）。
- **参数**：`page`（默认 1，最多 5）、`pageSize`（默认 200，最大 200）。
- **返回格式**：**Markdown 文本**。
- **实测状态**：✅ 2026-10-10（返回 2 张券）。

**文本结构**

```
# 您的优惠券列表
共 N 张可用优惠券 | 第 x/y 页 | 每页 200 条
## <券名>
- **优惠**: ¥xx.x (用券价格)
- **有效期**: yyyy-MM-dd HH:mm-yyyy-MM-dd HH:mm <时间段>
- **领取时间**: <相对时间，如「今日收到」>
- **标签**: <如「到店专用」>
<img src="…">
```

**注意点**

- 「优惠」给的是**用券后价格（元）**，不是面额。
- 「有效期」含两个时间片段（日期区间 + 每日可用时段），解析时注意拆开。
- 分页：`page` 最大 5，单页最大 200 —— 券很多时需翻页。

---

## 5. `query-my-account` — 查询积分账户

- **用途**：查询积分余额与过期情况。
- **参数**：无。
- **返回格式**：JSON 包裹。
- **实测状态**：✅ 2026-10-10。

**data 字段**（值均为字符串）

| 字段 | 说明 |
|---|---|
| `accountId` | 账户 ID（**个人敏感信息，不得入库 / 入产物**） |
| `currency` | 货币类型，实测为「麦享会积分」 |
| `availablePoint` | 可用积分 |
| `accumulativePoint` | 累计积分 |
| `usedPoint` | 已使用积分 |
| `frozenPoint` | 冻结积分 |
| `expiredPoint` | 已过期积分 |
| `currentMouthExpirePoint` | 本月将过期积分 |
| `lastMouthExpirePoint` | 上月已过期积分 |
| `nextMouthExpirePoint` | 下月将过期积分 |

**样例（已脱敏）**

```json
{
  "success": true,
  "code": 200,
  "message": "请求成功",
  "data": {
    "accountId": "<已脱敏>",
    "currency": "麦享会积分",
    "availablePoint": "0",
    "accumulativePoint": "0",
    "usedPoint": "0",
    "frozenPoint": "0",
    "expiredPoint": "0",
    "currentMouthExpirePoint": "0",
    "lastMouthExpirePoint": "0",
    "nextMouthExpirePoint": "0"
  }
}
```

**注意点**

- 字段名拼写含官方原始拼写 `currentMouthExpirePoint`（Mouth＝Month，官方如此），调用/解析时**按原样**，勿「纠正」。
- `accountId` 属个人信息，落库一律不存。

---

# 点餐与算价链路（2026-10-11 实测）

> 本组工具是「省钱精算」的核心：定位门店 → 拉菜单 → 拉门店券 → 算价。
> 全部返回 **JSON 包裹**格式。

## 6. `query-nearby-stores` — 查询到店门店

- **用途**：到店场景下查询可点餐门店，拿到后续工具的 `storeCode`。
- **参数**：

| 参数 | 必填 | 说明 |
|---|---|---|
| `beType` | ✅ | `1` 到店自取 ｜ `5` 得来速车道取餐 |
| `searchType` | ✅ | `1` 搜收藏餐厅 ｜ `2` 按位置搜索 |
| `city` | searchType=2 必填 | 城市名 |
| `keyword` | searchType=2 必填 | 位置关键词 |

- **返回格式**：JSON 包裹，但 **`data` 是裸数组**（不是 `data.stores[]`）。
- **实测状态**：✅ 2026-10-11（`searchType=2` + `city=西安` + `keyword=小寨` → 返回 5 家门店）。

**data[] 字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `storeCode` | string | 门店编码（**后续工具入参**） |
| `storeName` | string | 门店名称 |
| `address` | string | 门店地址 |
| `distance` | int | 到店距离（米） |
| `businessStatus` | bool | 是否营业中 |
| `businessStartTime` / `businessEndTime` | string | 营业时段（`HH:mm`） |
| `longitude` / `latitude` | number | ⚠️ 实测**恒为 `0.0`** |
| `reservation` | bool | 是否支持预约 |
| `reservationTimeOptions[]` | array | `{date, today, reservationOptionText}`；`today=true` 标记今天 |

**注意点**

- ⚠️ **`searchType=1`（收藏餐厅）大概率失败**：无收藏时返回 `success:false`、`code=600050`、`message="收藏餐厅列表为空，请您提供城市+关键词进行搜索"`。→ 兜底策略：**先试收藏，失败自动降级为 `searchType=2`**，追问用户城市+地标。
- ⚠️ **`longitude`/`latitude` 实测返回 `0.0`**，不能用于地图打点；`distance` 是可信的。
- `reservation=true` 时 `reservationTimeOptions` 每条都影响用户选择，展示时**不可省略**。

---

## 7. `query-meals` — 查询门店菜单

- **用途**：拉取指定门店可售餐品，拿 `productCode` 用于算价。
- **参数**：`storeCode`（必填）、`orderType`（必填，`1` 到店 / `2` 外送）、`beType`（必填）、`beCode`（`beType=5/2/6` 必传）、`reservationDate`（预约场景必传）。
- **返回格式**：JSON 包裹。
- **实测状态**：✅ 2026-10-11（`storeCode=1960648`、`orderType=1`、`beType=1` → 返回 15 个分类、约 130 个餐品）。

**data 结构**

```
data.categories[]      # 菜单分类
  ├─ name              # 分类名（如「人气热卖」「随心配 1+1」）
  └─ meals[]           # {code, tags[]}  ← 只有编码和标签，无价格
data.meals{}           # 餐品详情映射表，key = productCode
  └─ {name, image, currentPrice, originalPrice,
      discountType, canWithOrder, withOrder{cardId, cardType, membershipCode, specId}}
data.frequent{}        # 常点餐品
```

**注意点**

- ⚠️⚠️ **`currentPrice` / `originalPrice` 的单位是「元」**，且是**字符串**（如 `"33.5"`、`"47"`）。
  而 `calculate-price` 返回的金额单位是**「分」** —— **同一链路上两套单位，差 100 倍**。
  详见 `pricing-rules.md` §1。
- **`categories[].meals[]` 里没有价格**，价格要去 `data.meals[code]` 里按 code 查。
- 分类名与 `tags` 带换行符（如 `"小食拼盘\n/多人餐"`），比对时需先规范化。
- `discountType` 取值：`null`（不享受优惠）/ `"早餐卡优惠"` / `"促销优惠"` / `"麦金卡优惠"` / `"随单购早餐卡优惠"` / `"随单购麦金卡优惠"`。
- `canWithOrder=true` 的商品，`withOrder` 结构需在算价时通过 `withOrder` 参数传入才能享受随单购价。

---

## 8. `query-store-coupons` — 查询门店可用券

- **用途**：查询【指定门店 + 订单类型】下**可实际使用**的券（区别于券包里的历史券）。
- **参数**：`storeCode`（必填）、`orderType`（必填）、`beType`（必填）、`beCode`（同 query-meals 规则）、`reservationDate`。
- **返回格式**：JSON 包裹，`data` 为数组。
- **实测状态**：✅ 2026-10-11（`storeCode=1960648`、`orderType=1`、`beType=1` → 返回 2 张券）。

**data[] 字段**

| 字段 | 说明 |
|---|---|
| `title` | 券名（如「新人专享-中杯美式7折」） |
| `couponId` | **券 ID**（算价入参） |
| `couponCode` | **券码**（算价入参） |
| `tradeDateTime` | 有效期，格式 `yyyy-MM-dd HH:mm:ss-yyyy-MM-dd HH:mm:ss` |
| `products[]` | `{productCode, productName}` —— **券适用的商品编码** |
| `promotionId` | 促销活动 ID |

**注意点**

- ✅ **这是唯一能拿到 `couponId` + `couponCode` 的只读工具** —— 叠券算价的**前提**。
  （`available-coupons` 只给标题/状态/图片；`query-my-coupons` 只给用券后价格，都不给 ID。）
- 同一 `couponId` 可对应多个 `couponCode`，展示时**按 `couponId` 分组**，多个券码显示「首个(共 N 张)」。
- `products[]` 直接给出适用商品编码 → **可用于反查「哪张券能用在这件餐品上」**。

---

## 9. `calculate-price` — 商品价格试算

- **用途**：计算含优惠的实付价格。**下单前的必经步骤**。
- **参数**：`storeCode`、`orderType`、`beType`（三者必填）+ `items[]`；`beCode`（DT/外送必传）、`reservationDate`、`needTableware`、`withOrder`、`gmServiceCode` 选填。
  - `items[]` 每项：`productCode`、`quantity`（≥1），可选 `couponId`、`couponCode`、`modification`、`roundList`。
- **返回格式**：JSON 包裹。
- **实测状态**：✅ 2026-10-11（原价算价 + 叠券算价 共 5 次调用）。

**⚠️ 金额单位：`分`（已实测确认）**

| 字段 | 单位 | 实测样例 |
|---|---|---|
| `productOriginalPrice` / `productPrice` | **分** | `3350` = ¥33.50 |
| `originalPrice` / `price` / `discount` | **分** | `1900` → `1330`，`discount` `570` |
| `deliveryPrice` / `packingPrice` / `tablewarePrice` | **分** | — |
| `productList[].originalSubtotal` / `subtotal` | **分** | — |
| `enjoyed.realDiscount` / `enjoyable.realDiscount` | ⚠️ **元** | 折扣券为 `7.5` 这类折扣值 |
| `enjoyed.balance` / `enjoyable.balance` | **分** | 门槛差额 |

**验证样例（美式中杯 + 新人7折券）**

```
入参: productCode=9900000119, quantity=1, couponId=..., couponCode=...
返回: productOriginalPrice=1900  →  ¥19.00
      productPrice=1330          →  ¥13.30   （1900 × 0.7 = 1330 ✅ 7折精确生效）
      discount=570               →  ¥5.70
```

**完整 data 字段**

| 字段 | 说明 |
|---|---|
| `productOriginalPrice` / `productPrice` | 商品原价 / 现价（分） |
| `deliveryOriginalPrice` / `deliveryPrice` | 运费原价 / 现价（分，到店场景省略） |
| `packingOriginalPrice` / `packingPrice` | 打包费原价 / 现价（分，到店场景省略） |
| `tablewarePrice` | 餐具费现价（分） |
| `originalPrice` / `price` / `discount` | 合计原价 / 实付 / 优惠（分） |
| `productList[]` | `{productCode, productName, quantity, originalSubtotal, subtotal}`（分） |
| `takeWayList[]` | **取餐方式选项** `{code, title, subtitle}` —— 如 `eat-in`(堂食) / `take-in-store`(外带)，**下单时必须带 code** |
| `mealAssistanceList[]` | 助餐服务 `{code, name}`（团餐场景） |
| `enjoyed` | 已享受的优惠 `{amountType, realDiscount, balance}` |
| `enjoyable` | 可享受的优惠 `{amountType, realDiscount, balance}` |

`amountType`：`1` 特价 ｜ `2` 折扣 ｜ `3` 立减

**注意点**

- ⚠️⚠️ **`originalPrice` 语义与菜单不同名**：算价的 `originalPrice` = **叠券前的小计**（≈ 菜单的 `currentPrice`），
  **不是菜单的划线价 `originalPrice`**。
  例：大堡口福三件套，菜单 `originalPrice="48"`（划线价），算价 `originalPrice=2290`（¥22.90）。
  → **算价的 `discount` 只反映「券」带来的优惠，不反映套餐本身折扣**。
  「比单点省多少」要用菜单 `originalPrice`；「券再省多少」才用算价的 `discount`。
- ⚠️ 同一响应里**混用两套单位**：绝大多数金额字段是分，唯独 `enjoyed`/`enjoyable` 的 `realDiscount` 是**元**。
- 到店自取（`beType=1`）**不需要 `addressId`**，也不要传 `beCode`。
- 算价成功 ≠ 已下单。成功后应引导用户「确认价格后可以说『创建订单』」。

---

## 10. `delivery-query-addresses` — 查询配送地址

- **用途**：外送场景下列出用户的收货地址。
- **参数**：无。
- **返回格式**：JSON 包裹。
- **实测状态**：✅ 2026-10-11（本账号无地址 → `data.addresses: []`）。

**data.addresses[] 字段**

| 字段 | 说明 |
|---|---|
| `addressId` | 地址唯一标识 |
| `contactName` | 收货联系人（**个人信息，不入库**） |
| `fullAddress` | 完整送货地址（**个人信息，不入库**） |
| `phone` | 联系电话（**个人信息，不入库**） |

**注意点**

- ⚠️ **本工具不返回 `storeCode` / `beCode`** —— 外送门店需另调 `delivery-query-stores`。
  （左表旧文档曾误记为「可获取 storeCode/beCode/addressId」，已更正。）
- 地址为空时 `success:true` 但 `addresses: []` → 应引导用户**创建新配送地址**，而非报错。
