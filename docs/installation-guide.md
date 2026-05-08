# 安装指南（AI Agent 引导式）

> 本文档面向执行安装的 AI agent。用户只需复制 README 中的提示词，agent 将全程引导完成配置。

## Step 0: 环境检测

确定用户使用的客户端：

| 客户端 | 检测方式 |
|--------|----------|
| Claude Code (CLI) | 有 Bash 工具、能跑 `claude --version` |
| Claude Desktop | 无 Bash 工具，或用户明确说明 |
| Codex CLI | 用户明确说明，或检测到 `~/.codex/` |

无法判断时询问用户。

## Step 1: 克隆仓库

```bash
git clone https://github.com/kanlac/academic-skills.git ~/academic-skills
```

记住克隆路径，后续步骤中 `<plugin-path>` 指此路径。

## Step 2: 配置 MCP 服务器

需要两个 MCP server。`<mcp-path>` = `<plugin-path>/mcp-servers/chrome-setup`

**重要：** Playwright MCP **不要**加 `--isolated` 参数，否则无法共享 Chrome 登录态。

### Claude Code (CLI)

```bash
claude mcp add chrome-setup --scope user -- uv --directory <mcp-path> run agent-chrome-setup
claude mcp add playwright --scope user -- npx @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:9225
```

### Claude Desktop

配置文件位置：
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

在 `mcpServers` 中添加：

```json
{
  "chrome-setup": {
    "command": "uv",
    "args": ["--directory", "<mcp-path>", "run", "agent-chrome-setup"]
  },
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest", "--cdp-endpoint", "http://127.0.0.1:9225"]
  }
}
```

### Codex CLI

编辑 `~/.codex/config.toml`：

```toml
[mcp_servers.chrome-setup]
command = "uv"
args = ["--directory", "<mcp-path>", "run", "agent-chrome-setup"]

[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest", "--cdp-endpoint", "http://127.0.0.1:9225"]
```

## Step 3: 安装插件（仅 Claude Code）

```bash
claude plugin add <plugin-path>
```

其他客户端无插件系统，跳过。

## Step 4: 重启客户端

| 客户端 | 操作 |
|--------|------|
| Claude Code | 退出当前会话，重新启动 |
| Claude Desktop | Cmd+Q 完全退出后重新打开 |
| Codex | 重启会话 |

告知用户重启后在新会话中说 **"帮我设置论文下载的 Chrome 环境"** 完成首次设置。

## Step 5: 首次 Chrome 设置（新会话中执行）

1. `get_status` — 验证 chrome-setup MCP 连接
2. `setup_profile` — 创建 Agent Chrome profile
3. 提示用户退出所有 Chrome 窗口
4. 验证 Chrome 已退出（`pgrep -f 'Google Chrome'` 应为空）
5. `launch_chrome` — 启动 Agent Chrome（端口 9225）
6. `apply_profile_theme` — 设置 profile 名称和主题色
7. 如需知网：`open_url(url="https://www.cnki.net")` → 引导用户登录
8. 完成

## 前置依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| [uv](https://docs.astral.sh/uv/) | Python 包管理 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Google Chrome | 浏览器自动化 | 系统自带或官网下载 |
| Node.js | Playwright MCP | `brew install node` 或 [nodejs.org](https://nodejs.org) |

## 故障排查

| 问题 | 解决 |
|------|------|
| `launch_chrome` 失败 | 确保所有 Chrome 窗口已退出，再重试 |
| Playwright 连不上 Chrome | 检查端口 9225 是否在监听：`curl http://127.0.0.1:9225/json/version` |
| macOS IPv6 问题 | 将 Playwright 端点改为 `http://[::1]:9225` |
| 知网登录失效 | 在 Agent Chrome 中重新访问 cnki.net 登录 |
