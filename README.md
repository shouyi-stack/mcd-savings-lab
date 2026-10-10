# 麦麦省钱精算局 · McSavings Lab

> 一句话领券、一键算价、自动记账。把每次麦当劳消费，沉淀成你自己的消费数据资产。



![麦当劳 MCP](https://img.shields.io/badge/MCP-McDonald's%20China-red)
![License](https://img.shields.io/badge/license-MIT-green)
![Author](https://img.shields.io/badge/author-%E5%AE%88%E6%AF%85%E5%AE%A2%E6%A0%88-blue)

> 本项目为 **麦当劳程序员节创意开发大赛** 参赛作品，由 **守毅客栈** 独立开发，非麦当劳官方产品。

![demo](assets/demo.gif)

## 它解决什么问题

麦当劳的优惠券、套餐、积分规则复杂，很难在点单前算清「怎么点最省」。本 Skill 让你用一句话完成：

- 🎫 **一键领券** — 领光所有可领券，按价值排序告诉你哪些值得用
- 🧮 **组合试算** — 多套点法逐一套算，输出「原价 / 券后 / 实付 / 立省」
- 📊 **消费账本** — 每次消费自动落库，月底生成省钱月报
- ⏰ **临期预警** — 券快过期时提醒你，避免浪费

## 和普通省钱助手的区别

| 能力      | 通用省钱工具 | 麦麦省钱精算局         |
| ------- | ------ | --------------- |
| 单次最优方案  | ✅      | ✅               |
| 消费数据沉淀  | ❌ 用完即忘 | ✅ 本地 SQLite 数据集 |
| 券生命周期管理 | ❌      | ✅ 到期提醒 + 核销率统计  |
| 月度省钱报告  | ❌      | ✅ 一键生成          |

### 数据是怎么沉淀的

每次决策都落进本地 SQLite（`skill/scripts/ledger.py`），三张表 —— `coupons`（券）/ `orders`（订单）/ `points_log`（积分）：

```bash
# 一键出账本：累计省下 / 订单数 / 券核销率 / 临期券 / 偏好品类
python skill/scripts/ledger.py report

# 只看 7 天内到期的券
python skill/scripts/ledger.py list --expiring 7

# 导出订单明细做二次分析
python skill/scripts/ledger.py export --out data/orders.csv
```

把 `report` 的输出填进 `skill/assets/report-template.html`（占位符见文件头注释），就得到一张可直接截图的**省钱月报**——效果见 `skill/assets/report-sample.html`。

> ⚠️ 金额单位不写死：券包的「优惠」实测为**元**，算价工具单位待实测，因此入库时用 `--unit` 显式声明来源单位，本地统一以「分」存储以避免浮点误差。

## 快速开始

> 📦 **想直接试用 / 分享给别人？** 见 [`INSTALL.md`](INSTALL.md) —— 含四种安装方式与常见问题。
> ⚠️ 注意：Skill 本体在 **`skill/` 子目录**（仓库根目录放的是参赛文件），导入时请选 `skill/` 文件夹。

### 1. 申请 MCP Token

访问 <https://open.mcd.cn/mcp> → 登录 → 【控制台】→【激活】→ 复制 Token

### 2. 配置连接器（以 WorkBuddy 为例）

左侧【专家·技能·连接器】→【连接器】→ 右上角【自定义连接器】→【配置MCP】，粘贴：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
    }
  }
}
```

保存后回到列表**启用** `mcd-mcp`。

### 3. 开始使用

直接说：

- "帮我领券"
- "30 块想吃麦当劳，怎么点最省"
- "我有哪些券快过期了"
- "这个月我在麦当劳省了多少钱"

## 目标用户

- 经常吃麦当劳、想省钱的用户
- 想把个人消费数据沉淀下来做分析的用户
- 对 AI Agent / MCP 感兴趣的开发者

## 安全说明

- MCP Token **仅通过环境变量** `MCD_MCP_TOKEN` 读取，不入库、不打日志
- 仓库中不含任何真实凭证，配置示例仅使用占位符
- 下单 / 兑换等写操作默认需用户二次确认

## 项目结构

```
mcd-savings-lab/
├── README.md                   # 项目介绍 / 安装 / 示例 / 目标用户
├── INSTALL.md                  # 安装与试用指南（4 种安装方式）
├── CONTEST_DECLARATION.md      # 参赛声明（官方原文）
├── MCP_INTEGRATION.md          # MCP Server / Tool / 流程 / 业务价值
├── mcp-config.example.json     # 连接器配置示例（仅占位符）
├── workbuddy.md                # WorkBuddy 对话上下文
├── assets/                     # 演示素材（GIF / 截图）
├── data/                       # 本地消费数据（已 gitignore）
└── skill/                      # Skill 本体
    ├── SKILL.md                # Skill 定义与工作流
    ├── scripts/
    │   ├── mcp_call.py         # MCP 统一调用封装
    │   ├── ledger.py           # 消费数据资产层
    │   └── smoke_test.py       # 冒烟测试
    ├── references/             # 工具速查 / 流程 / 算价规则 / 合规红线
    └── assets/
        ├── report-template.html  # 省钱月报模板（占位符填充）
        └── report-sample.html    # 月报效果样本（示例数据）
```

## Roadmap

- [ ] 省钱看板可视化（月度趋势 / 券核销率图表）
- [ ] 更丰富的组合试算策略（凑单、满减联动）
- [ ] 消费数据导出（CSV / 图表）

## License

MIT © 2026 守毅客栈
