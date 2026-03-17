# README.md full compliance audit - comprehensive fixes needed

## Requested outcome
The `README.md` file has been fully updated to comply with the project standards outlined in `README_STANDARDS.md` (and detailed in the issue), addressing 11 specific compliance gaps.

## Requirements from issue
1. Ko-fi badge missing: Add `[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I57UKJ8)` to Line 1.
2. H1 + One-line description: Use short H1 name `# opencode-zotero-plugin` and add existence justification: `opencode-zotero-plugin wraps the Zotero API. It exists because agents cannot access local Zotero libraries directly — this tool bridges that gap by providing a CLI that reads/writes to a local SQLite db that stays in sync with the Zotero cloud.`
3. Section naming: Split into `## Configuration` (JSON config snippet) and `## Development Setup` (for contributors, direnv + just install).
4. MCP Configuration: Add `### MCP Configuration` under `## Configuration` with the JSON snippet.
5. Tools section: Add `## Tools` section documenting each tool the plugin exposes (name, parameter schema table, fenced JSON example input).
6. Dependencies: Add `## Dependencies` table listing Python 3.12+ (Runtime) and Zotero API (Data source).
7. Environment Variables: Use exactly `| Name | Required | Default | Controls |` columns with em dash (`—`) for empty defaults.
8. Checks: Update `## Checks` section to show both `direnv allow .` and `just check`.
9. No-install usage: Add drop-in command for agents: `uvx --from git+https://github.com/dzackgarza/opencode-zotero-plugin opencode-zotero-plugin --help`.
10. Direct CLI bypass: Document direct CLI usage bypassing plugin: `opencode-zotero-plugin --help`.
11. Output contracts: Document exact return structure for each tool (we can extract this info if available, or state what to expect).
- Adhere to the canonical section order: Ko-fi badge, H1, description, Configuration (w/ MCP), Tools, Environment Variables, Dependencies, Development Setup, Checks, License.

## Implementation plan
- Rewrite `README.md` entirely to incorporate all the structural requirements.
- Extract tool parameter schemas from `src/index.ts` to populate the `## Tools` section.
- Extract tool return values / contracts to populate the output contracts in `## Tools`.
- Create `.envrc`? (Only if explicitly requested, but we'll include `direnv allow .` in the docs as required by standard).

## Verification
- Run `cat README.md` to ensure the structure strictly follows the requested canonical order.
- Ensure all 11 gaps from the issue description are met.
- Ensure the Markdown renders correctly.

## Blockers
- Output contracts are not heavily defined in the current README. I'll need to infer them from `src/index.ts` or add generic placeholders if the structure is variable. However, I will do my best to provide a specific structure based on standard success/error return shapes mentioned in `src/index.ts` or `REQUIREMENTS.md`.
