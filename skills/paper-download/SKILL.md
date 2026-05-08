---
name: paper-download
description: |
  Use when the user asks to "download a paper", "find a paper",
  "get PDF for DOI", "下载论文", "找论文", "知网下载",
  or mentions academic paper retrieval needs.
version: 0.3.1
user-invocable: true
allowed-tools: Bash, Read, Write, WebFetch
---

# Paper Download Skill

两阶段学术论文下载：先检索收集元数据，再按成本递增逐级下载。

## 核心原则

1. **检索和下载分离** — 知网/Scholar 用于检索元数据，下载走独立的 Tier 策略
2. **确保论文匹配** — 跨源下载时必须用 DOI 或标题+作者校验，不确定时告知用户
3. **永远不主动付费** — Agent 不点击任何付费下载按钮。机构免费额度需用户授权
4. **逐级升级** — 能用 HTTP 搞定就不启动 Chrome

## 用户配置

配置文件路径：
- macOS/Linux: `~/.config/academic-skills/config.json`
- Windows: `%APPDATA%\academic-skills\config.json`

首次使用时，如果配置文件不存在，询问用户以下偏好后创建：

```json
{
  "cnki_auto_download": false,
  "download_dir": "~/Downloads/papers"
}
```

| 字段 | 含义 | 默认值 |
|------|------|--------|
| `cnki_auto_download` | 是否允许 agent 使用知网机构免费额度自动下载 | `false` |
| `download_dir` | PDF 保存目录 | `~/Downloads/papers` |

**`cnki_auto_download` 说明：**
- `false`（默认）：不在知网执行下载操作，把知网论文页链接回填到结果中并注明原因
- `true`：当机构账号有免费额度时自动下载；遇到付费页仍然停止，回填链接并标注"需付费"

## Prerequisites

Tier 2/3 需要 Chrome：
1. 调用 `check_port`（chrome-setup MCP）
2. 不可用 → `launch_chrome` 自动启动 Agent Chrome
3. 失败且提示 "Agent profile not found" → 首次设置，遵循 `references/setup-guide.md`
4. 其他错误 → `diagnose` 并告知用户

**重要：** 其他 Chrome 实例必须先退出。失败时告知用户："请先完全退出所有 Chrome 窗口，然后我再重试"

---

## 阶段一：检索（收集元数据）

目标：拿到结构化的论文列表，包含标题、作者、期刊、年份、DOI、是否 OA。

### 中文论文 → 知网检索

1. `browser_navigate` → `https://kns.cnki.net/kns8s/search`
2. 填入关键词搜索
3. 从结果中提取：标题、作者、期刊名、年份、DOI（如有）
4. OA 判断：可通过 `source=OAJ` 筛选 OA 期刊来源；或根据期刊名判断是否为已知 OA 期刊

### 英文论文 → Google Scholar

Google Scholar 覆盖面最全，作为英文论文的默认搜索引擎。

1. `browser_navigate` → `https://scholar.google.com`
2. 填入关键词或标题搜索
3. 从结果中提取：标题、作者、期刊/会议名、年份、引用数
4. 点击论文条目获取详情页链接，从中提取 DOI
5. OA 判断：结果右侧带 `[PDF]` 链接的为可直接获取的版本

**注意：** Google Scholar 反爬较严，频繁请求可能触发验证码。控制请求频率，遇到验证码提示用户在 Agent Chrome 中手动完成。

### 结果输出

- **≤10 条** → 直接在回答中展示结构化列表
- **>10 条** → 整理为 Excel（`.xlsx`），包含列：标题、作者、期刊、年份、DOI、是否OA、下载状态、下载链接/备注
- OA 论文单独标注，优先进入下载队列

---

## 阶段二：下载（逐级处理）

对检索结果中的每篇论文，按 Tier 顺序尝试下载。每个 Tier 能成功一批。

### 论文匹配校验

跨源下载时**必须校验**：
- 首选：DOI 精确匹配
- 次选：标题相似度（忽略标点/空格差异）
- 兜底：标题 + 作者 + 年份三者匹配

### Tier 1: HTTP 直接下载

无需浏览器，纯 HTTP 请求。有直接 PDF URL 的 OA 论文在这一步解决。

**来源（按顺序尝试）：**
1. arXiv: `https://arxiv.org/pdf/{id}.pdf`
2. Unpaywall: `GET https://api.unpaywall.org/v2/{doi}?email=unpaywall@example.com` → `best_oa_location.url_for_pdf`
3. Semantic Scholar: `openAccessPdf.url`（检索阶段已获取）
4. PMC: `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`
5. 期刊官网 URL 模式推断：
   - Springer: `https://link.springer.com/content/pdf/{doi}.pdf`
   - MDPI: `https://www.mdpi.com/{path}/pdf`
   - 中文 OA 期刊：多数使用 MagTech 系统，PDF URL 为 `downloadArticleFile.do?attachType=PDF&id={articleId}`
6. NSSD（国家哲学社会科学文献中心）: 社科类免费全文
7. ChinaXiv: 中国预印本平台，免费
8. Sci-Hub: `https://sci-hub.se/{doi}`（检查页面中的 PDF iframe src）

**下载方式：**
- `curl -L -o "{path}" "{url}"`
- 保存到配置的 `download_dir`
- 命名：`作者_短标题_年份.pdf`

### Tier 2: 浏览器导航（无需登录）

需要 Chrome + Playwright MCP，但全自动无人工。

**先尝试直接 PDF URL（无需浏览器）：**
1. 解析 DOI 重定向 → 出版商 URL
2. 尝试 URL 变体（append `/pdf`、替换 path segment）
3. HEAD 请求检查 Content-Type

**浏览器导航（上述失败时）：**
1. `browser_navigate` → 出版商页面或期刊官网
2. `browser_snapshot` → 读取页面结构
3. 找到 PDF 下载按钮/链接
4. `browser_click` → 触发下载（浏览器原生处理，自动带 Referer）
5. 等待下载完成

**注意：** 必须使用 Playwright 的 `browser_click` 模拟真实用户点击。不要用 JS 注入（`fetch()`、`window.open()`）——浏览器会拦截非用户发起的操作。

**Tier 2 结束后，所有 OA 论文应已下载完成。** 部分 OA 出版商（如 MDPI）会阻止直接 HTTP 下载但允许浏览器访问，所以 Tier 1 未能下载的 OA 论文在这一步补齐。

### Tier 3: 需要登录的平台

需要 Chrome 登录态。仅用于 Tier 1/2 均失败的论文。

**知网下载：**

前提条件（全部满足才执行）：
- 用户配置 `cnki_auto_download: true`
- 用户已在 Agent Chrome 中登录知网
- 机构账号有免费下载额度

流程：
1. 从检索阶段已获取的知网论文页 URL 进入
2. `browser_click` → PDF 下载按钮（让浏览器原生处理跳转）
3. 如果跳转到付费页（`fee_` 开头的 URL 或出现"余额不足"/"充值"文字）→ **立即停止**，不点任何付费按钮
4. 如果直接开始下载 → 等待完成

**其他登录平台（万方、维普等）：** 同理，有登录态且有免费额度时可尝试。

### 下载结果回填

下载完成后，更新结果列表/Excel：

| 下载状态 | 含义 |
|----------|------|
| ✓ 已下载 | PDF 已保存到 download_dir |
| ✗ 需付费 | 知网/出版商要求付费，附论文页链接 |
| ✗ 需机构权限 | 出版商要求机构登录 |
| ✗ 需手动 | 遇到验证码等需人工操作 |
| ✗ 未找到 | 所有渠道均无法获取 |

---

## CNKI 操作细节

完整流程见 `references/cnki-workflow.md`

**关键约束：**
- 知网 `bar.cnki.net` 下载系统校验 Referer 和 session，必须用 `browser_click` 从论文页面触发
- 遇到滑块验证码 → 提示用户在 Agent Chrome 中手动完成
- 登录失效 → 提示用户重新登录

## Error Escalation

所有无法解决的问题立即用中文告知用户：
- 不要静默重试超过一次
- 不要在验证码上循环
- 提供清晰的下一步指引
