#!/usr/bin/env python3
"""
Treasury Bulletin Search MCP Server v2.

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
    from fastmcp import FastMCP

mcp = FastMCP("treasury-search")

# ---------------------------------------------------------------------------
# Corpus discovery
# ---------------------------------------------------------------------------

CORPUS_DIRS = [
    "/app/resources",
    "/app/resources/transformed",
    "/app/treasury_bulletins_parsed/transformed",
    "/app/corpus/transformed",
    "/app/corpus",
    "/app/data/transformed",
    "/app/data",
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


def _get_all_txt_files() -> list[str]:
    """Return sorted list of all .txt files in corpus."""
    if not hasattr(_get_all_txt_files, "_cached"):
        corpus_dir = _get_corpus_dir()
        files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
        if not files:
            files = sorted(glob.glob(os.path.join(corpus_dir, "**", "*.txt"), recursive=True))
        _get_all_txt_files._cached = files
    return _get_all_txt_files._cached


# ---------------------------------------------------------------------------
# Inverted index (BM25-style)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric."""
    return re.findall(r'[a-z0-9]+', text.lower())


def _bigrams(tokens: list[str]) -> list[str]:
    """Generate bigrams from token list for phrase matching."""
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]


def _extract_years(text: str) -> set[int]:
    """Extract 4-digit years (1900-2030) from text."""
    return {int(y) for y in re.findall(r'(?<!\d)(19\d{2}|20[0-2]\d)(?!\d)', text)}


class BM25Index:
    """BM25 index with bigram support and year-boosting."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_paths: list[str] = []
        self.doc_names: list[str] = []
        self.doc_lens: list[int] = []
        self.doc_years: list[set[int]] = []  # years in filename
        self.avgdl: float = 0.0
        self.N: int = 0
        self.inverted: dict[str, dict[int, int]] = defaultdict(dict)
        self.df: dict[str, int] = Counter()

    def build(self, corpus_dir: str):
        """Index all .txt files in corpus_dir with unigrams and bigrams."""
        txt_files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
        if not txt_files:
            txt_files = sorted(glob.glob(os.path.join(corpus_dir, "**", "*.txt"), recursive=True))

        self.N = len(txt_files)
        total_len = 0

        for idx, fpath in enumerate(txt_files):
            self.doc_paths.append(fpath)
            fname = os.path.basename(fpath)
            self.doc_names.append(fname)
            # Extract year from filename for year-boosting
            self.doc_years.append(_extract_years(fname))

            with open(fpath, 'r', errors='replace') as f:
                text = f.read()

            tokens = _tokenize(text)
            # Add bigrams for phrase matching
            bigrams = _bigrams(tokens)
            all_terms = tokens + bigrams

            self.doc_lens.append(len(tokens))
            total_len += len(tokens)

            tf = Counter(all_terms)
            for term, count in tf.items():
                self.inverted[term][idx] = count
                self.df[term] += 1

        self.avgdl = total_len / max(self.N, 1)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, str, float]]:
        """Search with BM25 + bigrams + year-boosting."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        # Generate query bigrams for phrase matching
        query_bigrams = _bigrams(query_tokens)
        all_query_terms = query_tokens + query_bigrams

        # Extract years from query for boosting
        query_years = _extract_years(query)

        scores: dict[int, float] = defaultdict(float)

        for term in all_query_terms:
            if term not in self.inverted:
                continue
            idf = math.log((self.N - self.df[term] + 0.5) / (self.df[term] + 0.5) + 1.0)
            # Bigrams get 2x weight (phrase match is stronger signal)
            weight = 2.0 if '_' in term else 1.0
            for doc_idx, tf in self.inverted[term].items():
                dl = self.doc_lens[doc_idx]
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
                scores[doc_idx] += idf * tf_norm * weight

        # Year-boosting: if query mentions a year, boost docs from that year
        if query_years:
            for doc_idx in scores:
                doc_yrs = self.doc_years[doc_idx]
                if doc_yrs & query_years:
                    scores[doc_idx] *= 1.5  # 50% boost for year match
                # Also boost adjacent years (±2) with smaller boost
                elif any(abs(dy - qy) <= 2 for dy in doc_yrs for qy in query_years):
                    scores[doc_idx] *= 1.2  # 20% boost for nearby year

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
    Returns the top_k most relevant documents with BM25 ranking and a preview snippet.

    Args:
        query: Search terms (e.g. "national defense expenditures 1940")
        top_k: Number of results to return (default 10)

    Returns:
        Ranked list of matching documents with filenames, scores, and content preview.
    """
    idx = _get_index()
    results = idx.search(query, top_k=min(top_k, 30))
    if not results:
        return "No matching documents found. Try different search terms or use grep_corpus for exact phrases."

    query_tokens = set(_tokenize(query))
    lines = [f"Found {len(results)} relevant documents:\n"]
    for i, (name, path, score) in enumerate(results, 1):
        m = re.search(r'(\d{4})_(\d{2})', name)
        period = f" ({m.group(1)}-{m.group(2)})" if m else ""
        lines.append(f"{i}. {name}{period}  [score: {score:.1f}]")
        # Add snippet: find first line containing query terms
        if i <= 5:  # snippets for top 5 only
            try:
                with open(path, 'r', errors='replace') as f:
                    for lineno, line in enumerate(f, 1):
                        line_lower = line.lower()
                        if any(t in line_lower for t in query_tokens) and '|' in line:
                            lines.append(f"   L{lineno}: {line.rstrip()[:150]}")
                            break
            except:
                pass

    return "\n".join(lines)


@mcp.tool()
def grep_corpus(pattern: str, max_results: int = 30) -> str:
    """
    Search for a regex pattern across ALL Treasury Bulletin documents.
    Case-insensitive.

    Args:
        pattern: Regex pattern to search for (case-insensitive)
        max_results: Maximum total matching lines to return (default 30)

    Returns:
        Matching lines with filename and line number context.
    """
    txt_files = _get_all_txt_files()

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
                    matches.append(f"{fname}:{lineno}: {line.rstrip()[:200]}")
                    if len(matches) >= max_results:
                        break
        if len(matches) >= max_results:
            break

    if not matches:
        return f"No matches found for pattern: {pattern}\nTip: Try simpler terms, check spelling, or use search_corpus for keyword search."

    header = f"Found {len(matches)} match(es) for '{pattern}':\n"
    return header + "\n".join(matches)


@mcp.tool()
def read_document(filename: str, start_line: int = 1, num_lines: int = 200) -> str:
    """
    Read a section of a specific Treasury Bulletin document.

    Args:
        filename: The document filename (e.g. "treasury_bulletin_1940_01.txt")
        start_line: Starting line number (1-based, default 1)
        num_lines: Number of lines to read (default 200, max 500)

    Returns:
        The requested section of the document with line numbers.
    """
    corpus_dir = _get_corpus_dir()
    fpath = os.path.join(corpus_dir, filename)
    if not os.path.exists(fpath):
        candidates = glob.glob(os.path.join(corpus_dir, "**", filename), recursive=True)
        if candidates:
            fpath = candidates[0]
        else:
            return f"File not found: {filename}. Use list_documents to find valid filenames."

    num_lines = min(num_lines, 500)

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
    return header + "\n---\n".join(matches[:20])


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
    txt_files = _get_all_txt_files()
    names = [os.path.basename(f) for f in txt_files]

    if year_filter:
        if '-' in year_filter and len(year_filter) > 4:
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
def document_info(filename: str) -> str:
    """
    Get metadata and structure overview of a specific document:
    total lines, tables detected, section headers, and table names.

    Args:
        filename: The document filename

    Returns:
        Document metadata, structural overview, and list of table names found.
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

    # Detect table names (lines containing "Table" followed by identifier)
    table_names = []
    for i, line in enumerate(lines):
        m = re.match(r'.*\b(Table\s+\S+[\s.-]+[^\|]{5,80})', line, re.IGNORECASE)
        if m and '|' not in line:
            table_names.append(f"  Line {i+1}: {m.group(1).strip()[:100]}")
            if len(table_names) >= 30:
                break

    # Detect section headers
    headers = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and len(stripped) > 10 and stripped == stripped.upper() and any(c.isalpha() for c in stripped) and '|' not in stripped:
            headers.append(f"  Line {i+1}: {stripped[:80]}")
            if len(headers) >= 15:
                break

    info = [
        f"=== {filename} ===",
        f"Size: {size_kb:.1f} KB, {total_lines} lines",
        f"Tables detected: ~{table_count}",
    ]

    if table_names:
        info.append(f"\nTable names ({len(table_names)} found):")
        info.extend(table_names)

    if headers:
        info.append(f"\nSection headers ({len(headers)} found):")
        info.extend(headers)

    return "\n".join(info)


@mcp.tool()
def extract_table(filename: str, start_line: int, end_line: int = 0) -> str:
    """
    Extract and format a pipe-delimited table from a document.
    Cleans up formatting and shows column alignment clearly.

    Args:
        filename: The document filename
        start_line: First line of the table (1-based)
        end_line: Last line of the table (0 = auto-detect end, reads up to 100 lines)

    Returns:
        Formatted table with columns aligned and labeled.
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
        lines = f.readlines()

    total = len(lines)
    start = max(0, start_line - 1)

    if end_line > 0:
        end = min(total, end_line)
    else:
        # Auto-detect: read until we hit a non-table line (no pipes) after seeing table lines
        end = start
        seen_table = False
        blank_count = 0
        while end < min(total, start + 150):
            line = lines[end].strip()
            has_pipes = '|' in line
            is_separator = bool(re.match(r'^[\s|:_\-]+$', line))
            is_blank = len(line) == 0

            if has_pipes or is_separator:
                seen_table = True
                blank_count = 0
            elif is_blank and seen_table:
                blank_count += 1
                if blank_count >= 2:
                    break
            elif seen_table and not is_blank and not has_pipes:
                # Non-table line after table started — might be a title for next table
                break

            end += 1

    # Extract and format
    table_lines = []
    for i in range(start, end):
        line = lines[i].rstrip()
        if '|' in line:
            # Parse pipe-delimited columns
            cells = [c.strip() for c in line.split('|')]
            # Remove empty leading/trailing cells from pipe format
            if cells and cells[0] == '':
                cells = cells[1:]
            if cells and cells[-1] == '':
                cells = cells[:-1]
            table_lines.append(f"L{i+1}: " + " | ".join(cells))
        elif line.strip():
            table_lines.append(f"L{i+1}: {line}")

    if not table_lines:
        return f"No table data found at lines {start_line}-{end} in {filename}"

    header = f"=== Table from {filename} (lines {start_line}-{end}) ===\n"
    return header + "\n".join(table_lines)


@mcp.tool()
def find_data(query: str, grep_pattern: str = "") -> str:
    """
    Combined search: finds the best document AND reads the relevant section in one call.
    Saves multiple round-trips. Use this as your first tool for most questions.

    Args:
        query: Natural language search (e.g. "savings bonds sales 1960")
        grep_pattern: Optional exact pattern to find within the best doc (e.g. "1960")

    Returns:
        The most relevant document section containing matching data.
    """
    idx = _get_index()
    results = idx.search(query, top_k=5)
    if not results:
        return "No documents found. Try grep_corpus with different terms."

    # Try each top result until we find matching content
    for name, path, score in results:
        try:
            with open(path, 'r', errors='replace') as f:
                lines = f.readlines()
        except:
            continue

        # If grep_pattern given, find matching section
        if grep_pattern:
            try:
                regex = re.compile(grep_pattern, re.IGNORECASE)
            except:
                regex = None

            best_line = -1
            if regex:
                for i, line in enumerate(lines):
                    if regex.search(line) and '|' in line:
                        best_line = i
                        break
                # If no table match, try any match
                if best_line < 0:
                    for i, line in enumerate(lines):
                        if regex.search(line):
                            best_line = i
                            break
            if best_line < 0:
                continue
        else:
            # Find first table-like section with query terms
            query_tokens = set(_tokenize(query))
            best_line = -1
            for i, line in enumerate(lines):
                if '|' in line and any(t in line.lower() for t in query_tokens):
                    best_line = i
                    break
            if best_line < 0:
                best_line = 0

        # Read section around the match (go back to find table header)
        start = max(0, best_line - 10)
        end = min(len(lines), best_line + 40)

        # Output the section
        output = [f"=== {name} (lines {start+1}-{end}, score: {score:.1f}) ===\n"]
        for i in range(start, end):
            line = lines[i].rstrip()
            if line:
                prefix = ">>>" if i == best_line else "   "
                output.append(f"{prefix} {i+1:5d} | {line[:200]}")

        return "\n".join(output)

    return f"Found docs but no matching content for: {query}. Try grep_corpus or search_corpus separately."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
