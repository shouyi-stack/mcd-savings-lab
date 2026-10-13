# 基础与账户工具（tools-meta）

> 本组是「上下文类」工具：一个给**时间**、一个给**账户**。通常是链路的第一步或辅助步骤。
> 编号与 `tools.md`（工具总览）保持一致，便于交叉查找。
> 原则：**只记真实调用验证过的字段**；未实测的标 ⬜，不写死假设。
> 最后更新：2026-10-11

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

**注意点**

- 用服务器的 `date` 作为「今天」，**不要用本地时间**去推算券/活动的有效期边界。

---

## 2. `query-my-account` — 查询积分账户

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
- `accountId` 属个人信息，**落库一律不存**（`ledger.py` 的 schema 里根本没有这个字段）。
- 积分字段是**字符串**（如 `"0"`），比较/运算前先转 `int`。

---

## 相关文件

- 工具总览与响应格式分流 → `tools.md`
- 券与营销工具 → `tools-coupon.md`
- 点餐与算价工具 → `tools-ordering.md`
- 外送链路工具 → `tools-delivery.md`
