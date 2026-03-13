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

## Tools

| Tool | Description | Key Inputs |
|------|-------------|-----------|
| `zotero_count` | Total item count | — |
| `zotero_stats` | Library statistics | `action`: `"summary"`, `"types"`, `"years"`, `"tags"`, `"attachments"` |
| `zotero_search` | Search/filter library | `action`: `"by_title"`, `"by_author"`, `"without_pdf"`, `"without_tags"`; `query`: string |
| `zotero_get_item` | Full record for one item | `item_key`: string |
| `zotero_children` | Attachments/notes for an item | `item_key`: string |
| `zotero_update_item` | Update item fields | `item_key`: string; `fields`: object |
| `zotero_tags` | Tag operations | `action`: `"list"`, `"add"`, `"remove"`, `"rename"`; `item_key`, `tag`, `new_tag` |
| `zotero_import` | Import by identifier | `action`: `"doi"`, `"isbn"`, `"pmid"`, `"arxiv"`; `identifier`: string |
| `zotero_batch_add` | Bulk import from file | `action`: `"from_file"`; `file_path`: string |
| `zotero_export` | Export items | `action`: `"bibtex"`, `"ris"`, `"json"`; `item_keys`: string[] |
| `zotero_collections` | Collection operations | `action`: `"list"`, `"create"`, `"add_item"`; `name`, `collection_key`, `item_key` |
| `zotero_trash_items` | Trash items | `item_keys`: string[] |
| `zotero_check_pdfs` | Check PDF attachment status | `item_keys?`: string[] |
| `zotero_crossref` | CrossRef metadata lookup | `doi`: string |
| `zotero_find_dois` | Find missing DOIs | `item_keys?`: string[] |
| `zotero_fetch_pdfs` | Download open-access PDFs | `item_keys?`: string[] |

## PDF Extraction

- Default extractor: `docling`
- Override extractor: set `ZOTERO_PDF_EXTRACTOR=mineru`
- Override MinerU binary: set `ZOTERO_MINERU_CMD=/path/to/magic-pdf`
