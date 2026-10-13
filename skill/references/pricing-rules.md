# 算价规则与坑点（pricing-rules）

> 原则：**只写验证过的；没验证的明确标「待实测」，不写死假设。**
> 标注：✅ 已实测 ｜ ⚠️ 部分实测 ｜ ⬜ 待实测
> 最后更新：2026-10-11（算价链路已跑通，单位问题闭环）
> `calculate-price` 的字段明细见 `tools-ordering.md` §9；错误码见 `errors-faq.md`。

---

## 1. 金额单位（最关键的坑）

| 来源 | 单位 | 状态 |
|---|---|---|
| `calculate-price` 全部价格字段 | **分**（`3350` = ¥33.50） | ✅ 实测 2026-10-11 |
| `calculate-price` 的 `enjoyed`/`enjoyable.realDiscount` | ⚠️ **元**（同响应内的例外） | ✅ 实测 2026-10-11 |
| `query-meals` 的 `currentPrice` / `originalPrice` | **元**（字符串，如 `"33.5"`） | ✅ 实测 2026-10-11 |
| `query-my-coupons` 的「优惠」 | **元**（实测返回如 `¥13.3`） | ✅ 实测 2026-10-10 |
| `query-my-account` 积分数值 | 字符串整数（如 `"0"`），非金额 | ✅ 实测 2026-10-10 |

⚠️ **最大陷阱：同一条链路上存在 100 倍差**
`query-meals` 给**元**（`"33.5"`），`calculate-price` 给**分**（`3350`）。
拿菜单价直接和算价结果比 → **必错**。跨工具比对前，一律先统一到分。

⚠️ **次大陷阱：单个响应内部也混用单位**
`calculate-price` 里绝大多数金额字段是**分**，唯独 `enjoyed.realDiscount` / `enjoyable.realDiscount` 是**元**。

**处理约定**
- 本地账本（`ledger.py`）统一以**分（整数）**存储，避免浮点误差。
- 入库时用 `--unit` **显式声明来源单位**（`yuan` / `fen` / `unknown`），脚本不做假设。
- 同时保留原始值与原始单位（`raw_value` / `unit_source`）以便溯源。
- **链路固定单位**：菜单价 → `--unit yuan`；算价结果 → `--unit fen`。本文件原「`calculate-price` 单位待实测」项**已闭环**。

---

## 2. 算价的必传参数（缺一即失败）

`calculate-price` 与 `query-meals` / `query-store-coupons` **共用同一套门店上下文参数**：

| 参数 | 来源 | 说明 |
|---|---|---|
| `storeCode` | `query-nearby-stores`（到店）/ `delivery-query-stores`（外送） | 门店编码，**必填** |
| `orderType` | 业务场景 | `1` 到店（自取+得来速）｜`2` 外送（麦乐送+团餐），**必填** |
| `beType` | 业务场景 | `1` 到店自取｜`2` 麦乐送｜`5` 得来速｜`6` 团餐，**必填** |
| `beCode` | `query-nearby-stores` / `delivery-query-stores` | ⚠️ `beType=5/2/6` 时**必传**；`beType=1` **不传** |
| `items` | `query-meals` | **对象数组**，每项 `{productCode, quantity(≥1)}`，可叠 `couponId`/`couponCode` |

⚠️ **到店自取不需要 `addressId`** —— 本文件旧版本曾要求 `storeCode + beCode + addressId` 三元组，**实测为错误**，已更正。
`addressId` 仅外送（`orderType=2`）可能用到，来自 `delivery-query-addresses`（**该工具不返回 storeCode**，别搞反）。

> 缺任一必填项时，**不要发起算价请求**（会因参数不完整失败），先回 `query-nearby-stores` 补齐门店上下文。

---

## 3. 券的计价规则

- **「优惠」是「用券后价格」，不是面额** —— `query-my-coupons` 的 `¥13.3` 表示用券后花 13.3 元，而非省 13.3 元。
  - 想算「省了多少」需要同一餐品的**原价**做差：`立省 = 原价 − 用券后价格`。
- **门槛**：可领取券列表（`available-coupons`）**不返回面额与门槛**，只有标题 / 状态 / 图片；面额相关只能走 `query-my-coupons`。
- **渠道差异**：券可能带「到店专用」等标签，**外卖 / 到店**适用范围不同，比对前先确认标签。
- **有效期两段式**：`query-my-coupons` 的有效期含「日期区间 + 每日可用时段」两段，解析时拆开；`ledger` 用 `expire_at` 存结束时间、`daily_window` 存时段。

### 3.1 叠券算价（2026-10-11 实测打通）

**唯一可用的券 ID 来源 = `query-store-coupons`**：

| 工具 | 给不给 `couponId` / `couponCode` |
|---|---|
| `available-coupons` | ❌ 只有标题 / 状态 / 图片 |
| `query-my-coupons` | ❌ 只有「用券后价格」，无 ID |
| **`query-store-coupons`** | ✅ **给 `couponId` + `couponCode` + 适用 `products[].productCode`** |

**叠券步骤**
1. `query-store-coupons` 拿到门店券，得到 `couponId` / `couponCode` 及适用商品。
2. 用 `products[].productCode` **反查**「哪张券能用在哪件餐品上」。
3. 把 `couponId` + `couponCode` 一起塞进 `calculate-price` 的 `items[]` 对应项。
4. 读 `data.discount`（分）即为该券省下的金额。

**实测验证**（美式中杯 + 新人7折券）
```
originalPrice 1900 (¥19.00) → price 1330 (¥13.30)，discount 570 (¥5.70)
19.00 × 0.7 = 13.30  ✅ 折扣券精确生效
```

### 3.2 `discount` 只反映「券」的优惠（重要）

`calculate-price` 的 `discount` **不包含套餐本身的折扣**——因为它的 `originalPrice` 取的是「叠券前小计」，而非划线价。
「比单点省多少」要用菜单 `originalPrice`（划线价）；「券再省了多少」才用算价的 `discount`。详见 §6 第 9 条。

---

## 4. 组合试算策略

默认准备 2~3 套候选，逐套 `calculate-price` 后比价：

| 组合 | 说明 |
|---|---|
| A · 单点 | 不用券，作为基准线（提供「原价」） |
| B · 用券 | 直接对目标餐品使用最优券 |
| C · 用券 + 凑单 | 命中门槛时补一件小额餐品，看净值是否更优 |

**输出格式**（每条组合）：`原价 / 券后 / 实付 / 立省`，最后给出 Top3。

> 是否值得「凑单」，判定标准是 **净省额**（凑单后立省 − 凑单多花的钱）> 0，而不是「凑到门槛」本身。

**实测样例：30 元预算 · 到店自取 Top3**（2026-10-11，门店 1960648）

| 排名 | 方案 | 实付 | 划线价 | 比单点省 |
|---|---|---|---|---|
| 🥇 | 大堡口福三件套 | ¥22.90 | ¥48.00 | **¥25.10** |
| 🥈 | 龙焰鸡腿堡三件套 | ¥26.90 | ¥48.50 | **¥21.60** |
| 🥉 | 龙焰芝士棒鸡腿堡三件套 | ¥29.90 | ¥51.50 | **¥21.60** |

> ⚠️ 注意上表「划线价」取自 `query-meals` 的 `originalPrice`（**元**），「实付」取自 `calculate-price` 的 `price`（**分**，已 ÷100）。
> 两个字段**同名不同义**，这正是 §1 / §6 反复强调的单位与语义坑。

---

## 5. 限流与批量调用

- 服务端限制 **600 次 / 分钟 / Token**。
- 批量试算、循环调用一律**串行**，调用间隔 **≥150ms**（`mcp_call.py` 已内置节流）。
- 多组合仍触发 `429` 时，**降级为单组合试算**，并在回复中说明降级原因。

---

## 6. 坑点清单（Gotchas）

1. **菜单给「元」、算价给「分」，差 100 倍** —— 跨工具比对前先统一到分。见 §1。
2. **同一响应内部也混单位** —— `calculate-price` 的 `enjoyed`/`enjoyable.realDiscount` 是**元**，其余金额字段是**分**。
3. **「优惠」≠「面额」** —— `query-my-coupons` 的 `¥13.3` 是用券后价格，不是省了 13.3。见 §3。
4. **券 ID 只有 `query-store-coupons` 给** —— `available-coupons` / `query-my-coupons` 都给不了。见 §3.1。
5. **算价必填是 `storeCode` + `orderType` + `beType` + `items`** —— 到店自取**不需要** `addressId`。见 §2。
6. **`beCode` 只在 `beType=5/2/6` 时传** —— `beType=1`（到店自取）不传。
7. **`delivery-query-addresses` 不返回 `storeCode`** —— 外送门店要走 `delivery-query-stores`。
8. **`query-nearby-stores` 的 `longitude`/`latitude` 恒为 `0.0`** —— 不能用于打点；`distance` 可信。
9. **算价的 `originalPrice` ≠ 菜单的 `originalPrice`** —— 前者是「叠券前小计」，后者是「划线价」。
   例：大堡口福三件套，菜单 `"48"` vs 算价 `2290`(¥22.90)。
   → **`discount` 只反映券的优惠，不含套餐本身折扣**。
10. **`query-nearby-stores` 收藏列表常为空** —— `searchType=1` 失败（`code=600050`）时自动降级 `searchType=2` + 城市 + 关键词。
11. **券有渠道限制** —— 「到店专用」的券不能用于外卖。
12. **有效期含每日时段** —— 别只看日期。
13. **积分字段是字符串** —— `availablePoint` 等是 `"0"` 而非数字 0，比较前先转 int。
14. **官方字段拼写原样保留** —— `currentMouthExpirePoint`（Mouth＝Month）、`tradeDateTime` 等，勿「纠正」。

---

## 7. 验证清单

**已闭环（2026-10-11）**

- [x] `calculate-price` 返回结构与**金额单位** → **分**（例外：`enjoyed`/`enjoyable.realDiscount` 为元）
- [x] `query-meals` 餐品编码字段名 → `categories[].meals[].code`，价格在 `data.meals{code}` 里
- [x] `query-store-coupons` 返回格式与字段 → **JSON**，含 `couponId` / `couponCode` / `products[]`
- [x] `delivery-query-addresses` 实际字段名 → `addresses[]{addressId, contactName, fullAddress, phone}`；**不含 storeCode**
- [x] `query-nearby-stores` 取 `storeCode` 的可用路径 → `searchType=2` + `city` + `keyword`
- [x] 叠券算价全链路 → `query-store-coupons` 取 ID → `calculate-price` 叠券 → `discount` 校验通过
- [x] 外送链路**前置依赖与失败码** → `beCode` 是硬依赖（`600048`）；无效地址 `600020`；无地址返回空数组（2026-10-11）

**仍待验证**

- [ ] 凑单门槛能否直接取到（券信息无门槛字段；`calculate-price` 的 `enjoyable.balance` 疑似门槛差额，需构造临界用例）
- [ ] `promotionId` 的实际用途（是否需要回传算价）
- [ ] 外送链路**成功路径**（外送菜单 / 门店券 / 外送算价）—— 需真实配送地址；**失败路径已闭环**（见 `tools-delivery.md`、`flows.md` 链路四）
- [ ] `withOrder` 随单购参数对最终价的影响
- [ ] `modification` 特制选项（`selectedKey` / `unselectedKey`）传参规则

---

## 相关文件

- 工具总览与响应格式 → `tools.md`
- `calculate-price` 字段明细 → `tools-ordering.md` §9
- 标准链路与失败路径 → `flows.md`
- 错误码与常见问题 → `errors-faq.md`
- 合规红线 → `compliance.md`
