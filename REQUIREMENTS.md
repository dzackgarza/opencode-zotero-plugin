# Zotero Local Integration Requirements

This document is the source of truth for continuation and release gating of the local Zotero refactor.

## Priority Rule

Implementation comes before proof.
Missing local write functionality is the highest priority.
Tests, live proofs, and other gates apply after the required implementation checklist below is complete enough to verify.

## Hard Requirements

1. Do not use the Zotero Web API.
   Use neither `api.zotero.org` nor Zotero API keys, user IDs, group IDs, or Web-API write helpers.
1. Use the local Zotero surfaces only.
   Reads come from `http://127.0.0.1:23119/api/...`.
   Writes come from local desktop surfaces such as `http://127.0.0.1:23119/connector/...`
   and installed local plugin endpoints such as `http://127.0.0.1:23119/fulltext-attach`
   and `http://127.0.0.1:23119/opencode-zotero-write`.
1. External enrichment remains allowed.
   Crossref, PubMed, Unpaywall, Semantic Scholar, arXiv, and similar metadata/PDF sources are in scope.
1. Agents must be able to write locally.
   Required capabilities:
   create and import items;
   edit existing item metadata;
   add, remove, rename, and merge tags on existing items;
   attach PDFs and other files;
   attach markdown or note text;
   place or finalize items into collections.
1. Deletion is not a release requirement.
   Permanent delete is forbidden.
   If a delete surface exists, it must mean move to trash only, and it must not claim success until the local trash path is proven.
1. Silent fallbacks are forbidden.
   No broad `except Exception: pass`, no `return None` on user-facing failures, no hidden retries that erase the real failing stage.
1. Mutating operations must return structured results end to end.
   Required fields:
   `success`, `operation`, `stage`, `error`, `details`, and the relevant item or collection identifiers.
1. Plugin, CLI, dispatcher, and MCP surfaces must preserve the same failure detail.
   A local write failure may not be flattened into a generic command failure.
1. Proof must use real Zotero and real external services.
   Mocks do not satisfy completion for this refactor.

## Implementation Checklist

### Required capabilities

- [x] Local read path uses `http://127.0.0.1:23119/api/...`.
- [x] New item creation/import uses connector-backed local writes.
- [x] External enrichment remains allowed.
- [x] Structured mutating-operation results exist and are surfaced instead of silent skips for the patched paths.
- [x] Batch/enrichment accounting no longer counts failed attachment or update attempts as success.
- [x] Existing-item metadata edits are implemented through a local write surface.
- [x] Existing-item tag edits are implemented through a local write surface.
  Add, remove, rename, merge, and delete-on-item semantics.
- [x] Existing-item collection placement/finalization is implemented through a local write surface.
- [x] Existing-item PDF and file attachment writes are implemented through the installed `/fulltext-attach` plugin endpoint.
- [x] Existing-item link attachment writes are implemented through a local write surface.
- [x] Existing-item markdown/note attachment writes are implemented through a local write surface.
- [x] Existing note edits are implemented through a local write surface.
- [x] Consumer write paths probe the installed local Zotero add-on version and gate on a minimum supported version before calling plugin endpoints.

### Explicitly non-gating or legacy surfaces

- [x] Trash write semantics are implemented through the local plugin bridge.
- [ ] Trash write semantics are proven locally.
  This is intentionally non-gating until the bridge is built, installed, and proven live.
- [x] Collection create, rename, and move writes are implemented through a local write surface.
- [x] Collection merge and trash semantics are implemented through a local write surface.
  These are not part of the current release-critical set unless promoted later.
- [ ] Sync conflict resolution remains in scope.
  This is currently out of scope for the connector refactor and should not gate release.

## Temporary Allowance During Refactor

- An operation may return an explicit structured write-surface failure only as a stopgap while the connector-backed implementation is still missing.
- Such a stopgap does not satisfy the requirement for any capability listed above under local writes.
- Temporary explicit failures are acceptable only for non-required operations or for trash semantics that are intentionally blocked on a proven local path.

## Required Proof Gates

- Proof gates are downstream of the implementation checklist above. They do not replace it.
- Fresh live Python tests against the local Zotero instance with `0` failures for:
  `test_write_contract_local_api.py`
  and the relevant enrichment and export coverage.
- Fresh `bun run typecheck` at the package root.
- Fresh `uv run python -c 'import server; print("ok")'` inside `mcp-server/`.
- At least one real `process.env.OPENCODE_BIN || "opencode" run` proof for a successful local write path.
- At least one real `process.env.OPENCODE_BIN || "opencode" run` proof for an explicit structured local failure path when a capability is intentionally still gated.
- No counters or summaries may count failed attachment, import, or metadata-update attempts as success.

## Continuation Focus

- Replace any remaining explicit write-surface placeholders for required capabilities with real local write-surface implementations.
- Keep this checklist current as each required capability moves from explicit placeholder to real local write-surface implementation.
- Keep collection and trash semantics safe. Never permanently delete anything.
- Keep live export tests aligned with actual Zotero formatted-export behavior.
- Treat this file as the gating checklist for future continuation work.

## Non-Goals

- Reintroducing the Zotero Web API.
- Permanent deletion.
- Restart-based debugging or cache-based explanations.
