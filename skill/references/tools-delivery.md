# 外送链路工具（tools-delivery）

> 外送（`orderType=2`）与到店共用「菜单 → 券 → 算价」三件套，但**多一步取 `beCode`**：
> 外送门店的 `beCode` **只能**由 `delivery-query-stores` 提供，`query-nearby-stores` 只覆盖到店。
> 全部返回 **JSON 包裹**格式。
> 编号与 `tools.md`（工具总览）保持一致。
> 最后更新：2026-10-11

---

## 10. `delivery-query-addresses` — 查询配送地址

- **用途**：外送场景下列出用户的收货地址，取 `addressId`。
- **参数**：无。
- **返回格式**：JSON 包裹（**不是** Markdown 表格）。
- **实测状态**：✅ 2026-10-11（本账号无地址 → `data.addresses: []`）。

**data.addresses[] 字段**

| 字段 | 说明 |
|---|---|
| `addressId` | 地址唯一标识（**外送链路的起点入参**） |
| `contactName` | 收货联系人（**个人信息，不入库**） |
| `fullAddress` | 完整送货地址（**个人信息，不入库**） |
| `phone` | 联系电话（**个人信息，不入库**） |

**注意点**

- ⚠️ **本工具不返回 `storeCode` / `beCode`** —— 外送门店需另调 `delivery-query-stores`。
  （早期文档曾误记为「可获取 storeCode/beCode/addressId」，已更正。）
- 地址为空时 `success:true` 但 `addresses: []` → 应引导用户**创建新配送地址**，而非报错。

---

## 11. `delivery-query-stores` — 查询外送可配送门店

- **用途**：外送（麦乐送 / 团餐）场景下，按配送地址查可配送门店，拿 `storeCode` + `beCode`。
- **参数**：

| 参数 | 必填 | 说明 |
|---|---|---|
| `addressId` | ✅ | 配送地址 ID，来源 `delivery-query-addresses` |
| `beType` | ✅ | `2` 麦乐送 ｜ `6` 团餐 |

- **返回格式**：JSON 包裹，`data` 为**裸数组**（字段同 `query-nearby-stores`：`storeName` / `address` / `storeCode` / `beCode` / `reservation` / `reservationTimeOptions[]`）。
- **实测状态**：⚠️ **部分实测**（2026-10-11）—— 仅验证**失败路径**，成功返回结构**待补测**（需真实配送地址）。

**失败路径（已实测）**

| 入参 | 返回 |
|---|---|
| `addressId="0"`、`beType=2` | `{"success":false,"code":600020,"message":"配送地址不存在"}` |

**注意点**

- ⚠️ `addressId` 必须是 `delivery-query-addresses` 返回的**真实地址 ID**；伪造 / 失效 ID 直接 `code=600020`。
- 展示时须完整给出每个门店的 `storeCode` 与 `beCode`（缺 `beCode` 后续外送调用全部失败）。

---

## 12. `delivery-create-address` — 创建配送地址

- **用途**：用户无配送地址时，创建新的收货地址（外送链路的前置步骤）。
- **参数**：`city`、`contactName`、`phone`、`address`、`addressDetail`（均为必填）、`gender`（选填）。
  - `phone` 要求 **11 位纯数字**（以 1 开头）。
- **返回格式**：⬜ **待实测**。
- **实测状态**：⬜ 未实测（**写操作**：会在账号下真实新增地址）。

**注意点**

- ⚠️ 属**写操作**：会真实修改账号数据。按 `compliance.md` 的约束，**先复述将创建的地址信息、待用户确认后才调用**。
- 团餐场景另需向用户收集「预算金额 + 人数」，用于计算人均预算。

---

## 外送链路专属错误码（已实测）

| 错误码 | message | 触发条件 |
|---|---|---|
| `600020` | 配送地址不存在 | `delivery-query-stores` 传入了无效 / 不属于本账号的 `addressId` |
| `600048` | 外送场景下，beType=2/5/6 时必传 beCode | `query-meals` / `query-store-coupons` / `calculate-price` 在外送场景**漏传 `beCode`** |

> 📌 与到店的差异：到店自取（`beType=1`）**不传 `beCode`**；一旦 `beType∈{2,5,6}`，`beCode` 就是硬依赖，缺一个即 `600048`。

---

## 外送链路标准步骤

```
now-time-info
  → delivery-query-addresses          # 取 addressId（可能为空数组）
  → delivery-query-stores(beType=2)   # 取 storeCode + beCode
  → query-meals(orderType=2, beType=2, beCode)
  → query-store-coupons(orderType=2, beType=2, beCode)
  → calculate-price(orderType=2, beType=2, beCode, items[])
```

详见 `flows.md` 链路四。

---

## 相关文件

- 工具总览与响应格式分流 → `tools.md`
- 点餐与算价工具（到店） → `tools-ordering.md`
- 四条标准链路（含外送失败路径） → `flows.md`
- 错误码与常见问题 → `errors-faq.md`
- 合规红线（写操作确认） → `compliance.md`
