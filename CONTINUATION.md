# Continuation: opencode-zotero-plugin

## Source of truth

- Use `REQUIREMENTS.md` as the canonical continuation and release-gating document.
- Do not revive the old Zotero Web API / `remote.py` migration plan. The current product direction is local-only.
- Reads come from the local Zotero API. Writes go through `/connector/...` plus the add-on endpoints configured in `python/src/zotero_librarian/config.yaml` and discovered from the add-on version probe.

## Current implementation status

- PR #22 merged into `main` on 2026-03-10 and implemented issues #9, #10, #12-#16, #18, and #20.
- PR #23 merged into `main` on 2026-03-10 and implemented issue #11 (Better BibTeX lookup) and issue #17 (Markdown PDF extraction with `docling` default and optional `mineru`).
- Open GitHub issues: none.
- Main surfaces:
  - TypeScript plugin: `src/index.ts`
  - Python dispatcher: `python/src/zotero_librarian/_dispatch.py`
  - Human CLI: `python/src/zotero_librarian/_cli.py`
  - MCP server: `mcp-server/server.py`
- Extraction direction:
  - single public entrypoint: `extract_and_attach_text(...)`
  - Markdown attachment output only
  - `docling` by default
  - optional `mineru` selected via `ZOTERO_PDF_EXTRACTOR` and `ZOTERO_MINERU_CMD`

## Fresh verification snapshot

- `bun install`
- `bun run typecheck`
- `cd python && uv run python -c 'import zotero_librarian; print("Python import OK")'`
- `cd python && uv run pytest tests/test_validation.py tests/test_dispatch.py -v`
- `cd mcp-server && uv run python -c 'import server; print("ok")'`

Live Zotero-dependent proof has not been rerun in this handoff.

## Current repo state

- The local checkout is still on `pr-impl`, but `origin/main` already contains the merged work.
- Start new feature work from updated `main` or a fresh branch from it.
- Review existing tracked local changes before rebasing or committing. At the time of this handoff, `justfile` and `mcp-server/uv.lock` already differed from HEAD.
- Generated local artifacts such as `node_modules/`, `.serena/`, and `__pycache__/` are not source.

## Next meaningful work

- Run the live proof gates from `REQUIREMENTS.md` with Zotero 7 running and the local add-on endpoints available:
  - `cd python && uv run pytest tests/ -v`
  - `cd python && uv run python -m zotero_librarian._dispatch count_items '{}'`
  - `cd python && uv run zotero-lib stats summary`
  - `\opencode run --agent plugin-proof 'How many items in my Zotero library?'`
- Verify explicit structured failure paths for local write operations, not just successful writes.
- Prove trash semantics locally if the bridge is available. This remains non-gating but still open in `REQUIREMENTS.md`.
- Keep sync conflict resolution out of release gating unless `REQUIREMENTS.md` is updated to promote it.

## Known pitfalls

- The previous version of this file pointed to a forbidden Web API continuation path. Ignore that plan.
- Run `bun install` before `bun run typecheck`. Without a local install, the command may fall back to an older global `tsc`.
- Do not reopen issue #21 as a ChromaDB/vector-store task. Current direction is keyword search over extracted Markdown plus local semantic search over `.md` files.
