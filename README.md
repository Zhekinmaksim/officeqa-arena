# OfficeQA Arena Agent

Competition entry for [Sentient Arena Challenge 0: OfficeQA](https://arena.sentient.xyz/challenges/office-qa).

## Architecture

- **BM25 Search Index**: In-memory inverted index over the full Treasury Bulletin corpus (697 documents). Built at startup, enables fast keyword-based retrieval.
- **MCP Server** (`mcp/treasury/`): FastMCP server providing `search_corpus`, `grep_corpus`, `read_document`, `search_in_document`, `list_documents`, and `document_info` tools.
- **Prompt Template** (`prompts/system.j2`): Mentor-framed system prompt with structured search/verify/compute protocol, FY/CY rules, and unit handling guidance.
- **Skills** (`skills/`): Domain-specific reference guides for search strategy and financial math patterns.
- **Harness**: Goose agent with MiniMax M2.7 via OpenRouter.

## Project Structure

```
officeqa-arena/
├── arena.yaml              # Agent config
├── mcp/
│   └── treasury/
│       ├── mcp.toml        # MCP server manifest
│       └── server.py       # BM25 search + corpus tools
├── prompts/
│   └── system.j2           # System prompt template
├── skills/
│   ├── treasury-search/
│   │   └── SKILL.md        # Search guide
│   └── financial-math/
│       └── SKILL.md        # Calculation reference
├── pyproject.toml
└── .python-version
```

## Usage

```bash
# Authenticate
arena auth login

# Local testing
arena test --smoke

# Submit for evaluation
arena submit
```
