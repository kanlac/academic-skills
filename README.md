# Academic Skills

学术论文下载插件。通过三层策略自动下载论文 PDF。

## 三层下载策略

| 层级 | 本质 | 手段 | 需要 Chrome |
|------|------|------|:-----------:|
| Tier 1 | 能找到直接 PDF URL | HTTP 请求（arXiv、Unpaywall、Sci-Hub、URL 模式推断） | 否 |
| Tier 2 | 有页面但需交互才能拿到 PDF | Chrome 自动导航点击（无需登录） | 是 |
| Tier 3 | 需要登录态 | Chrome + 登录 session（知网等） | 是 |

自动从 Tier 1 开始尝试，失败后逐级升级。

---

## 安装指南（Agent 引导式）

> **面向 AI agent 的安装手册。** 用户只需将以下一行发给任意支持 MCP 的 AI 客户端：
>
> ```
> 读这个安装手册帮我装好这个 skill: https://github.com/kanlac/academic-skills
> ```
>
> Agent 将自动引导完成全部配置。

---

### Agent 安装流程

以下内容面向执行安装的 AI agent。请按顺序执行，每步完成后向用户确认。

#### Step 0: 环境检测

确定用户使用的客户端：

| 客户端 | 检测方式 |
|--------|----------|
| Claude Code (CLI) | 有 Bash 工具、能跑 `claude --version` |
| Claude Desktop | 无 Bash 工具，或用户明确说明 |
| Codex CLI | 用户明确说明，或检测到 `~/.codex/` |

如果无法判断，问用户：「你用的是哪个客户端？Claude Code / Claude Desktop / Codex？」

#### Step 1: 克隆仓库

```bash
git clone https://github.com/kanlac/academic-skills.git ~/academic-skills
```

记住克隆路径，后续步骤需要。如果用户指定了其他路径则使用用户指定的。

#### Step 2: 配置 MCP 服务器

本插件需要两个 MCP server。根据客户端类型选择对应配置方式：

**重要：** `<plugin-mcp-path>` 替换为 Step 1 中的实际路径 + `/mcp-servers/chrome-setup`。Playwright MCP **不要**加 `--isolated` 参数（否则无法共享登录态）。

##### Claude Code (CLI)

```bash
claude mcp add chrome-setup -s user -- uv --directory <plugin-mcp-path> run agent-chrome-setup
claude mcp add playwright -s user -- npx @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:9225
```

##### Claude Desktop

编辑配置文件：
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

在 `mcpServers` 对象中添加：

```json
{
  "chrome-setup": {
    "command": "uv",
    "args": ["--directory", "<plugin-mcp-path>", "run", "agent-chrome-setup"]
  },
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest", "--cdp-endpoint", "http://127.0.0.1:9225"]
  }
}
```

##### Codex CLI

编辑 `~/.codex/config.toml`：

```toml
[mcp_servers.chrome-setup]
command = "uv"
args = ["--directory", "<plugin-mcp-path>", "run", "agent-chrome-setup"]

[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest", "--cdp-endpoint", "http://127.0.0.1:9225"]
```

#### Step 3: 安装插件（仅 Claude Code）

```bash
claude plugin add <clone-path>
```

Claude Desktop 和 Codex 无插件系统，跳过此步。Skill 功能通过 MCP server 和对话中的提示词实现。

#### Step 4: 重启会话

通知用户重启：

| 客户端 | 操作 |
|--------|------|
| Claude Code | 退出当前会话，重新启动 `claude` |
| Claude Desktop | 完全退出（Cmd+Q / 右键托盘→退出），重新打开，开始新对话 |
| Codex | 重启 Codex 会话 |

告诉用户：「MCP 配置完成。请重启客户端，然后在新会话中说 "帮我设置论文下载的 Chrome 环境" 来完成首次设置。」

#### Step 5: 首次 Chrome 设置（重启后的新会话中执行）

1. 调用 `get_status` 验证 chrome-setup MCP 连接正常
2. 调用 `setup_profile` 创建 Agent Chrome profile 目录
3. 告诉用户：「请先完全退出所有 Chrome 窗口」
4. 验证 Chrome 已完全退出（macOS: `pgrep -f 'Google Chrome'` 返回空）
5. 调用 `launch_chrome` 启动 Agent Chrome
6. 调用 `apply_profile_theme` 设置 profile 名称和颜色
7. 如需知网：`open_url(url="https://www.cnki.net")` → 引导用户登录
8. 完成！告诉用户可以开始使用

#### 安装完成后的使用方式

用户可以直接说：

- "下载这篇论文 https://arxiv.org/abs/2301.00001"
- "帮我找并下载：attention is all you need"
- "下载 DOI 10.1038/s41586-024-07386-0"
- "从知网下载《xxx》"

---

## 前置依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| [uv](https://docs.astral.sh/uv/) | Python 包管理 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Google Chrome | 浏览器自动化 | 系统已装即可 |
| Node.js | Playwright MCP 的 npx | `brew install node` 或 [官网](https://nodejs.org) |

## 项目结构

```
academic-skills/
├── skills/
│   └── paper-download/       # 论文下载 Skill
│       ├── SKILL.md          # 主流程定义
│       └── references/       # 参考文档
├── mcp-servers/
│   └── chrome-setup/         # Chrome 生命周期管理 MCP server
│       └── src/
└── README.md
```

## 许可

MIT
