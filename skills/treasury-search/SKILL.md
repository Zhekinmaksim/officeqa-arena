---
name: treasury-search
description: Guide for searching and extracting data from the U.S. Treasury Bulletin corpus using MCP tools.
---

# Treasury Bulletin Search Guide

## MCP Tools (always use treasury__ prefix)

1. **treasury__search_corpus(query, top_k)** — BM25 ranked search. Use 2-4 keywords.
2. **treasury__grep_corpus(pattern, max_results)** — Regex across all files. Spreads results across files.
3. **treasury__read_document(filename, start_line, num_lines)** — Read document section (up to 500 lines).
4. **treasury__search_in_document(filename, pattern, context_lines)** — Find text within a doc.
5. **treasury__extract_table(filename, start_line)** — Parse pipe-delimited table cleanly.
6. **treasury__list_documents(year_filter)** — List docs by year or range.
7. **treasury__document_info(filename)** — See table names, headers, structure.

## Shell Backup

If MCP tools don't find results, use shell:
```bash
grep -ri "search term" /app/corpus/ | head -30
grep -ri "table.*SB-2" /app/corpus/treasury_bulletin_1982*.txt
```

## Search Strategy

1. Start with `treasury__search_corpus` using keywords from question
2. Try `treasury__grep_corpus` with exact phrases or table codes
3. Check adjacent year bulletins if data not in expected year
4. Use `treasury__document_info` to see all table names in a document
5. For multi-year data, later bulletins often have historical tables

## Common Table Codes

- **FFO** = Federal Fiscal Operations (receipts, outlays, debt)
- **SB** = Savings Bonds (sales, redemptions, outstanding)
- **CM** = Capital Movements (foreign liabilities, assets)
- **AY** = Average Yields (bond yields by maturity)
- **FCP** = Foreign Currency Positions (bank/nonbank positions)
- **IFS** = International Financial Statistics
- **OFS** = Ownership of Federal Securities

## Document Naming

Files: `treasury_bulletin_YYYY_MM.txt` (1939-2025)

## Table Format

Pipe-delimited: `Category | 1940 | 1941 | 1942`
Column hierarchy: `Category | 1940 > Jan. | 1940 > Feb.`
(Parentheses) = negative numbers

## Fiscal Year Calendar

- FY 1977+: Oct 1 – Sep 30
- FY before 1977: Jul 1 – Jun 30
- TQ: Jul 1 – Sep 30, 1976
