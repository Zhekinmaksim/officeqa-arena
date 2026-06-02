---
name: treasury-search
description: Guide for searching and extracting data from the U.S. Treasury Bulletin corpus using MCP tools.
---

# Treasury Bulletin Search Guide

## Available MCP Tools

You have these tools to search the Treasury Bulletin corpus:

1. **search_corpus(query, top_k)** — BM25 ranked search across all 697 documents. Best for finding which document contains the answer.
2. **grep_corpus(pattern, max_results)** — Regex search across all files. Best for exact terms, numbers, or phrases.
3. **read_document(filename, start_line, num_lines)** — Read a section of a specific document. Use after finding the right file.
4. **search_in_document(filename, pattern, context_lines)** — Search within a specific document. Useful for finding tables in a large file.
5. **list_documents(year_filter)** — List available documents, optionally filtered by year.
6. **document_info(filename)** — Get document metadata: size, table count, section headers.

## Search Strategy

1. Start with `search_corpus` using 2-4 keywords from the question
2. If no good results, try `grep_corpus` with exact phrases
3. Once you find the right document, use `search_in_document` to locate the specific table
4. Use `read_document` to see the full table with context
5. Extract numbers and compute with Python

## Common Document Naming Pattern

Files follow: `treasury_bulletin_YYYY_MM.txt`
- YYYY = publication year (1939-2025)
- MM = month (01-12)

## Table Format

Tables use pipe-delimited format:
```
Category | 1940 | 1941 | 1942
National defense | 1,590 | 6,301 | 23,970
```

Column headers may use ">" for hierarchy:
```
Category | 1940 > Jan. | 1940 > Feb. | 1940 > Mar.
```

## Units

Check the table header/title for units — common ones:
- "In millions of dollars"
- "In thousands of dollars"  
- "In billions of dollars"
- "Percent" or "%"

## Fiscal Year Calendar

- FY 1977 onward: Oct 1 – Sep 30 (FY 2000 = Oct 1999 – Sep 2000)
- Before 1977: Jul 1 – Jun 30 (FY 1976 = Jul 1975 – Jun 1976)
- Transition Quarter (TQ): Jul 1 – Sep 30, 1976

## Always Use Python for Computation

Never do mental math. Always write and execute a Python script:
```python
# Example: percent change
old_val = 1590
new_val = 6301
pct_change = ((new_val - old_val) / old_val) * 100
print(f"{pct_change:.2f}")
```
