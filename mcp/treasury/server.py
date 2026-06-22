#!/usr/bin/env python3
"""
Treasury Bulletin Search MCP Server.

Provides efficient search and data extraction over the full
Treasury Bulletin corpus (697 transformed .txt documents, 1939-2025).
Designed for the Sentient Arena OfficeQA challenge.
"""

import os
import re
import sys
import json
import math
import glob
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
from typing import Optional

# FastMCP import — shipped with the submission
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    # Fallback: try pip-installed fastmcp
    from fastmcp import FastMCP

mcp = FastMCP("treasury-search")

# ---------------------------------------------------------------------------
# Corpus discovery
# ---------------------------------------------------------------------------

CORPUS_DIRS = [
    "/app/treasury_bulletins_parsed/transformed",
    "/app/corpus/transformed",
    "/app/corpus",
    "/app/data/transformed",
    os.environ.get("CORPUS_DIR", ""),
]

INDEX = None  # lazy-built inverted index


def _find_corpus_dir() -> str:
    """Find the directory containing transformed .txt files."""
    for d in CORPUS_DIRS:
        if d and os.path.isdir(d):
            txts = glob.glob(os.path.join(d, "*.txt"))
            if txts:
                return d
    # Fallback: search /app recursively for .txt files
    for root, dirs, files in os.walk("/app"):
        txts = [f for f in files if f.endswith(".txt")]
        if len(txts) > 50:
            return root
    return "/app"


def _get_corpus_dir() -> str:
    if not hasattr(_get_corpus_dir, "_cached"):
        _get_corpus_dir._cached = _find_corpus_dir()
    return _get_corpus_dir._cached


# ---------------------------------------------------------------------------
# Inverted index (BM25-style)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric."""
    return re.findall(r'[a-z0-9]+', text.lower())


class BM25Index:
    """Lightweight BM25 index over text documents."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_paths: list[str] = []
        self.doc_names: list[str] = []
        self.doc_lens: list[int] = []
        self.avgdl: float = 0.0
        self.N: int = 0
        # term -> {doc_idx: term_freq}
        self.inverted: dict[str, dict[int, int]] = defaultdict(dict)
        self.df: dict[str, int] = Counter()  # document frequency

    def build(self, corpus_dir: str):
        """Index all .txt files in corpus_dir."""
        txt_files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
        if not txt_files:
            txt_files = sorted(glob.glob(os.path.join(corpus_dir, "**", "*.txt"), recursive=True))

        self.N = len(txt_files)
        total_len = 0

        for idx, fpath in enumerate(txt_files):
            self.doc_paths.append(fpath)
            self.doc_names.append(os.path.basename(fpath))

            with open(fpath, 'r', errors='replace') as f:
                text = f.read()

            tokens = _tokenize(text)
            self.doc_lens.append(len(tokens))
            total_len += len(tokens)

            tf = Counter(tokens)
            for term, count in tf.items():
                self.inverted[term][idx] = count
                self.df[term] += 1

        self.avgdl = total_len / max(self.N, 1)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, str, float]]:
        """Search and return top_k results as (filename, path, score)."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: dict[int, float] = defaultdict(float)

        for term in query_tokens:
            if term not in self.inverted:
                continue
            idf = math.log((self.N - self.df[term] + 0.5) / (self.df[term] + 0.5) + 1.0)
            for doc_idx, tf in self.inverted[term].items():
                dl = self.doc_lens[doc_idx]
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
                scores[doc_idx] += idf * tf_norm

        ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_k]
        return [(self.doc_names[idx], self.doc_paths[idx], score) for idx, score in ranked]


def _get_index() -> BM25Index:
    global INDEX
    if INDEX is None:
        INDEX = BM25Index()
        INDEX.build(_get_corpus_dir())
    return INDEX


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_corpus(query: str, top_k: int = 10) -> str:
    """
    Search the entire Treasury Bulletin corpus for documents matching a query.
    Returns the top_k most relevant documents with BM25 ranking.

    Args:
        query: Search terms (e.g. "national defense expenditures 1940")
        top_k: Number of results to return (default 10)

    Returns:
        Ranked list of matching documents with filenames and relevance scores.
    """
    idx = _get_index()
    results = idx.search(query, top_k=min(top_k, 20))
    if not results:
        return "No matching documents found. Try different search terms."

    lines = [f"Found {len(results)} relevant documents:\n"]
    for i, (name, path, score) in enumerate(results, 1):
        # Extract year/month from filename
        m = re.search(r'(\d{4})_(\d{2})', name)
        period = f" ({m.group(1)}-{m.group(2)})" if m else ""
        lines.append(f"{i}. {name}{period}  [score: {score:.1f}]")

    return "\n".join(lines)


@mcp.tool()
def grep_corpus(pattern: str, max_results: int = 20) -> str:
    """
    Search for a regex pattern across all Treasury Bulletin documents.
    Faster than search_corpus for exact keyword/number lookups.

    Args:
        pattern: Regex pattern to search for (case-insensitive)
        max_results: Maximum number of matching lines to return

    Returns:
        Matching lines with filename and line number context.
    """
    corpus_dir = _get_corpus_dir()
    txt_files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
    if not txt_files:
        txt_files = sorted(glob.glob(os.path.join(corpus_dir, "**", "*.txt"), recursive=True))

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Invalid regex: {e}"

    matches = []
    for fpath in txt_files:
        fname = os.path.basename(fpath)
        with open(fpath, 'r', errors='replace') as f:
            for lineno, line in enumerate(f, 1):
                if regex.search(line):
                    matches.append(f"{fname}:{lineno}: {line.rstrip()}")
                    if len(matches) >= max_results:
                        break
        if len(matches) >= max_results:
            break

    if not matches:
        return f"No matches found for pattern: {pattern}"

    header = f"Found {len(matches)} match(es) for '{pattern}':\n"
    return header + "\n".join(matches)


@mcp.tool()
def read_document(filename: str, start_line: int = 1, num_lines: int = 200) -> str:
    """
    Read a section of a specific Treasury Bulletin document.

    Args:
        filename: The document filename (e.g. "treasury_bulletin_1940_01.txt")
        start_line: Starting line number (1-based, default 1)
        num_lines: Number of lines to read (default 200)

    Returns:
        The requested section of the document with line numbers.
    """
    corpus_dir = _get_corpus_dir()
    fpath = os.path.join(corpus_dir, filename)
    if not os.path.exists(fpath):
        # Try to find it
        candidates = glob.glob(os.path.join(corpus_dir, "**", filename), recursive=True)
        if candidates:
            fpath = candidates[0]
        else:
            return f"File not found: {filename}. Use search_corpus or list_documents to find valid filenames."

    with open(fpath, 'r', errors='replace') as f:
        lines = f.readlines()

    total = len(lines)
    start = max(0, start_line - 1)
    end = min(total, start + num_lines)
    section = lines[start:end]

    header = f"=== {filename} (lines {start+1}-{end} of {total}) ===\n"
    numbered = [f"{i+start+1:5d} | {line.rstrip()}" for i, line in enumerate(section)]
    return header + "\n".join(numbered)


@mcp.tool()
def list_documents(year_filter: Optional[str] = None) -> str:
    """
    List all available Treasury Bulletin documents.
    Optionally filter by year (e.g. "1940") or year range (e.g. "1940-1950").

    Args:
        year_filter: Optional year or year range to filter by

    Returns:
        List of available document filenames with their year/month.
    """
    corpus_dir = _get_corpus_dir()
    txt_files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
    if not txt_files:
        txt_files = sorted(glob.glob(os.path.join(corpus_dir, "**", "*.txt"), recursive=True))

    names = [os.path.basename(f) for f in txt_files]

    if year_filter:
        if '-' in year_filter:
            parts = year_filter.split('-')
            try:
                y_start, y_end = int(parts[0]), int(parts[1])
            except ValueError:
                return f"Invalid year range: {year_filter}. Use format: 1940-1950"
            filtered = []
            for n in names:
                m = re.search(r'(\d{4})', n)
                if m and y_start <= int(m.group(1)) <= y_end:
                    filtered.append(n)
            names = filtered
        else:
            names = [n for n in names if year_filter in n]

    if not names:
        return f"No documents found{' for filter: ' + year_filter if year_filter else ''}."

    return f"Available documents ({len(names)} files):\n" + "\n".join(names)


@mcp.tool()
def search_in_document(filename: str, pattern: str, context_lines: int = 3) -> str:
    """
    Search for a pattern within a specific document and return matching lines with context.

    Args:
        filename: The document filename
        pattern: Regex pattern to search for (case-insensitive)
        context_lines: Number of context lines before/after each match (default 3)

    Returns:
        Matching sections with surrounding context.
    """
    corpus_dir = _get_corpus_dir()
    fpath = os.path.join(corpus_dir, filename)
    if not os.path.exists(fpath):
        candidates = glob.glob(os.path.join(corpus_dir, "**", filename), recursive=True)
        if candidates:
            fpath = candidates[0]
        else:
            return f"File not found: {filename}"

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Invalid regex: {e}"

    with open(fpath, 'r', errors='replace') as f:
        lines = f.readlines()

    matches = []
    for i, line in enumerate(lines):
        if regex.search(line):
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            block = []
            for j in range(start, end):
                prefix = ">>>" if j == i else "   "
                block.append(f"{prefix} {j+1:5d} | {lines[j].rstrip()}")
            matches.append("\n".join(block))

    if not matches:
        return f"No matches for '{pattern}' in {filename}"

    header = f"Found {len(matches)} match(es) in {filename}:\n\n"
    return header + "\n---\n".join(matches[:15])  # limit output


@mcp.tool()
def document_info(filename: str) -> str:
    """
    Get metadata and structure overview of a specific document:
    total lines, tables detected, section headers, and year coverage.

    Args:
        filename: The document filename

    Returns:
        Document metadata and structural overview.
    """
    corpus_dir = _get_corpus_dir()
    fpath = os.path.join(corpus_dir, filename)
    if not os.path.exists(fpath):
        candidates = glob.glob(os.path.join(corpus_dir, "**", filename), recursive=True)
        if candidates:
            fpath = candidates[0]
        else:
            return f"File not found: {filename}"

    with open(fpath, 'r', errors='replace') as f:
        text = f.read()
        lines = text.split('\n')

    total_lines = len(lines)
    size_kb = len(text) / 1024

    # Detect table headers (lines with multiple | characters)
    table_lines = [i+1 for i, l in enumerate(lines) if l.count('|') >= 3]
    table_count = 0
    if table_lines:
        # Group consecutive table lines into tables
        groups = []
        current = [table_lines[0]]
        for tl in table_lines[1:]:
            if tl - current[-1] <= 2:
                current.append(tl)
            else:
                groups.append(current)
                current = [tl]
        groups.append(current)
        table_count = len(groups)

    # Detect section headers (lines in ALL CAPS or starting with #)
    headers = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and (stripped.startswith('#') or (len(stripped) > 10 and stripped == stripped.upper() and any(c.isalpha() for c in stripped))):
            headers.append(f"  Line {i+1}: {stripped[:80]}")
            if len(headers) >= 20:
                break

    info = [
        f"=== {filename} ===",
        f"Size: {size_kb:.1f} KB, {total_lines} lines",
        f"Tables detected: ~{table_count}",
        f"\nSection headers ({len(headers)} found):",
    ]
    info.extend(headers[:20])

    return "\n".join(info)


# ---------------------------------------------------------------------------
# Table parser (clean column-aligned output from raw HTML/pipe tables)
# ---------------------------------------------------------------------------

def _parse_html_tables(html):
    tables = []
    for table_match in re.finditer(r'<table>(.*?)</table>', html, re.DOTALL):
        table_html = table_match.group(1)
        rows_raw = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)
        grid = []
        pending = {}
        for ri, row_html in enumerate(rows_raw):
            cells = re.findall(r'<(th|td)(.*?)>(.*?)</(?:th|td)>', row_html, re.DOTALL)
            row = []
            ci = 0
            while (ri, ci) in pending:
                row.append(pending.pop((ri, ci)))
                ci += 1
            for tag, attrs, content in cells:
                while (ri, ci) in pending:
                    row.append(pending.pop((ri, ci)))
                    ci += 1
                val = re.sub(r'<[^>]+>', '', content).strip()
                colspan = int(m.group(1)) if (m := re.search(r'colspan="(\d+)"', attrs)) else 1
                rowspan = int(m.group(1)) if (m := re.search(r'rowspan="(\d+)"', attrs)) else 1
                for c in range(colspan):
                    while (ri, ci) in pending:
                        row.append(pending.pop((ri, ci)))
                        ci += 1
                    row.append(val if c == 0 else "")
                    for r in range(1, rowspan):
                        pending[(ri + r, ci)] = val if c == 0 else ""
                    ci += 1
            while (ri, ci) in pending:
                row.append(pending.pop((ri, ci)))
                ci += 1
            grid.append(row)
        if grid:
            tables.append(grid)
    return tables


def _parse_pipe_tables(text):
    tables = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        if re.match(r'^\|[\s-]+\|', lines[i]):
            sep_idx = i
            header_start = sep_idx - 1
            while header_start > 0 and '|' in lines[header_start - 1] and lines[header_start - 1].strip().startswith('|'):
                header_start -= 1
            header_cells = []
            for hi in range(header_start, sep_idx):
                cells = [c.strip() for c in lines[hi].split('|')]
                cells = [c for c in cells if c]
                if not header_cells:
                    header_cells = cells
                else:
                    for ci in range(min(len(header_cells), len(cells))):
                        if cells[ci] and cells[ci] != header_cells[ci]:
                            header_cells[ci] = f"{header_cells[ci]} > {cells[ci]}"
            grid = [header_cells]
            j = sep_idx + 1
            while j < len(lines) and '|' in lines[j]:
                cells = [c.strip() for c in lines[j].split('|')]
                cells = [c for c in cells if c or len([x for x in cells if x]) > 1]
                if cells and cells[0] == '':
                    cells = cells[1:]
                if cells and cells[-1] == '':
                    cells = cells[:-1]
                if cells:
                    grid.append(cells)
                j += 1
            if len(grid) > 1:
                tables.append(grid)
            i = j
        else:
            i += 1
    return tables


def _clean_cell(val):
    v = val.strip()
    v = re.sub(r'\s*\d+/', '', v)
    if v.startswith('(') and v.endswith(')'):
        v = '-' + v[1:-1]
    v = v.rstrip(' p')
    return v


def _format_table(grid, table_idx):
    if not grid:
        return ""
    headers = grid[0]
    merged = list(headers)
    data_start = 1
    if len(grid) > 1:
        row2 = grid[1]
        non_empty = [c for c in row2 if c.strip()]
        if non_empty and all(len(c) < 30 for c in non_empty):
            numeric = sum(1 for c in non_empty if re.match(r'^[\d,.\-()$ ]+$', c.strip()))
            if numeric < len(non_empty) / 2:
                merged = []
                for i in range(max(len(headers), len(row2))):
                    h1 = headers[i].strip() if i < len(headers) else ""
                    h2 = row2[i].strip() if i < len(row2) else ""
                    merged.append(f"{h1} > {h2}" if h1 and h2 else h1 or h2)
                data_start = 2
    lines = [f"=== TABLE {table_idx + 1} ===",
             " | ".join(h.strip() for h in merged),
             "-" * 40]
    for row in grid[data_start:]:
        padded = row + [""] * (len(merged) - len(row))
        cleaned = [_clean_cell(c) for c in padded[:len(merged)]]
        if any(c.strip() for c in cleaned):
            lines.append(" | ".join(c.strip() for c in cleaned))
    return "\n".join(lines)


@mcp.tool()
def parse_table(filename: str, search: Optional[str] = None) -> str:
    """
    Parse tables from a Treasury Bulletin document into clean, column-aligned output.
    Much more reliable than reading raw lines — handles HTML tables, rowspan/colspan,
    footnotes, and parentheses-as-negative. Use this instead of read_document for tables.

    Args:
        filename: The document filename (e.g. "treasury_bulletin_1941_01.txt")
        search: Optional search term to filter rows (case-insensitive). Only matching rows are shown.

    Returns:
        Clean pipe-delimited tables with headers and aligned columns.
    """
    corpus_dir = _get_corpus_dir()
    fpath = os.path.join(corpus_dir, filename)
    if not os.path.exists(fpath):
        candidates = glob.glob(os.path.join(corpus_dir, "**", filename), recursive=True)
        if candidates:
            fpath = candidates[0]
        else:
            return f"File not found: {filename}"

    content = open(fpath, 'r', errors='replace').read()

    tables = _parse_html_tables(content)
    if not tables:
        tables = _parse_pipe_tables(content)
    if not tables:
        return f"No tables found in {filename}. First 2000 chars:\n{content[:2000]}"

    output = []
    for i, grid in enumerate(tables):
        formatted = _format_table(grid, i)
        if search:
            lines = formatted.split("\n")
            header_lines = lines[:3]
            # Match in headers OR data rows
            header_match = any(search.lower() in h.lower() for h in header_lines)
            matching = [l for l in lines[3:] if search.lower() in l.lower()]
            if matching or header_match:
                output.append("\n".join(header_lines))
                if matching:
                    output.extend(matching)
                elif header_match:
                    # Show first 10 data rows if header matches
                    output.extend(lines[3:13])
                output.append("")
        else:
            output.append(formatted)
            output.append("")

    result = "\n".join(output)
    if not result.strip():
        return f"No matching rows for '{search}' in {filename}"
    return result[:8000]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
