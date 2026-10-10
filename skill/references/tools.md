# 工具速查（只记录实测过的）

> 原则：只写经**真实调用**验证过的工具与字段；未实测的工具不写入本文件（对应执行手册 Day 2 要求）。
> 首次记录：2026-10-10 ｜ 最后更新：2026-10-10

## ⚠️ 两种响应格式（重要）

实测发现，麦当劳 MCP 的工具返回**两种格式**，解析逻辑必须区分处理：

| 格式 | 特征 | 已实测工具 |
|---|---|---|
| **JSON 包裹** | `{success, code, message, traceId, data}` | `now-time-info`、`query-my-account` |
| **Markdown 文本** | 纯 Markdown（含标题/列表，图片为内嵌 `<img>` 标签） | `campaign-calendar`、`available-coupons`、`query-my-coupons` |

> 📌 含义：对 Markdown 类工具，脚本/工作流**不能假设有 JSON 字段**；需按文本渲染或正则提取。
> `traceId` 仅用于排障，**绝不写入任何产物**。

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
