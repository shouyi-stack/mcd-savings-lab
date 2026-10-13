# 点餐与算价工具（tools-ordering）

> 本组是「省钱精算」的核心链路：**定位门店 → 拉菜单 → 拉门店券 → 算价**。
> 全部返回 **JSON 包裹**格式。
> 编号与 `tools.md`（工具总览）保持一致。
> 原则：**只记真实调用验证过的字段**；未实测的标 ⬜。
> 最后更新：2026-10-11

---

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

- **用途**：拉取指定门店可售餐品，拿 `productCode` 用于算价。到店（`orderType=1`）与外送（`orderType=2`）共用。
- **参数**：`storeCode`（必填）、`orderType`（必填，`1` 到店 / `2` 外送）、`beType`（必填）、`beCode`（**`beType=5/2/6` 必传**）、`reservationDate`（预约场景必传）。
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
- **外送场景漏传 `beCode` 会直接失败**（`code=600048`）—— 见 `tools-delivery.md`。

---

## 8. `query-store-coupons` — 查询门店可用券

- **用途**：查询【指定门店 + 订单类型】下**可实际使用**的券（区别于券包里的历史券）。
- **参数**：`storeCode`（必填，**必须全部由数字组成**）、`orderType`（必填）、`beType`（必填）、`beCode`（同 `query-meals` 规则）、`reservationDate`。
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
- 外送场景（`orderType=2`）**必须带 `beCode`**，且会多出 `deliveryPrice` / `packingPrice` —— 见 `tools-delivery.md`。

---

## 相关文件

- 工具总览与响应格式分流 → `tools.md`
- 基础与账户工具 → `tools-meta.md`
- 券与营销工具（券 ID 的「非」来源） → `tools-coupon.md`
- 外送链路工具 → `tools-delivery.md`
- 算价规则与坑点（单位 / 语义） → `pricing-rules.md`
- 错误码与常见问题 → `errors-faq.md`
