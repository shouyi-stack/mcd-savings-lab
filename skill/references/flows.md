# 标准链路（flows）

> 每条链路都写出**正常路径**与**失败路径**。失败时给用户明确提示与替代方案，而非直接报错退出。
> 标注含义：✅ 已实测 ｜ ⚠️ 部分实测 ｜ ⬜ 待实测（步骤来自方案设计，未经真实调用验证）
> 工具字段明细见 `tools.md` 及其子文件（`tools-meta` / `tools-coupon` / `tools-ordering` / `tools-delivery`）；错误码见 `errors-faq.md`。

---

## 链路一：一键领券

```
now-time-info ✅          # 确认时间上下文
  → available-coupons ✅  # 列出可领券（Markdown 文本，无券 ID / 面额）
  → auto-bind-coupons ⬜  # 一键领取（写操作，需用户确认）
  → query-my-coupons ✅   # 回读券包（Markdown 文本）
  → ledger.py log-coupons # 写入本地账本
```

**正常路径**
1. `now-time-info` 取当前时间，用于过滤临期券。
2. `available-coupons` 列出可领券；按标题去重后播报数量。
3. **先向用户复述将领取的券**，确认后再调 `auto-bind-coupons`。
4. `query-my-coupons` 回读券包，按价值 / 临期排序展示。
5. 落库到 `data/mcd_ledger.db`。

**失败路径**

| 情况 | 处理 |
|---|---|
| `401` Token 无效/过期 | 提示用户到 <https://open.mcd.cn/mcp> 控制台重新激活并更新 `MCD_MCP_TOKEN`，**不报错退出** |
| `429` 触发限流 | 暂停并退避重试（间隔 ≥150ms），提示稍后再说 |
| 无可用券（列表为空） | 如实告知「当前没有可领的券」，并建议查看当月活动日历 |
| 券已领过 | 幂等处理：不重复提示失败，跳过已拥有的券 |
| 用户未确认 | **不调用** `auto-bind-coupons`，仅展示可领清单 |

---

## 链路二：点餐定位（到店自取）

```
now-time-info ✅            # 时间上下文（判断券是否在有效期）
  → query-nearby-stores ✅  # 取 storeCode（到店）
  → query-meals ✅          # 门店菜单（可售餐品 + 菜单价）
  → query-store-coupons ✅  # 当前门店可用券（含 couponId / couponCode）
  → calculate-price ✅      # 价格试算（单组合）
```

**正常路径**
1. `query-nearby-stores`：先试收藏餐厅（`beType=1` + `searchType=1`）；为空则降级 `searchType=2` + 城市 + 关键词，取 `storeCode`。
2. `query-meals`：`storeCode` + `orderType=1` + `beType=1` 拉菜单，从 `data.meals` 按 `productCode` 取餐品。
3. `query-store-coupons`：同参数拉「门店下单可用」券（区别于券包历史券），取 `couponId` / `couponCode`。
4. 用券的 `products[].productCode` **反查**该券适用哪件餐品。
5. `calculate-price`：`storeCode` + `orderType=1` + `beType=1` + `items[]`（可叠 `couponId` / `couponCode`）试算。
6. 读 `data.price`（**分**，÷100 展示）、`data.discount`（券省额）、`data.takeWayList`（下单要用的取餐方式 code）。

**失败路径**

| 情况 | 处理 |
|---|---|
| 收藏餐厅为空（`code=600050`） | 降级 `searchType=2`，追问用户「城市 + 地标」 |
| `query-meals` 返回空 | 提示该门店当前无在售餐品，建议更换门店（重新取 `storeCode`） |
| `query-store-coupons` 券为空 | **正常现象**（该门店无可用券），如实告知并展示菜单价，不报错 |
| `storeCode` 缺失 | **不调用**后续工具（会失败），先补 `query-nearby-stores` |
| `calculate-price` 参数不全 | 校验 `storeCode` + `orderType` + `beType` + `items` 四项；到店自取**不需要** `addressId` |
| 金额单位混淆 | 菜单价是**元**、算价是**分** —— 展示前统一到分，见 `pricing-rules.md` §1 |
| `401` / `429` | 同链路一：提示重新激活 / 退避重试 |

> ℹ️ **外送场景（`orderType=2`）** 另走：`delivery-query-addresses` 取地址 → `delivery-query-stores` 取 `storeCode` + `beCode` → 再接上面的菜单/券/算价。详见下方**链路四**。

---

## 链路四：外送（麦乐送 `orderType=2`）

```
now-time-info ✅                     # 时间上下文
  → delivery-query-addresses ✅       # 取 addressId（无地址时返回空数组）
  → delivery-query-stores ⚠️部分      # 取 storeCode + beCode（需真实 addressId）
  → query-meals ⬜(外送)              # 外送菜单（orderType=2 + beType=2 + beCode）
  → query-store-coupons ⬜            # 外送门店可用券
  → calculate-price ⬜                # 外送算价（外送会多出 deliveryPrice / packingPrice）
```

**与到店的核心差异**：外送多了 **`beCode`** 这一步 —— 到店自取不传 `beCode`，但 `beType∈{2,5,6}` 时 `beCode` 是**硬依赖**，且**只能**由 `delivery-query-stores` 提供。

**正常路径**
1. `delivery-query-addresses` 列出配送地址，取 `addressId`。
2. `delivery-query-stores(addressId, beType=2)` 取 `storeCode` + `beCode`。
3. `query-meals(storeCode, orderType=2, beType=2, beCode)` 拉外送菜单 —— **必须带 `beCode`**。
4. `query-store-coupons(storeCode, orderType=2, beType=2, beCode)` 拉外送门店券（取 `couponId` / `couponCode`）。
5. `calculate-price(storeCode, orderType=2, beType=2, beCode, items[])` 试算；外送响应会额外带 `deliveryPrice` / `packingPrice`。

**失败路径（已实测 3 条）**

| 情况 | 返回 / 处理 |
|---|---|
| 无配送地址 | `delivery-query-addresses` 返回 `success:true` + `addresses:[]`（**空数组不是报错**）→ 引导用户先创建配送地址，再重试 |
| `addressId` 无效 | `delivery-query-stores` 返回 `code=600020`「配送地址不存在」→ 回第 1 步重新取 `addressId` |
| 外送场景漏传 `beCode` | `code=600048`「外送场景下，beType=2/5/6 时必传 beCode」→ 先补 `delivery-query-stores` 取 `beCode` |
| 误用到店 `storeCode` 走外送 | 到店门店**没有**外送 `beCode`，外送算价必失败 → 外送**必须**走 `delivery-query-stores` |
| `401` / `429` | 同链路一：提示重新激活 / 退避重试 |

> ⚠️ 成功路径（外送菜单 / 门店券 / 外送算价）**待有配送地址后补测**（见 `pricing-rules.md` §7）。

---

## 链路三：多组合试算比价

```
对 2~3 套组合分别 calculate-price ✅   # 2026-10-11 实测：3 套餐比价通过
  → 比较「优惠金额 / 实付」
  → 输出 Top3 省钱方案
  → ledger.py log-order（用户确认下单后）
```

**正常路径**
1. 基于链路二的门店上下文，准备 2~3 套候选组合（如「单点 / 用券 / 用券+凑单」）。
2. **串行**调用 `calculate-price`（间隔 ≥150ms，规避 429），逐套算价。
3. 对比各组合的 `price` / `discount`（**均为分**），统一单位后排序。
4. 输出 **Top3 方案**，标明「实付 / 划线价 / 比单点省」。
   - ⚠️ 「划线价」取自 `query-meals.originalPrice`（**元**），「实付」取自 `calculate-price.price`（**分**）——**同名不同义**，务必分别换算。

**失败路径**

| 情况 | 处理 |
|---|---|
| 多组合频繁触发 `429` | **降级为单组合试算**（先保证能出结果），并在回复中说明降级原因 |
| 某一组合算价失败 | 跳过该组合继续，最终结果里注明「第 N 套不可用」 |
| 全部组合失败 | 回退到链路二的门店信息，给出菜单 + 可用券，让用户手动选 |
| 单位不一致风险 | ✅ **已闭环**（2026-10-11）：算价为**分**，菜单为**元**；统一到分后再比 |
| 用户直接说要下单 | 走「高风险动作」：复述清单 + 实付金额 → 二次确认 → 才 `create-order` |

---

## 通用约束（四条链路共享）

- **写操作需确认**：`auto-bind-coupons`、`delivery-create-address`、`create-order` 一律先复述后确认。
- **节流**：所有批量/循环调用串行执行，间隔 ≥150ms。
- **隐私**：`accountId`、券明细只入本地库；日志与产物中一律脱敏。
- **降级优先**：任何链路失败都给出**可用的替代路径**，而非只说「不支持」。

---

## 相关文件

- 工具总览与响应格式 → `tools.md`
- 各工具字段（按业务域）→ `tools-meta.md` / `tools-coupon.md` / `tools-ordering.md` / `tools-delivery.md`
- 算价规则与金额单位 → `pricing-rules.md`
- 错误码与常见问题 → `errors-faq.md`
- 合规红线 → `compliance.md`
