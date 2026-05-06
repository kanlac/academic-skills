# Tier Decision Guide

## Quick Classification

| Signal | Tier | Reason |
|--------|------|--------|
| arXiv ID (e.g., 2301.12345) | 1 | Always free PDF |
| DOI + Unpaywall says OA | 1 | Direct PDF link available |
| PMC ID (PMC1234567) | 1 | PubMed Central free access |
| DOI + not OA + known publisher | 2 | Need to navigate publisher page |
| CNKI / 知网 / Chinese journal | 3 | Requires CNKI login |
| User says "用知网下" | 3 | Explicit CNKI request |
| User mentions Sci-Hub / LibGen | Gray | User-initiated gray source |

## OA Detection via Unpaywall

```
GET https://api.unpaywall.org/v2/{doi}?email=unpaywall@example.com
```

Response fields to check:
- `is_oa`: boolean — is the paper open access?
- `best_oa_location.url_for_pdf`: direct PDF URL (may be null even if OA)
- `best_oa_location.url`: landing page URL
- `oa_status`: "gold" | "green" | "hybrid" | "bronze" | "closed"

If `url_for_pdf` is null but `is_oa` is true, try `url` (landing page) → Tier 2.

## DOI Resolution

A DOI like `10.1234/example` resolves via:
- `https://doi.org/10.1234/example` → redirects to publisher page

Use this redirect URL for Tier 2 navigation.

## Fallback Chain

```
Tier 1 (OA direct) 
  → failed? → Tier 2 (publisher page)
    → failed? → Ask user: try CNKI or gray sources?
```

Never automatically escalate to gray sources without user consent.
