# Academic Paper Download Plugin - Design Document v1

> Date: 2026-05-06  
> Status: Approved  
> Target Users: Chinese university faculty and students

---

## 1. Overview

A Claude Code plugin for downloading academic papers, supporting three tiers of complexity:

| Tier | Scenario | Mechanism |
|------|----------|-----------|
| **Tier 1** | OA papers with direct PDF links | Agent uses WebFetch / curl |
| **Tier 2** | Publisher pages requiring navigation | Playwright MCP |
| **Tier 3** | CNKI (知网) requiring login | Playwright MCP + persistent Chrome profile |

The plugin consists of:
- **1 custom MCP server** (`chrome-setup`): Chrome lifecycle management (Python)
- **1 skill** (`paper-download`): Paper download methodology + reference docs
- **1 third-party dependency**: `@playwright/mcp` for browser operations

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Desktop / Claude Code           │
│  ┌───────────────────────────────────────────────────┐  │
│  │                    Agent (Sandbox)                  │  │
│  │                                                    │  │
│  │  ┌──────────────┐   ┌───────────────────────────┐│  │
│  │  │ Skill:       │   │ Decision Logic:            ││  │
│  │  │ paper-download│   │ DOI? → check OA → Tier 1  ││  │
│  │  │ (methodology)│   │ Publisher? → Tier 2        ││  │
│  │  │              │   │ CNKI? → Tier 3             ││  │
│  │  └──────────────┘   └───────────────────────────┘│  │
│  └────────────┬──────────────────────┬───────────────┘  │
│               │ MCP calls            │ MCP calls         │
│  ┌────────────▼────────┐  ┌─────────▼──────────────┐   │
│  │ chrome-setup MCP    │  │ Playwright MCP          │   │
│  │ (Python, sandbox外) │  │ (@playwright/mcp)       │   │
│  │                     │  │ --cdp-endpoint          │   │
│  │ • check_port        │  │   http://127.0.0.1:9225 │   │
│  │ • setup_profile     │  │                         │   │
│  │ • create_shortcut   │  │ • browser_navigate      │   │
│  │ • get_status        │  │ • browser_click         │   │
│  │ • diagnose          │  │ • browser_fill          │   │
│  │ • open_url          │  │ • browser_snapshot      │   │
│  └─────────────────────┘  │ • browser_evaluate      │   │
│                            │ • browser_take_screenshot│  │
│                            └────────────┬────────────┘   │
│                                         │ CDP            │
│  ┌──────────────────────────────────────▼────────────┐  │
│  │         Chrome (port 9225, Agent profile)          │  │
│  │         User manually launches via shortcut        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Plugin Structure

```
academic-paper-plugin/
├── .claude-plugin/
│   └── plugin.json                 # Plugin manifest
├── mcp-servers/
│   └── chrome-setup/
│       ├── pyproject.toml          # Python package (uv compatible)
│       ├── src/
│       │   └── chrome_setup/
│       │       ├── __init__.py
│       │       ├── server.py       # FastMCP server entry
│       │       ├── port.py         # Port check + CDP version query
│       │       ├── profile.py      # Profile directory creation + color config
│       │       ├── shortcut.py     # Desktop shortcut (.app / .lnk)
│       │       └── platform.py     # OS detection + Chrome path resolution
│       └── README.md
├── skills/
│   └── paper-download/
│       ├── SKILL.md                # Main methodology
│       └── references/
│           ├── tier-decision.md    # Tier classification logic
│           ├── cnki-workflow.md    # CNKI operation guide
│           ├── sources.md          # Paper source catalog
│           ├── setup-guide.md      # First-time setup instructions
│           └── gray-sources.md     # Sci-Hub/LibGen/Z-Library guide
└── README.md
```

---

## 4. MCP Server: `chrome-setup`

### 4.1 Technology

- **Language**: Python 3.10+
- **MCP SDK**: `mcp` (FastMCP pattern)
- **Package manager**: `uv` (recommended) or `pip`
- **Zero external dependencies** beyond `mcp` SDK — uses only stdlib (`pathlib`, `subprocess`, `json`, `socket`, `platform`, `shutil`)

### 4.2 Tools

#### `check_port`

检测 9225 端口是否有 CDP Chrome 响应。

```python
@mcp.tool()
async def check_port() -> dict:
    """Check if Chrome CDP is available on port 9225."""
    # Returns:
    # {
    #   "available": true/false,
    #   "browser_version": "Chrome/147.0.7727.138" | null,
    #   "ws_url": "ws://127.0.0.1:9225/devtools/browser/..." | null,
    #   "error": null | "connection_refused" | "timeout" | "not_cdp"
    # }
```

实现：HTTP GET `http://127.0.0.1:9225/json/version`，解析 JSON 响应。macOS 同时尝试 `[::1]:9225`（IPv6 fallback）。

#### `setup_profile`

创建 Agent Chrome profile 目录，预配置名称和颜色。

```python
@mcp.tool()
async def setup_profile(
    profile_name: str = "Paper Agent",
    color: str = "teal"  # teal | purple | orange | green | red
) -> dict:
    """Create a dedicated Chrome profile for agent use."""
    # Creates: ~/.config/chrome-profiles/agent/chrome-profile/
    # Writes: Local State + Default/Preferences with color config
    # Creates: "First Run" sentinel to skip welcome
    # Returns:
    # {
    #   "success": true,
    #   "profile_path": "~/.config/chrome-profiles/agent/chrome-profile",
    #   "profile_name": "Paper Agent",
    #   "color": "teal",
    #   "already_existed": false
    # }
```

Profile 数据目录：
- macOS: `~/.config/chrome-profiles/agent/`
- Windows: `%USERPROFILE%\.config\chrome-profiles\agent\`

颜色映射（ARGB signed int）：

| Color | Seed Value | Visual |
|-------|-----------|--------|
| teal | -16745597 | 青色标题栏 |
| purple | -8708190 | 紫色标题栏 |
| orange | -1543926 | 橙色标题栏 |
| green | -15753896 | 绿色标题栏 |
| red | -2543579 | 红色标题栏 |

#### `create_shortcut`

生成桌面快捷方式，启动带调试端口的 Chrome。

```python
@mcp.tool()
async def create_shortcut(
    location: str = "desktop"  # "desktop" | "dock" (mac only)
) -> dict:
    """Create a desktop shortcut to launch Chrome with CDP on port 9225."""
    # macOS: Creates ~/Desktop/Agent Chrome.app/ (or adds to Dock)
    #   - Info.plist + launcher script
    #   - launcher script calls: open -na "Google Chrome" --args \
    #       --remote-debugging-port=9225 \
    #       --user-data-dir=~/.config/chrome-profiles/agent/chrome-profile \
    #       --no-first-run --no-default-browser-check
    #
    # Windows: Creates ~/Desktop/Agent Chrome.lnk
    #   - Target: chrome.exe
    #   - Arguments: --remote-debugging-port=9225 --user-data-dir=...
    #
    # Returns:
    # {
    #   "success": true,
    #   "shortcut_path": "~/Desktop/Agent Chrome.app",
    #   "platform": "darwin",
    #   "chrome_path": "/Applications/Google Chrome.app/..."
    # }
```

Chrome 可执行文件探测顺序：

**macOS:**
1. `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
2. `/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary`
3. `/Applications/Chromium.app/Contents/MacOS/Chromium`

**Windows:**
1. `C:\Program Files\Google\Chrome\Application\chrome.exe`
2. `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
3. `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`

#### `get_status`

综合状态检查。

```python
@mcp.tool()
async def get_status() -> dict:
    """Get complete setup status."""
    # Returns:
    # {
    #   "profile_exists": true/false,
    #   "profile_path": "...",
    #   "shortcut_exists": true/false,
    #   "shortcut_path": "...",
    #   "port_available": true/false,
    #   "browser_version": "..." | null,
    #   "platform": "darwin" | "win32",
    #   "chrome_found": true/false,
    #   "chrome_path": "...",
    #   "setup_complete": true/false  # all above are true
    # }
```

#### `diagnose`

诊断连接问题并给出修复建议。

```python
@mcp.tool()
async def diagnose() -> dict:
    """Diagnose connection issues and provide fix suggestions."""
    # Checks:
    # 1. Is Chrome installed? → If not: "请安装 Google Chrome"
    # 2. Is profile directory intact? → If corrupted: offer to recreate
    # 3. Is port 9225 occupied by non-Chrome? → "端口被其他程序占用"
    # 4. Is Chrome running without debug port? → "请完全退出 Chrome，使用专用快捷方式启动"
    # 5. Is Chrome running with debug port but wrong profile? → warn
    # 6. IPv6 issue? (macOS) → suggest [::1]
    #
    # Returns:
    # {
    #   "issues": [
    #     {"code": "chrome_not_running", "message": "...", "fix": "..."},
    #     ...
    #   ],
    #   "healthy": true/false
    # }
```

#### `open_url`

在 Agent Chrome 中打开指定 URL（要求 Chrome 已在运行）。

```python
@mcp.tool()
async def open_url(url: str) -> dict:
    """Open a URL in the Agent Chrome instance (requires Chrome running on port 9225)."""
    # Implementation: HTTP PUT to http://127.0.0.1:9225/json/new?{url}
    # Returns:
    # {
    #   "success": true,
    #   "tab_id": "...",
    #   "url": "https://..."
    # }
```

### 4.3 MCP Configuration

#### Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "chrome-setup": {
      "command": "uv",
      "args": ["run", "--from", "agent-chrome-setup", "agent-chrome-setup"]
    },
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--cdp-endpoint",
        "http://127.0.0.1:9225"
      ]
    }
  }
}
```

#### Claude Code:

```bash
claude mcp add chrome-setup -- uv run --from agent-chrome-setup agent-chrome-setup
claude mcp add playwright -- npx @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:9225
```

---

## 5. Skill: `paper-download`

### 5.1 SKILL.md Overview

```yaml
---
name: paper-download
description: |
  Use when the user asks to "download a paper", "find a paper",
  "get PDF for DOI", "下载论文", "找论文", "知网下载",
  or mentions academic paper retrieval needs.
version: 0.1.0
user-invocable: true
allowed-tools: Bash, Read, Write, WebFetch
---
```

### 5.2 Skill Workflow (Decision Tree)

```
User Request
    │
    ├─ Has DOI? ──────────────────────────────────┐
    │                                              ▼
    │                                    Check OA status
    │                                    (Unpaywall API via WebFetch)
    │                                         │
    │                              ┌──────────┴──────────┐
    │                              ▼                      ▼
    │                         OA available            Not OA
    │                              │                      │
    │                              ▼                      ▼
    │                      Tier 1: Direct           Tier 2: Publisher
    │                      download PDF             page navigation
    │
    ├─ Chinese paper / CNKI? ─────────────────────── Tier 3: CNKI flow
    │
    ├─ Topic search? ─────────────────────────────── Search sources,
    │                                                 then per-result
    │                                                 apply tier logic
    │
    └─ Gray-area request? ────────────────────────── Gray source guide
```

### 5.3 Tier 1: OA Direct Download

**When**: Paper has a freely accessible PDF URL (arXiv, PubMed Central, OA journals, Unpaywall hit).

**Method**: Agent uses WebFetch or curl to download the PDF directly.

**Key sources checked (in order)**:
1. **Unpaywall**: `GET https://api.unpaywall.org/v2/{doi}?email=user@example.com`
   - If `is_oa: true` → use `best_oa_location.url_for_pdf`
2. **Semantic Scholar**: `GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf`
3. **arXiv**: If arXiv ID available → `https://arxiv.org/pdf/{id}.pdf`
4. **PMC**: If PMCID available → `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`

**Download**:
```bash
# Agent executes (if Bash available):
curl -L -o "./paper_title.pdf" "https://..."

# Or via WebFetch (if in sandbox):
WebFetch(url, save_to="./paper_title.pdf")
```

**File naming**: `FirstAuthor_ShortTitle_Year.pdf` (agent decides based on metadata).

**Save location**: Current working directory (user's project folder in Claude Desktop).

### 5.4 Tier 2: Publisher Page Navigation

**When**: Paper exists on a publisher site with accessible PDF (institutional access via IP, or free-to-read but requires JS navigation).

**Method**: Playwright MCP navigates to the publisher page, finds the PDF link, downloads.

**Typical flow**:
1. Agent calls `browser_navigate` to publisher page (e.g., ScienceDirect, Springer, Wiley)
2. Agent calls `browser_snapshot` to read page structure
3. Agent identifies PDF download button/link
4. Agent calls `browser_click` on the PDF link
5. PDF downloads to Chrome's download directory

**Common publisher patterns** (documented in `references/sources.md`):
- ScienceDirect: `.pdf-download-btn-link`
- Springer: `a[data-track-action="Download PDF"]`
- Wiley: `a.article-tool__pdf`
- Taylor & Francis: `a[href*="/doi/pdf/"]`

**Fallback**: If publisher blocks or requires login the agent doesn't have → suggest user try gray-area sources or check institutional access.

### 5.5 Tier 3: CNKI (知网) Flow

**When**: User explicitly asks for CNKI paper, or paper is only available on CNKI.

**Prerequisites check** (agent must verify before proceeding):
1. Call `get_status` → confirm `setup_complete: true`
2. Call `check_port` → confirm Chrome is running
3. If not ready → guide user through setup (see Section 7)

**CNKI workflow** (via Playwright MCP):

```
1. browser_navigate → https://www.cnki.net
2. browser_snapshot → check login status
   ├─ If logged in → proceed to search
   └─ If not logged in → STOP, tell user:
      "知网登录已失效，请在 Agent Chrome 中重新登录知网"
3. browser_navigate → https://kns.cnki.net/kns8s/search
4. browser_fill → search box with query
5. browser_click → search button
6. browser_snapshot → read results
7. browser_click → target paper
8. browser_snapshot → paper detail page
9. browser_click → PDF download button
10. Wait for download to complete
```

**Known issues & handling**:
- **Tencent slider CAPTCHA**: Agent detects via `#tcaptcha_transform_dy` visibility. Cannot solve automatically → pause and ask user.
- **Login expired**: Detect "请登录" text → inform user, open CNKI login page.
- **No download permission**: Detect "您的机构没有该资源的使用权限" → inform user to check institutional account.
- **CAJ only (no PDF)**: Some papers only offer CAJ format → inform user, suggest converting or trying other sources.

### 5.6 Gray-Area Sources

**Included sources** (3-5, user-enabled):

| Source | Coverage | Access Method |
|--------|----------|---------------|
| Sci-Hub | ~85M papers | DOI → `https://sci-hub.se/{doi}` |
| LibGen | Books + papers | Search → download link |
| Anna's Archive | Aggregator of above | Search → mirrors |

**Skill treatment**: Document URLs and access patterns in `references/gray-sources.md`. Agent only uses these when:
1. User explicitly requests, OR
2. All legal tiers failed and user consents

**Legal disclaimer**: Skill documents that these sources may violate copyright in some jurisdictions. Decision left to user.

---

## 6. Chrome Setup: First-Time Flow

### 6.1 The Two-Session Problem

Since MCP configuration requires app restart, the first-time setup is a **cross-session process**:

**Session 1 (Setup)**:
```
1. Skill detects: chrome-setup MCP not available
2. Skill guides agent to:
   a. Write MCP config to claude_desktop_config.json (chrome-setup + playwright)
   b. Tell user: "配置已写入，请完全退出 Claude Desktop 后重新打开"
```

**Session 2 (Profile + Shortcut + Login)**:
```
1. Agent calls get_status → confirms MCP is available
2. Agent calls setup_profile → creates Chrome profile
3. Agent calls create_shortcut → puts shortcut on Desktop
4. Agent tells user: "请使用桌面上的 'Agent Chrome' 快捷方式启动 Chrome"
5. User launches Chrome via shortcut
6. Agent calls check_port → confirms Chrome is running
7. Agent calls open_url(url="https://login.cnki.net") → opens CNKI login
8. Agent tells user: "请在打开的 Chrome 窗口中登录知网"
9. User logs in → cookies persist in Agent profile
10. Agent calls browser_navigate + browser_snapshot → verifies login success
11. Setup complete!
```

### 6.2 Subsequent Sessions

```
1. User launches "Agent Chrome" (shortcut)
2. Opens Claude Desktop, starts conversation
3. Invokes paper-download skill
4. Agent calls check_port → Chrome is running, all good
5. Proceeds with paper download workflow
```

### 6.3 Session 1 Detail: Writing MCP Config

The skill (in SKILL.md) instructs the agent to write config. No MCP needed for this step — agent uses its file editing tools:

**macOS** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "chrome-setup": {
      "command": "uv",
      "args": ["run", "--from", "agent-chrome-setup", "agent-chrome-setup"]
    },
    "playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--cdp-endpoint",
        "http://127.0.0.1:9225"
      ]
    }
  }
}
```

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
Same content, different file path.

---

## 7. Cross-Platform Support

### 7.1 Platform Detection

```python
import platform

def get_platform() -> str:
    system = platform.system()
    if system == "Darwin":
        return "darwin"
    elif system == "Windows":
        return "win32"
    else:
        return "linux"
```

### 7.2 Path Conventions

| Item | macOS | Windows |
|------|-------|---------|
| Chrome executable | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` | `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| Agent profile | `~/.config/chrome-profiles/agent/` | `%USERPROFILE%\.config\chrome-profiles\agent\` |
| Desktop shortcut | `~/Desktop/Agent Chrome.app/` | `%USERPROFILE%\Desktop\Agent Chrome.lnk` |
| Claude Desktop config | `~/Library/Application Support/Claude/claude_desktop_config.json` | `%APPDATA%\Claude\claude_desktop_config.json` |
| Download location | Current working directory | Current working directory |

### 7.3 macOS .app Bundle

```
Agent Chrome.app/
  Contents/
    Info.plist
    MacOS/
      launcher    # chmod +x shell script
```

`launcher`:
```bash
#!/bin/bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE="$HOME/.config/chrome-profiles/agent/chrome-profile"
exec "$CHROME" \
  --remote-debugging-port=9225 \
  --user-data-dir="$PROFILE" \
  --no-first-run \
  --no-default-browser-check
```

### 7.4 Windows .lnk Shortcut

Created via Python `subprocess` calling PowerShell:
```python
script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{chrome_path}"
$Shortcut.Arguments = '--remote-debugging-port=9225 --user-data-dir="{profile_path}" --no-first-run --no-default-browser-check'
$Shortcut.Description = "Agent Chrome (CDP port 9225)"
$Shortcut.Save()
'''
subprocess.run(["powershell", "-Command", script], check=True)
```

---

## 8. Playwright MCP Integration

### 8.1 Connection Mode

- Flag: `--cdp-endpoint http://127.0.0.1:9225`
- **不使用 `--isolated`**：直接使用 Chrome 的默认 browser context，保留所有 cookies/登录态
- macOS IPv6 fallback: 如果 `127.0.0.1` 连不上，skill 引导用户改配置为 `http://[::1]:9225`

### 8.2 Available Capabilities

When connected via CDP to existing Chrome:

| Feature | Works? | Notes |
|---------|--------|-------|
| Navigation | Yes | |
| Click/Fill/Type | Yes | |
| Screenshots | Yes | |
| Page snapshot (accessibility tree) | Yes | Primary interaction method |
| JavaScript evaluation | Yes | |
| File downloads | Yes | Downloads to Chrome's configured path |
| Tab management | Yes | |
| Cookie access | Yes | Via `--caps=storage` |
| Device emulation | No | Not supported with CDP |
| Video recording | No | Not supported with CDP |

### 8.3 Key Playwright MCP Tools Used by Skill

| Tool | Usage |
|------|-------|
| `browser_navigate` | Go to CNKI/publisher URL |
| `browser_snapshot` | Read page structure (accessibility tree, better than screenshot) |
| `browser_click` | Click buttons, links |
| `browser_fill` | Fill search boxes |
| `browser_evaluate` | Run custom JS (batch operations, complex extraction) |
| `browser_take_screenshot` | Visual debugging, CAPTCHA detection |
| `browser_wait_for` | Wait for page load, element appearance |
| `browser_tabs` | Manage multiple open tabs |

---

## 9. Error Handling & User Communication

### 9.1 Error Categories

| Error | Detection | Response |
|-------|-----------|----------|
| Chrome not running | `check_port` returns `available: false` | "请使用桌面快捷方式启动 Agent Chrome" |
| CNKI login expired | Page contains "请登录" | "知网登录已失效，请在 Agent Chrome 中重新登录" |
| CNKI no permission | "没有该资源的使用权限" | "您的账户没有下载权限，请确认机构账户有效" |
| CAPTCHA triggered | `#tcaptcha_transform_dy` visible | "需要验证码，请在 Chrome 窗口中手动完成验证" |
| PDF not available | Only CAJ format | "该论文仅提供 CAJ 格式，建议尝试其他来源" |
| Network error | Request timeout | Retry once, then report to user |
| Port conflict | 9225 occupied by non-Chrome | "端口 9225 被其他程序占用，请关闭占用程序" |

### 9.2 Principle

All unresolvable issues **immediately escalate to user** with clear Chinese instructions. Agent never loops or retries silently more than once.

---

## 10. Skill References Structure

### `references/tier-decision.md`

Documents the decision logic for choosing download tier:
- DOI-based OA check flow
- Source identification (arXiv, CNKI, publisher)
- Fallback chain: Tier 1 → Tier 2 → Tier 3 → Gray sources

### `references/cnki-workflow.md`

Complete CNKI operation guide:
- Search page URL and selectors
- Result list parsing
- Paper detail page structure
- Download button identification
- CAPTCHA detection and handling
- Login verification method
- Batch download patterns (via `evaluate_script`)

### `references/sources.md`

Catalog of paper sources with:
- URL patterns
- OA status
- API availability
- PDF access method
- Rate limits
- Coverage (disciplines, volume)

### `references/setup-guide.md`

First-time setup instructions for the skill to follow:
- Session 1 vs Session 2 flow
- Config file locations per platform
- Verification steps

### `references/gray-sources.md`

Gray-area source documentation:
- Sci-Hub current mirrors and DOI resolution
- LibGen search and download patterns
- Anna's Archive unified search
- Legal disclaimer text

---

## 11. Future Extensions (Not in v1)

| Feature | Description | Priority |
|---------|-------------|----------|
| API search tools | Unified multi-source search via WebFetch (Unpaywall, OpenAlex, CrossRef, CORE, Semantic Scholar) | High |
| Batch download | Download multiple papers from a list of DOIs | Medium |
| Citation export | Export to BibTeX/RIS/GB/T 7714 | Medium |
| Wanfang/CQVIP support | Additional Chinese academic sources | Low |
| Zotero integration | Push to Zotero library | Low |
| Local paper index | SQLite DB of downloaded papers | Low |

---

## 12. Installation & Distribution

### 12.1 MCP Server (PyPI)

```bash
# Install
uv pip install agent-chrome-setup

# Or run directly
uv run --from agent-chrome-setup agent-chrome-setup
```

Package name: `agent-chrome-setup`  
Entry point: `agent-chrome-setup` (console_scripts)

### 12.2 Plugin (Claude Code)

```bash
# Install from registry or local path
claude plugin add academic-paper
```

Or manual: clone repo, add to `~/.claude/plugins/`.

### 12.3 Dependencies

| Component | Requires |
|-----------|----------|
| chrome-setup MCP | Python 3.10+, `mcp` SDK, `uv` (recommended) |
| Playwright MCP | Node.js 18+, `npx` |
| Chrome | Google Chrome (any recent version) |
| Skill | No additional dependencies |

---

## 13. Security Considerations

1. **No credentials in conversation**: CNKI login happens in browser, agent never sees password
2. **Profile isolation**: Agent Chrome profile is separate from user's daily Chrome
3. **No persistent tokens stored by MCP**: All auth state lives in Chrome profile cookies
4. **Port binding**: `127.0.0.1:9225` is localhost-only, not network-exposed
5. **Gray sources opt-in**: Agent only uses Sci-Hub/LibGen when user explicitly consents
6. **Download validation**: Agent checks file size > 0 and content-type is PDF before reporting success

---

## 14. Confirmed Decisions

| Item | Decision |
|------|----------|
| Profile directory | `~/.config/chrome-profiles/agent/` (Win: `%USERPROFILE%\.config\chrome-profiles\agent\`) |
| Shortcut name | "Agent Chrome" |
| Default color | Teal |
| IPv6 | Auto-detect, try both `127.0.0.1` and `[::1]` |
| `open_url` tool | Keep |
| Package name | `agent-chrome-setup` |
