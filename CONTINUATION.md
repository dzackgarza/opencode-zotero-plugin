# Continuation: opencode-zotero-plugin

## Current state

- Python package split: done. 16 modules in `python/src/zotero_librarian/`.
- `__init__.py`: minimal — only `get_zotero` + `__version__`. No re-exports.
- `_dispatch.py`: imports from specific submodules directly.
- Tests: all import from submodules. Offline tests pass (10/10).
- TS plugin `src/index.ts`: 9 composite tools shelling to `_dispatch.py`.
- MCP server `mcp-server/server.py`: 9 FastMCP tools via direct Python imports.
- `zotero/agents.py`: deleted.
- `zotero/_dev/scripts/manage.py`: deleted.
- `zotero/justfile`: rewired to `zotero-lib` CLI.

---

## 1. CRITICAL: Integrate `scripts/zotero.py` into the plugin

**This is the main unfinished task.** The remote Web API script at
`zotero/scripts/zotero.py` must become a proper module in the plugin,
not a separate standalone script.

### What it provides (not covered by local API modules)

- `add-doi` / `add-isbn` / `add-pmid` — lookup via Zotero translation server
  (distinct from the local-API `import_by_doi` which uses a different mechanism)
- `find-dois` — CrossRef lookup to fill in missing DOIs
- `fetch-pdfs` — Unpaywall/open-access PDF fetching
- `crossref` — cross-reference a text file of citations against the library
- `batch-add` — add multiple items from a file of DOIs/ISBNs
- `export` — BibTeX/RIS/CSL-JSON export via remote API

### Target module

Create `python/src/zotero_librarian/remote.py`:
- Move all logic from `scripts/zotero.py` into proper functions
- Config via `get_web_config()` reading `ZOTERO_API_KEY` + `ZOTERO_USER_ID` / `ZOTERO_GROUP_ID`
- Keep zero-stdlib-dependency constraint (or add `httpx` — already a dep)
- Functions: `web_items()`, `web_search()`, `web_get()`, `web_collections()`,
  `web_tags()`, `web_add_doi()`, `web_add_isbn()`, `web_add_pmid()`,
  `web_batch_add()`, `web_find_dois()`, `web_fetch_pdfs()`, `web_crossref()`,
  `web_export()`, `web_update()`, `web_delete()`

### Wire it into everything

1. **`pyproject.toml`**: no new deps needed (uses `httpx` already in deps)
2. **`_dispatch.py`**: add remote tool entries (keyed `remote_*`)
3. **`_cli.py`**: add `remote` subcommand group (or integrate into existing commands)
4. **`mcp-server/server.py`**: add `zotero_remote_*` tools
5. **`src/index.ts`**: add TS tool wrappers for remote operations
6. **`tests/test_remote.py`**: tests against live remote API (skip if no API key)
7. **Delete `zotero/scripts/zotero.py`** once migrated

---

## 2. Live Zotero tests

Zotero was not running during the last session. Once started:

```bash
# Full test suite
cd ./opencode-zotero-plugin/python
uv run pytest tests/ -v

# Specific verification commands from the plan
uv run python -m zotero_librarian._dispatch count_items '{}'
uv run zotero-lib stats summary
```

Expected: 146 currently-skipped tests become active.

Failures to look for:
- `_cli.py`: `find-similar-tags` command uses an inline python invocation instead
  of calling `similar_tags()` from `duplicates.py` — should be a proper subcommand.
- `_cli.py` `collections` subcommand uses `--item-key` / `--collection-key` flags
  that argparse needs to supply as `args.item_key` / `args.collection_key` — verify
  argparse uses underscores not hyphens for dest names.

---

## 3. TS plugin: live test

```bash
cd ./opencode-zotero-plugin
bun install   # already done
\opencode run --agent Minimal "How many items in my Zotero library?"
```

This exercises the full TS → `_dispatch.py` → local API path.

---

## 4. MCP server: install and smoke test

```bash
cd ./opencode-zotero-plugin/mcp-server
uv sync
uv run fastmcp run server.py
```

The `pyproject.toml` references `zotero-librarian` as an editable path dep
(`{ path = "../python", editable = true }`). Verify `uv sync` resolves it.

---

## 5. `_cli.py` bugs to fix before live testing

- `find-similar-tags` just recipe in `justfile` uses inline python. The `_cli.py`
  `search` subcommand doesn't have a `similar-tags` action. Add it.
- `tags` subcommand's `--item-key` / `--item_key` argparse dest: verify
  `args.item_key` not `args.item-key` (argparse converts hyphens to underscores
  for dest, so `--item-key` → `args.item_key` — should be fine, but confirm).
- `import` is a Python keyword — the subparser name `"import"` is fine as a
  string but confirm `args.command == "import"` works correctly in the handler
  dispatch dict (it does, but test it).

---

## 6. Update `zotero/SKILL.md`

Still references `scripts/zotero.py` as the tool interface. Once `remote.py` is
integrated and `scripts/zotero.py` is deleted, update SKILL.md to point to
`zotero-lib` (CLI) and the new plugin tools.

---

## 7. `zotero/AGENTS.md` cleanup

The bulk of `AGENTS.md` is still the old per-function table for `agents.py`.
After live testing confirms the new plugin works, replace the whole file with a
pointer to `../opencode-zotero-plugin/AGENTS.md`.

---

## 8. Register MCP server in system opencode config

Once verified, add to `./ai/` opencode config:
```json
{
  "mcp": {
    "zotero": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "./opencode-zotero-plugin/mcp-server", "fastmcp", "run", "server.py"]
    }
  }
}
```

---

## Order of operations

1. Integrate `remote.py` from `scripts/zotero.py` (Item 1 above — main task)
2. Start Zotero, run `uv run pytest tests/ -v` (Item 2)
3. Fix any `_cli.py` issues found (Item 5)
4. Run TS plugin live test (Item 3)
5. Run MCP server live test (Item 4)
6. Delete `zotero/scripts/zotero.py`, update `SKILL.md` and `AGENTS.md` (Items 6-7)
7. Register MCP in system config (Item 8)
