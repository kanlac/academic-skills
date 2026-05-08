---
name: paper-download
description: |
  Use when the user asks to "download a paper", "find a paper",
  "get PDF for DOI", "下载论文", "找论文", "知网下载",
  or mentions academic paper retrieval needs.
version: 0.2.0
user-invocable: true
allowed-tools: Bash, Read, Write, WebFetch
---

# Paper Download Skill

通过三层策略下载学术论文 PDF，按成本递增逐级尝试。

## 核心原则

1. **知网用于检索，不用于下载** — 知网是中文论文元数据最全的源，但下载优先走期刊官网或 OA 渠道
2. **确保论文匹配** — 跨源下载时必须用 DOI 或标题+作者校验，绝不能下错论文
3. **逐级升级，懒加载** — 能用 HTTP 搞定就不启动 Chrome

## 环境感知

- **Claude Desktop（沙箱）:** 无 Bash，用 WebFetch 下载，MCP 工具可用
- **Claude Code / Codex（完整 shell）:** Bash + curl + WebFetch 均可用，优先 curl
- 检测方式：Bash 工具不可用或返回权限错误 → 沙箱环境

## Prerequisites

Tier 2/3 需要 Chrome：
1. 调用 `check_port`（chrome-setup MCP）
2. 不可用 → `launch_chrome` 自动启动 Agent Chrome
3. 失败且提示 "Agent profile not found" → 首次设置，遵循 `references/setup-guide.md`
4. 其他错误 → `diagnose` 并告知用户

**重要：** 其他 Chrome 实例必须先退出。失败时告知用户："请先完全退出所有 Chrome 窗口，然后我再重试"

## Decision Flow

```
输入：DOI、标题、URL 或关键词
    │
    ├─ arXiv 论文？ → Tier 1 直下
    │
    ├─ 有 DOI？
    │   ├─ Unpaywall 检查 OA → 有 PDF URL → Tier 1
    │   ├─ 期刊官网 URL 模式推断 → Tier 1
    │   └─ 以上失败 → Tier 2 浏览器导航
    │
    ├─ 中文论文 / 知网论文？
    │   ├─ Step 1: 知网检索 → 获取元数据（DOI、期刊名、年卷期）
    │   ├─ Step 2: 有 DOI → 回到 Tier 1/2 从期刊官网下载
    │   ├─ Step 3: 无 DOI → 用标题在期刊官网搜索（Tier 2）
    │   └─ Step 4: 以上全部失败 → 知网付费下载（Tier 3，最后手段）
    │
    └─ 关键词搜索（无具体论文）？
        └─ 搜索后对每条结果应用上述逻辑
```

## 论文匹配校验

跨源下载时**必须校验**：
- 首选：DOI 精确匹配
- 次选：标题相似度 > 90%（忽略标点/空格差异）
- 兜底：标题 + 作者 + 年份三者匹配
- **下载后确认**：PDF 文件名或首页内容是否对应目标论文

绝不能默默交付一篇错误的论文。不确定时告知用户。

## Tier 1: HTTP 直接下载

无需浏览器，纯 HTTP 请求。

**来源（按顺序尝试）：**
1. arXiv: `https://arxiv.org/pdf/{id}.pdf`
2. Unpaywall: `GET https://api.unpaywall.org/v2/{doi}?email=unpaywall@example.com` → `best_oa_location.url_for_pdf`
3. Semantic Scholar: `GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf`
4. PMC: `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`
5. 期刊官网 URL 模式：
   - Springer: `https://link.springer.com/content/pdf/{doi}.pdf`
   - MDPI: `https://www.mdpi.com/{path}/pdf`
   - 中文 OA 期刊: MagTech 系统 `downloadArticleFile.do?attachType=PDF&id={articleId}`
6. Sci-Hub: `https://sci-hub.se/{doi}` （检查页面中的 PDF iframe src）

**下载方式：**
- 优先 `curl -L -o "./filename.pdf" "URL"`
- 沙箱中用 WebFetch
- 命名：`作者_短标题_年份.pdf`

## Tier 2: 浏览器导航（无需登录）

需要 Chrome + Playwright MCP，但全自动。

**先尝试直接 PDF URL（无需浏览器）：**
1. 解析 DOI 重定向 → 出版商 URL
2. 尝试 URL 变体（append `/pdf`、替换 path segment）
3. HEAD 请求检查 Content-Type

**浏览器导航（上述失败时）：**
1. `browser_navigate` → 出版商页面
2. `browser_snapshot` → 读取页面结构
3. 找到 PDF 下载按钮/链接
4. `browser_click` → 触发下载（浏览器原生处理，自动带 Referer）
5. 等待下载完成

**注意：** 必须使用 Playwright 的 `browser_click` 模拟真实用户点击。不要用 JS 注入（`fetch()`、`window.open()`）——浏览器会拦截非用户发起的操作。

## Tier 3: 知网付费下载（最后手段）

仅在以下条件全部满足时使用：
- 论文确实只有知网有（无 DOI、期刊官网无法下载）
- 用户已登录且有下载额度
- Tier 1/2 均失败

**流程：** 见 `references/cnki-workflow.md`

**关键：** 在知网页面点击 PDF 下载按钮时，使用 `browser_click` 让浏览器原生处理跳转。知网的 `bar.cnki.net` 下载系统会校验 Referer 和 session，任何 JS 注入方式都会被拦截。

## 中文论文特殊流程

中文论文的最优路径：

```
知网检索（获取元数据）
    │
    ├─ 提取 DOI → doi.org 解析到期刊官网 → 下载
    │
    ├─ 无 DOI，但知道期刊名
    │   ├─ 搜索期刊官网（多数中文期刊用 MagTech/ScholarOne 系统）
    │   └─ 在官网用标题搜索 → PDF 全文下载（OA 期刊免费）
    │
    └─ 以上全部失败 → 知网付费下载
```

**为什么不直接从知网下载？** 知网对所有 PDF 下载统一收费，即使论文来自 OA 期刊。同一篇论文在期刊官网免费，在知网要 ¥6+。

## Error Escalation

所有无法解决的问题立即用中文告知用户：
- 不要静默重试超过一次
- 不要在验证码上循环
- 提供清晰的下一步指引
