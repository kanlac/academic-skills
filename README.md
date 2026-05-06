# Academic Skills

Claude Code 插件：学术论文下载助手。通过三层策略自动下载论文 PDF。

## 三层下载策略

| 层级 | 方式 | 适用场景 | 需要 Chrome？ |
|------|------|----------|:---:|
| Tier 1 | HTTP 直接下载 | arXiv、OA 期刊（Unpaywall） | 否 |
| Tier 2 | 浏览器导航点击 | 有 anti-bot 保护的出版商页面 | 是 |
| Tier 3 | 浏览器 + 登录态 | 知网等需要账号的数据库 | 是 |

自动从 Tier 1 开始尝试，失败后逐级升级。

## 安装

### 前置条件

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- [uv](https://docs.astral.sh/uv/) (Python 包管理)
- Google Chrome
- Node.js (用于 Playwright MCP 的 npx)

### 1. 克隆仓库

```bash
git clone https://github.com/kanlac/academic-skills.git
```

### 2. 安装为 Claude Code 插件

```bash
claude plugin add /path/to/academic-skills
```

### 3. 配置 MCP 服务器

需要两个 MCP server：

```bash
# Chrome 生命周期管理（本插件提供）
claude mcp add chrome-setup -s user -- uv --directory /path/to/academic-skills/mcp-servers/chrome-setup run agent-chrome-setup

# Playwright 浏览器操作（第三方）
claude mcp add playwright -s user -- npx @playwright/mcp@latest --cdp-endpoint http://127.0.0.1:9225
```

> **注意：** Playwright MCP 不要加 `--isolated` 参数，否则无法共享登录态。

### 4. 重启 Claude Code

```bash
# 退出当前会话，重新启动
claude
```

### 5. 首次设置 Chrome Profile

在新会话中告诉 Claude：

> "帮我设置论文下载环境"

Claude 会自动：
1. 创建 Agent Chrome 专用 profile
2. 启动带调试端口的 Chrome
3. 引导你登录知网（如需要）

## 使用

直接对 Claude 说：

- "下载这篇论文 https://arxiv.org/abs/2301.00001"
- "帮我找并下载：attention is all you need"
- "下载 DOI 10.1038/s41586-024-07386-0"

## 项目结构

```
academic-skills/
├── skills/
│   └── paper-download/       # 论文下载 Skill
│       ├── SKILL.md          # 主流程定义
│       └── references/       # 参考文档
├── mcp-servers/
│   └── chrome-setup/         # Chrome 管理 MCP server
│       └── src/
└── README.md
```

## 许可

MIT
