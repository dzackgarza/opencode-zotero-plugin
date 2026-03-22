# opencode-zotero-plugin

OpenCode plugin wrapper for the local `zotero-librarian` CLI.

## What It Exposes

- Read tools:
  - `zotero_count`
  - `zotero_stats`
  - `zotero_search`
  - `zotero_get_item`
  - `zotero_export`
  - `zotero_check_pdfs`
  - `zotero_crossref`
  - `zotero_find_dois`
  - `zotero_fetch_pdfs`
- Write tools:
  - `zotero_import`
  - `zotero_update_item`
  - `zotero_tags`
  - `zotero_collections`
  - `zotero_delete_items`

## Runtime Requirements

- Zotero 7+ running locally
- Zotero local API enabled:
  - `Edit -> Settings -> Advanced -> Allow other applications to communicate with Zotero`
- For write tools, the local write add-on must also be installed on the same Zotero instance
- `uv` for running the Python CLI
- Bun for the plugin package and integration tests

Repo-root [`opencode.json`](./opencode.json) is the canonical proof config for this repo. CI starts `opencode serve` from the repo root and relies on standard global-plus-project config precedence.

## Tool Routing

The TypeScript wrapper shells into the Python dispatcher:

```bash
uvx --from "$ZOTERO_LIBRARIAN_CLI_SPEC" python -m zotero_librarian._dispatch <tool_name> '<json_args>'
```

Read operations use Zotero's built-in local API on `http://127.0.0.1:23119/api/...`.
Write operations depend on the local write add-on endpoints exposed by the running Zotero desktop app.

## Testing

Run the wrapper proof through the package justfile:

```bash
just test
```

CI is the canonical proof environment. For local debugging, start a repo-local OpenCode server from this checkout, set `OPENCODE_BASE_URL`, and then run the same `just` entrypoints.
