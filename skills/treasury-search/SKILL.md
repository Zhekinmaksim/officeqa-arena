---
name: treasury-search
description: Quick reference for Treasury Bulletin corpus search tools.
---

# Treasury Search

## Tools
- `search_corpus(query, top_k)` — BM25 ranked search, returns top docs with preview
- `grep_corpus(pattern, max_results)` — Regex search across all 697 files
- `read_document(filename, start_line, num_lines)` — Read document section
- `search_in_document(filename, pattern)` — Find pattern within one doc
- `list_documents(year_filter)` — List docs by year/range
- `document_info(filename)` — Show table names and structure
- `extract_table(filename, start_line)` — Parse pipe-delimited table

## Shell Backup
```bash
grep -ri "search term" /app/resources/ | head -20
```

## File Naming
`treasury_bulletin_YYYY_MM.txt` (1939-2025)

## Table Codes
FFO=Fiscal Operations, SB=Savings Bonds, CM=Capital Movements, AY=Average Yields, OFS=Ownership Federal Securities
