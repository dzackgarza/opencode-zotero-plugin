# opencode-zotero-plugin

OpenCode plugin + MCP server for Zotero library management.
This tool exists to allow agents to interact with a local Zotero library, enabling them to search, read, create, and manage Zotero items directly from your machine.

## Install

```bash
direnv allow
npm install @dzackgarza/opencode-zotero-plugin
```

## Checks

Run all project checks using `just`:

```bash
just check
```

## PDF Extraction

PDF extraction attaches Markdown back to the Zotero item.

- Default extractor: `docling`
- Override extractor: set `ZOTERO_PDF_EXTRACTOR=mineru`
- Override MinerU binary: set `ZOTERO_MINERU_CMD=/path/to/magic-pdf`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ZOTERO_USER_ID` | Zotero User ID | `0` |
| `ZOTERO_API_KEY` | Zotero API Key | `local` |
| `ZOTERO_LIBRARIAN_CONFIG` | Path to custom config.yaml | *builtin config* |
| `ZOTERO_PDF_EXTRACTOR` | PDF extractor to use (`docling` or `mineru`) | `docling` |
| `ZOTERO_MINERU_CMD` | Path to `magic-pdf` binary for MinerU | `magic-pdf` |

## License

MIT
