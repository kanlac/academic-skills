# Gray-Area Sources

> **Legal Notice**: These sources may violate copyright laws in some jurisdictions. 
> Use at your own discretion. The agent only uses these when explicitly requested by the user.

## Sci-Hub

Access papers by DOI.

**Current mirrors** (may change):
- https://sci-hub.se/{doi}
- https://sci-hub.st/{doi}
- https://sci-hub.ru/{doi}

**Method:**
1. Construct URL: `https://sci-hub.se/{doi}`
2. Navigate via Playwright → find PDF embed or download link
3. PDF is usually in an `<iframe>` or `<embed>` element with `.pdf` URL

**Limitations:**
- Mirrors go down frequently
- Some newer papers not available
- May require CAPTCHA

## Library Genesis (LibGen)

Aggregator of books and papers.

**Mirrors:**
- https://libgen.is
- https://libgen.rs

**Method:**
1. Search: `https://libgen.is/scimag/?q={doi_or_title}`
2. Find result in table
3. Click mirror link (Sci-Hub, LibGen, etc.)
4. Download PDF

## Anna's Archive

Meta-search across Sci-Hub, LibGen, Z-Library, and more.

**URL:** https://annas-archive.org

**Method:**
1. Search: `https://annas-archive.org/search?q={query}`
2. Filter by type: "Scientific papers"
3. Click result → download from available mirrors

## Usage Policy

The agent should:
1. Never suggest gray sources unprompted
2. Only use when user explicitly asks or all legal sources have been exhausted AND user consents
3. Inform user of legal risks before proceeding
4. Try legal sources first (Tier 1 → Tier 2 → ask user)
