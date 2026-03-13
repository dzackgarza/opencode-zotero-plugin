[![Ko-Fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I57UKJ8)

# opencode-zotero-plugin

OpenCode plugin that reads items from a local Zotero library, extracts PDF attachments to Markdown, and writes the result back to the Zotero item.

## Features

- Fetches items and attachments from the Zotero local API
- Extracts PDF text to Markdown using `docling` (default) or `mineru`
- Writes extracted Markdown back as a note attachment on the Zotero item
- Exposes tools for searching and retrieving library items to OpenCode agents

## Installation

```bash
npm install @dzackgarza/opencode-zotero-plugin
```

Repo-local verification uses [`.envrc`](./.envrc), [`.config/opencode.json`](./.config/opencode.json), and a checked-in symlink under [`.config/plugins`](./.config/plugins) so OpenCode loads the real plugin without a machine-specific `file://` path.

## Environment Variables

| Name | Required | Default | Controls |
|------|----------|---------|---------|
| `ZOTERO_API_KEY` | Yes | — | Zotero Web API key |
| `ZOTERO_USER_ID` | Yes | — | Zotero user ID |
| `ZOTERO_PDF_EXTRACTOR` | No | `docling` | PDF extractor: `docling` or `mineru` |
| `ZOTERO_MINERU_CMD` | No | `magic-pdf` | Path to MinerU binary (used when extractor is `mineru`) |

## Side Effects

- Writes extracted Markdown back to the Zotero item as a note attachment via the Zotero local API.
- Reads PDF files from the local Zotero data directory.

## External Dependencies

- [Zotero](https://www.zotero.org/) desktop app running locally with the local API enabled
- [docling](https://github.com/DS4SD/docling) or [MinerU](https://github.com/opendatalab/MinerU) for PDF extraction

## PDF Extraction

- Default extractor: `docling`
- Override extractor: set `ZOTERO_PDF_EXTRACTOR=mineru`
- Override MinerU binary: set `ZOTERO_MINERU_CMD=/path/to/magic-pdf`
