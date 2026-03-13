# opencode-zotero-plugin — Agent Guide

OpenCode plugin + MCP server for Zotero library management.

## Tools Available

| Tool | Description |
|------|-------------|
| `zotero_count` | Total item count |
| `zotero_stats` | Library stats: `summary`, `types`, `years`, `tags`, `attachments` |
| `zotero_search` | Search/filter: `by_title`, `by_author`, `without_pdf`, `without_tags`, `not_in_collection`, `duplicate_dois`, `duplicate_titles`, `invalid_dois` |
| `zotero_get_item` | Get single item by key |
| `zotero_update_item` | Update fields on an item |
| `zotero_tags` | Tag management: `list`, `add`, `remove` |
| `zotero_import` | Import: `by_doi`, `by_isbn` |
| `zotero_export` | Export: `json`, `bibtex` |
| `zotero_collections` | Collections: `list`, `move_item` |

## Architecture

```
src/index.ts          ← OpenCode plugin (TS), shells to Python _dispatch
python/src/
  zotero_librarian/
    client.py         ← get_zotero(), pagination helpers
    query.py          ← read-only queries and searches
    items.py          ← CRUD operations on items
    attachments.py    ← file upload/download/extract
    notes.py          ← note CRUD
    collections.py    ← collection CRUD
    tags.py           ← tag management
    batch.py          ← bulk operations
    export.py         ← JSON/CSV/BibTeX export
    import_.py        ← DOI/ISBN/arXiv/BibTeX import
    stats.py          ← library statistics
    sync.py           ← sync status
    duplicates.py     ← duplicate detection
    validation.py     ← DOI/ISBN/ISSN validators
    arxiv.py          ← arXiv search and download
    _dispatch.py      ← JSON-in/JSON-out CLI dispatcher
    _cli.py           ← human-friendly CLI (zotero-lib)
mcp-server/server.py  ← FastMCP server (direct Python imports)
```

## Dispatch Protocol

All tools accessible via:
```bash
python -m zotero_librarian._dispatch <tool_name> '<json_args>'
```

Example:
```bash
python -m zotero_librarian._dispatch count_items '{}'
python -m zotero_librarian._dispatch search_by_title '{"query": "transformer"}'
python -m zotero_librarian._dispatch library_summary '{}'
```

## CLI (Human Use)

```bash
zotero-lib count
zotero-lib stats summary
zotero-lib search by-title "attention mechanism"
zotero-lib search without-pdf
zotero-lib collections list
zotero-lib tags list
zotero-lib import doi 10.1038/nature12345
zotero-lib export json --output library.json
```

## MCP Server

```bash
cd mcp-server && uv run fastmcp run server.py
```

## Testing

```bash
just typecheck
just test-import
just test
```

## Prerequisites

- Zotero 7+ running with local API enabled:
  `Edit → Settings → Advanced → "Allow other applications to communicate with Zotero"`
- Python 3.13+, `uv`
- Bun (for TS plugin)
