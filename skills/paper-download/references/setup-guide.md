# First-Time Setup Guide

## Overview

This plugin requires two MCP servers to be configured in the user's AI client:
1. **chrome-setup** — Chrome lifecycle management (this plugin's own MCP)
2. **playwright** — Browser operations (`@playwright/mcp`, third-party)

Setup is a two-phase process:
- **Phase 1**: Configure MCP servers in the user's client → requires session restart
- **Phase 2**: Create Chrome profile, shortcut, and guide login

## Phase 1: Configure MCP Servers

### Determine the user's environment

Ask the user which client they are using, then apply the appropriate configuration method below.

### MCP server definitions

Both servers share the same semantic configuration regardless of client:

| Server | Command | Key Arguments |
|--------|---------|---------------|
| chrome-setup | `uv --directory <plugin-mcp-path> run agent-chrome-setup` | (none) |
| playwright | `npx @playwright/mcp@latest` | `--cdp-endpoint http://127.0.0.1:9225` |

Where `<plugin-mcp-path>` is the absolute path to this plugin's `mcp-servers/chrome-setup/` directory.

### Critical: Do NOT add `--isolated` to Playwright MCP

The Playwright MCP MUST connect without the `--isolated` flag. Without it, Playwright shares the browser's default context (cookies, login sessions). Adding `--isolated` creates a fresh empty context — this will break CNKI login persistence.

### Client-specific configuration

#### Claude Desktop

Config file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add/merge into `mcpServers` object:
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

Restart required: Fully quit app (Cmd+Q / right-click tray → Quit) → relaunch → start new conversation.

#### Claude Code (CLI)

```bash
claude mcp add chrome-setup -s user -- uv --directory <plugin-mcp-path> run agent-chrome-setup
claude mcp add playwright -s user -- npx @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:9225
```

Restart required: Exit current session → start new session (or use `--continue` to resume).

#### Codex CLI

Config file: `~/.codex/config.toml`

```toml
[mcp_servers.chrome-setup]
command = "uv"
args = ["--directory", "<plugin-mcp-path>", "run", "agent-chrome-setup"]

[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest", "--cdp-endpoint", "http://127.0.0.1:9225"]
```

#### Other MCP-compatible clients

Any client supporting MCP stdio transport can use these servers. The pattern is:
- chrome-setup: spawn `uv --directory <path> run agent-chrome-setup` via stdio
- playwright: spawn `npx @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:9225` via stdio

### After configuring

Tell user the appropriate restart instruction for their client:
- Claude Desktop: "请完全退出 Claude Desktop（Cmd+Q），然后重新打开，开始新对话"
- Claude Code: "请退出当前会话，重新启动 Claude Code"
- Codex: "请重启 Codex 会话"

## Phase 2: Setup Chrome Profile + Shortcut

After restart, both MCP servers should be available.

### Steps:
1. `get_status` → verify chrome-setup MCP is responding
2. `setup_profile` → create Agent Chrome profile directory
3. Tell user: "请先完全退出所有 Chrome 窗口（确保没有任何 Chrome 进程在运行）"
4. Verify ALL Chrome processes are gone:
   - macOS: `pgrep -f 'Google Chrome'` should return empty
   - Windows: `tasklist /FI "IMAGENAME eq chrome.exe"` should show no results
   - If Chrome is still running, tell user: "仍有 Chrome 进程在运行，请在 Dock 右键 Chrome 图标选择'退出'，或在活动监视器中强制退出所有 Chrome 进程"
5. `launch_chrome` → agent auto-launches Chrome with Agent profile on port 9225
   - Chrome opens as the user's own app (visible, interactive)
   - If fails, retry once after a few seconds
   - If still fails, call `diagnose` and report to user
6. `apply_profile_theme` → set profile name "Agent" and teal color (must call AFTER first launch)
7. `open_url(url="https://www.cnki.net")` → open CNKI login page
8. Tell user: "请在打开的 Chrome 窗口中登录知网账户"
9. Wait for user confirmation
10. Verify login via Playwright: `browser_navigate` to cnki.net → check login state
11. Done! Tell user: "设置完成！以后下载论文时我会自动启动 Agent Chrome。"

### Optional: Desktop shortcut
After setup, optionally create a shortcut for manual launch:
- `create_shortcut` → put "Agent Chrome" on Desktop
- macOS: run `xattr -cr` on the .app to remove quarantine

## Subsequent Usage

Each time user wants to download papers:
1. Agent calls `check_port` → if unavailable, calls `launch_chrome` automatically
2. User may need to quit regular Chrome first (agent will prompt if needed)
3. Download proceeds via the three-tier strategy

## Troubleshooting

If `launch_chrome` fails:
1. Call `diagnose` for detailed analysis
2. Common fix: user must quit ALL Chrome windows first, then agent retries `launch_chrome`
3. macOS IPv6 issue: if 127.0.0.1 fails, suggest changing Playwright MCP endpoint to `http://[::1]:9225`
4. Stale lock files: `launch_chrome` automatically cleans these, but if issues persist check `~/.config/chrome-profiles/agent/` for orphaned lock files
