# 安装与试用 · 麦麦省钱精算局

> 给别人试用的完整步骤。全程约 5 分钟，**不需要写代码**。

---

## ⚠️ 先读这一条（最关键）

本项目仓库根目录放的是**参赛文件**（README / CONTEST_DECLARATION 等），  
**Skill 本体在 `skill/` 子目录里**。

所以：

- ❌ 不要用「从 Git 仓库导入 + 仓库地址」直接装 —— 根目录没有 `SKILL.md`，会装成空壳
- ✅ 请把 **`skill/` 这个文件夹**（或打包好的 zip）导入

---

## 前置条件

| 项                     | 要求                                       |
| --------------------- | ---------------------------------------- |
| WorkBuddy             | 正常安装并登录                                  |
| Python                | 3.8+（脚本只用标准库，**无需 pip 安装任何依赖**）          |
| **麦当劳账号 + MCP Token** | **必须**。券、积分、订单都是**账号级数据**，每个人要用自己的 Token |

---

## 第 1 步：申请 MCP Token

1. 打开 <https://open.mcd.cn/mcp>
2. 用麦当劳账号登录 → 【控制台】→【激活】
3. 复制生成的 Token（下面第 3 步要用）

> Token 是个人凭据，**不要发给别人、不要提交到任何仓库**。



---

## 第 2 步：安装 Skill（四种方式，任选其一）

### 方式 A · 拖拽导入（最省事，推荐）

1. 下载仓库并解压（或直接用别人发你的 `mcd-savings-lab-skill.zip`）
2. WorkBuddy 左侧【技能】→【添加技能】→【上传技能】
3. 选中解压出来的 **`skill/` 文件夹**（内含 `SKILL.md`）→ 确认

> 也可以直接把该文件夹拖进 WorkBuddy 主窗口中央。

### 方式 B · ZIP 包导入

1. 拿到 `mcd-savings-lab-skill.zip`
2. WorkBuddy →【设置】→【技能管理】→【导入技能】→ 选择该 zip
3. 系统自动解压并注册

### 方式 C · 手动放置（开发者）

把 `skill/` 文件夹复制到用户级技能目录，并重命名为技能名：

```bash
# 用户级（对所有项目生效）
~/.workbuddy/skills/mcd-savings-lab/

# 或项目级（只对当前项目生效）
<你的项目>/.workbuddy/skills/mcd-savings-lab/
```

放好后目录应长这样：

```
~/.workbuddy/skills/mcd-savings-lab/
├── SKILL.md
├── scripts/
│   ├── mcp_call.py
│   ├── ledger.py
│   └── smoke_test.py
├── references/
│   ├── tools.md
│   ├── tools-meta.md
│   ├── tools-coupon.md
│   ├── tools-ordering.md
│   ├── tools-delivery.md
│   ├── flows.md
│   ├── pricing-rules.md
│   ├── errors-faq.md
│   └── compliance.md
└── assets/
    ├── report-template.html
    └── report-sample.html
```

### 方式 D · 从 Git 仓库导入（需先处理目录层级）

若要走「从 Git 仓库导入」，需要先让 `SKILL.md` 位于被导入目录的**根**：

```bash
git clone https://github.com/shouyi-stack/mcd-savings-lab.git
cd mcd-savings-lab
# 把 skill/ 的内容作为独立目录导入
```

然后把 `skill/` 目录按**方式 A / C** 导入即可。

---

## 第 3 步：配置 MCP 连接器

WorkBuddy 左侧【专家·技能·连接器】→【连接器】→ 右上角【自定义连接器】→【配置 MCP】，粘贴：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer 你的MCP_TOKEN" }
    }
  }
}
```

保存后回到连接器列表，**启用** `mcd-mcp`。

> ⚠️ 注意 `url` **不要加路径后缀**（不是 `https://mcp.mcd.cn/mcp`），否则会连接失败。  
> 配置里出现是**你自己的 Token**，不要截图外发。

---

## 第 4 步：验证装好了没

**（1）跑自检**（只用标准库，不联网也能跑）

```bash
python skill/scripts/smoke_test.py --offline
```

看到「🎉 全部通过」即文件齐全。想连网测工具：

```bash
python skill/scripts/smoke_test.py
```

**（2）直接说一句话试用**

在 WorkBuddy 对话里输入任意一句：

- 「帮我领券」
- 「30 块想吃麦当劳，怎么点最省」
- 「我有哪些券快过期了」
- 「这个月我在麦当劳省了多少钱」

**能返回真实的券列表 / 方案 / 月报，就是装好了。**

---

## 常见问题

| 现象                | 原因与解决                                                |
| ----------------- | ---------------------------------------------------- |
| 技能装了但没反应          | 确认导入的是 **`skill/` 文件夹**（含 `SKILL.md`），而不是仓库根目录       |
| 连接器连接失败           | 检查 `url` **是否带了 `/mcp` 后缀** —— 必须无后缀                 |
| 提示 401 / Token 无效 | Token 过期，回 <https://open.mcd.cn/mcp> 重新激活并更新配置       |
| 查不到券 / 积分是 0      | 券和积分是**账号级**的，需要用**你自己的** Token；新号确实可能是 0            |
| 提示 429            | 调用太频繁（限流 600 次/分钟），等一会儿再试                            |
| 报「缺少依赖」           | 本项目**不需要任何第三方库**，只要有 Python 3.8+ 即可                  |
| 想卸载               | 【设置】→【技能管理】→ 找到 `mcd-savings-lab` → 卸载；连接器同理在连接器列表关闭 |

---

## 安全与隐私

- 消费数据只落在**本地** `data/` 目录，**不上传、不外传**
- Token 只从环境变量 / 连接器配置读取，**不写入仓库、不打日志**
- `accountId` 等账号信息**不入库**
- 本技能**不会代替你支付**：领券、下单等写操作都会先复述清单，等你确认
