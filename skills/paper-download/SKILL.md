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

# Paper Download Skill

Download academic papers through a three-tier strategy based on accessibility.

> **Note on tool names:** This skill references Playwright MCP tools like `browser_navigate`,
> `browser_snapshot`, etc. Actual tool names depend on the connected Playwright MCP version.
> Discover available tools at runtime and use the closest match.

## Environment Awareness

- **Claude Desktop (sandboxed):** Bash/curl may not be available. Use WebFetch for Tier 1 downloads. MCP tools always work.
- **Claude Code / Codex (full shell):** Bash, curl, WebFetch all available. Prefer curl for downloads.
- Detect your environment: if Bash tool is unavailable or returns permission errors, you are in a sandbox.

## Prerequisites

Before any Tier 2/3 operation, verify Chrome setup:
1. Call `check_port` (from chrome-setup MCP)
2. If unavailable → call `launch_chrome` to start Agent Chrome automatically
3. If `launch_chrome` fails with "Agent profile not found" → first-time setup needed, follow `references/setup-guide.md`
4. If `launch_chrome` fails with other errors → call `diagnose` and report to user

**Critical:** All other Chrome instances must be quit before `launch_chrome` can succeed. If it fails, tell user: "请先完全退出所有 Chrome 窗口，然后我再重试启动"

## Decision Flow

```
Input: DOI, title, URL, or topic
         │
         ├── Is it an arXiv paper? (arXiv ID or arxiv.org URL)
         │   └── YES → Tier 1: Direct PDF from https://arxiv.org/pdf/{id}.pdf
         │
         ├── Has DOI?
         │   └── YES → Check OA via Unpaywall:
         │       GET https://api.unpaywall.org/v2/{doi}?email=unpaywall@example.com
         │       ├── is_oa: true → Tier 1: Use best_oa_location.url_for_pdf
         │       └── is_oa: false → Tier 2: Try direct PDF, then browser
         │
         ├── Is it a CNKI/知网 paper?
         │   └── YES → Tier 3: CNKI workflow (see references/cnki-workflow.md)
         │
         ├── Topic search (no specific paper)?
         │   └── Search sources, then apply tier logic per result
         │
         └── User requests gray-area source?
             └── See references/gray-sources.md
```

## Tier 1: OA Direct Download

Paper has a freely accessible PDF URL.

**Sources (check in order):**
1. arXiv: `https://arxiv.org/pdf/{arxiv_id}.pdf`
2. Unpaywall: `GET https://api.unpaywall.org/v2/{doi}?email=unpaywall@example.com` → `best_oa_location.url_for_pdf`
3. Semantic Scholar: `GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf` → `openAccessPdf.url`
4. PMC: `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`

**Download method:**
- Use WebFetch to download PDF (works in all environments including sandbox)
- Or use `curl -L -o "./filename.pdf" "URL"` via Bash (non-sandbox only)
- Save to current working directory
- Naming: `FirstAuthor_ShortTitle_Year.pdf`

## Tier 2: Publisher Page Navigation

Paper is on a publisher site. **Always try direct download first before using the browser.**

**Step 1 — Try direct PDF (no browser needed):**
1. Resolve DOI: `https://doi.org/{doi}` → follow redirects to publisher URL
2. Check if the final URL or a derived URL is a direct PDF:
   - ScienceDirect: replace `/article/` with `/article/pii/.../pdf` or append `?pdf`
   - Springer: append `/fulltext.pdf`
   - Many publishers: try `Content-Type` header check via HEAD request
3. If direct PDF URL found → download with WebFetch/curl (same as Tier 1)

**Step 2 — Browser navigation (only if Step 1 fails):**

Requires: Playwright MCP connected to Agent Chrome on port 9225.

Flow:
1. `browser_navigate` → publisher URL
2. `browser_snapshot` → read page structure (accessibility tree)
3. Identify PDF download button/link
4. `browser_click` → download button
5. Wait for download

**Common publisher PDF patterns:**
- ScienceDirect: link containing `/pdfft` or "Download PDF" button
- Springer: `a[data-track-action="Download PDF"]`
- Wiley: "PDF" link in article tools
- Taylor & Francis: link with `/doi/pdf/` in href
- IEEE: "Download PDF" button

**Fallback:** If publisher blocks or requires institutional login → suggest gray-area sources or ask user about institutional access.

## Tier 3: CNKI (知网)

Requires login session in Agent Chrome.

**Full workflow:** See `references/cnki-workflow.md`

**Quick reference:**
1. Verify login: `browser_navigate` to cnki.net → check for user avatar/name
2. Search: Navigate to `https://kns.cnki.net/kns8s/search` → fill query → click search
3. Download: Click paper → click PDF download button on detail page

**Error handling:**
- Login expired → tell user "请在 Agent Chrome 中重新登录知网"
- CAPTCHA → tell user "需要手动完成验证码"
- No permission → tell user "账户没有下载权限，请确认机构账户"

## File Naming

Default: `FirstAuthor_ShortTitle_Year.pdf`
- Extract metadata from API response or page content
- Remove special characters from filename
- If metadata unavailable, use the original filename from download

## Error Escalation

All unresolvable issues immediately inform the user in Chinese:
- Never retry silently more than once
- Never loop on CAPTCHA
- Provide clear next-step instructions
