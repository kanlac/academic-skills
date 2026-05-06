# Paper Sources Catalog

## Tier 1 Sources (Free, Direct PDF)

| Source | Coverage | API | Rate Limit | PDF Access |
|--------|----------|-----|------------|-----------|
| arXiv | STEM preprints (2.4M+) | REST, no auth | 1 req/3s | Always free |
| Unpaywall | DOI→OA lookup (30M+ OA) | REST, email only | 100K/day | Direct PDF links |
| Semantic Scholar | 200M+ papers | REST, no auth (key optional) | 1 req/s (100/s with key) | OA PDF when available |
| PubMed Central | Biomedical (8M+) | REST, free key | 3/s (10/s with key) | Free full-text |
| DOAJ | 10M+ OA articles | REST, no auth | No strict limit | Links to OA PDFs |
| OpenAlex | 297M works | REST, no auth | Credit-based ($1 free/day) | OA links |
| CORE | 431M records | REST, free key | 10/s without key | Full-text OA |

## Tier 2 Sources (Publisher Pages)

| Publisher | DOI Prefix Examples | PDF Access Pattern |
|-----------|--------------------|--------------------|
| Elsevier/ScienceDirect | 10.1016/ | Navigate → PDF button |
| Springer Nature | 10.1007/, 10.1038/ | Navigate → Download PDF |
| Wiley | 10.1002/ | Navigate → PDF link |
| Taylor & Francis | 10.1080/ | Navigate → Download |
| IEEE | 10.1109/ | Navigate → Download PDF |
| ACM | 10.1145/ | Navigate → PDF |
| SAGE | 10.1177/ | Navigate → PDF |
| Oxford University Press | 10.1093/ | Navigate → PDF |

## Tier 3 Sources (Login Required)

| Source | Coverage | Access |
|--------|----------|--------|
| CNKI (知网) | Chinese academic (largest) | Institutional login |

## API Quick Reference

### Unpaywall
```
GET https://api.unpaywall.org/v2/{doi}?email=unpaywall@example.com
```
Key fields: `is_oa`, `best_oa_location.url_for_pdf`, `oa_status`

### Semantic Scholar
```
GET https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,authors,year,openAccessPdf,externalIds
```
Key fields: `openAccessPdf.url`, `externalIds.ArXiv`

### arXiv
```
PDF: https://arxiv.org/pdf/{id}.pdf
Abs: https://arxiv.org/abs/{id}
API: http://export.arxiv.org/api/query?id_list={id}
```

### CrossRef (metadata)
```
GET https://api.crossref.org/works/{doi}
```
Key fields: `title`, `author`, `container-title`, `published`
