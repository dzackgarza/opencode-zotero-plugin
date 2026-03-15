# opencode-zotero-plugin

CLI-first Zotero integration for local Zotero 7, with a thin OpenCode plugin adapter and FastMCP wrapper.

## Architecture

Canonical implementation:

- Python library in `python/src/zotero_librarian/`
- Typer CLI entrypoint: `zotero-lib`
- JSON bridge command: `zotero-lib dispatch <tool_name> '<json_args>'`

Thin adapters:

- OpenCode plugin: `src/index.ts` delegates to `zotero-lib dispatch ...`
- MCP server: `mcp-server/server.py` delegates to the same Python package surface

## Prerequisites

- Zotero 7+ running locally with:
  `Edit -> Settings -> Advanced -> "Allow other applications to communicate with Zotero"`
- Python 3.13+
- `uv`
- Bun (for plugin typecheck)

## CLI First (Primary Surface)

Run from this repo:

```bash
cd python
uv run zotero-lib --help
```

Progressive-disclosure examples:

```bash
uv run zotero-lib stats --help
uv run zotero-lib stats summary

uv run zotero-lib search --help
uv run zotero-lib search by-title "attention mechanism"

uv run zotero-lib tags --help
uv run zotero-lib tags add ABCD1234 "reading,ml"

uv run zotero-lib import --help
uv run zotero-lib import doi 10.1038/nature12345

uv run zotero-lib export --help
uv run zotero-lib export bibtex --output library.bib
```

Low-level machine bridge:

```bash
uv run zotero-lib dispatch count_items '{}'
uv run zotero-lib dispatch search_by_title '{"query":"transformer"}'
```

## OpenCode Plugin Registration (Secondary Surface)

Install package:

```bash
npm install @dzackgarza/opencode-zotero-plugin
```

Register in OpenCode config (example):

```json
{
  "plugin": ["@dzackgarza/opencode-zotero-plugin"]
}
```

Plugin tools are thin delegates to the Python CLI/dispatch layer.

## MCP Server

```bash
cd mcp-server
uv run fastmcp run server.py
```

## Validation

Use the repo recipes:

```bash
just install
just check
```

Optional full Python tests (requires running Zotero):

```bash
just test
```
