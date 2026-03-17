[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I57UKJ8)
# opencode-zotero-plugin
opencode-zotero-plugin wraps the Zotero API. It exists because agents cannot access local Zotero libraries directly — this tool bridges that gap by providing a CLI that reads/writes to a local SQLite db that stays in sync with the Zotero cloud.

## Configuration

Add to your OpenCode configuration:

```json
{
  "plugin": [
    "@dzackgarza/opencode-zotero-plugin@git+https://github.com/dzackgarza/opencode-zotero-plugin"
  ]
}
```

### MCP Configuration

Add to any MCP client config:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/dzackgarza/opencode-zotero-plugin.git",
        "opencode-zotero-plugin",
        "mcp"
      ]
    }
  }
}
```

### No-install usage

Drop-in command for agents:

```bash
uvx --from git+https://github.com/dzackgarza/opencode-zotero-plugin opencode-zotero-plugin --help
```

### Direct CLI usage

Direct CLI usage (bypasses plugin):

```bash
# Direct CLI usage (bypasses plugin)
cd python && uv run python -m zotero_librarian._cli --help
```

## Tools

### zotero_count

Use when you only need the total number of items in the Zotero library.

#### zotero_count Input

This tool takes no parameters.

#### zotero_count Example Input

```json
{}
```

#### zotero_count Output Contract

Returns a string containing just the integer count (e.g., `"142"`).

### zotero_stats

Use when you need aggregate library statistics such as summary, item types, years, tags, or attachment counts.

#### zotero_stats Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | `string` | Yes | 'summary', 'types', 'years', 'tags', or 'attachments' |

#### zotero_stats Example Input

```json
{
  "action": "summary"
}
```

#### zotero_stats Output Contract

Returns a JSON object matching the requested action's structure.
For `summary`, returns:
- `total_items`
- `item_types` (dict of counts)
- `collections` (count)
- `tags` (count)
- `years` (dict with `earliest`, `latest`)
- `attachments` (count)
- `notes` (count)

### zotero_search

Use when you need to search or filter the local Zotero library.

#### zotero_search Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | `string` | Yes | Search action |
| `query` | `string` | No | Search query for title, author, or DOI lookups |

#### zotero_search Example Input

```json
{
  "action": "by_title",
  "query": "Attention Is All You Need"
}
```

#### zotero_search Output Contract

Returns a JSON array of complete Zotero item objects matching the query. Each item object contains:
- `key`: Item identifier string
- `version`: Integer version number
- `library`: Object with `type`, `id`, `name`, `links`
- `links`: Object with `self`, `alternate`, `up` links
- `meta`: Object with `creatorSummary`, `parsedDate`, `numChildren`
- `data`: Complete item metadata object (e.g., `itemType`, `title`, `creators`, `date`, `tags`)

### zotero_get_item

Use when you need the full Zotero record for a specific item key.

#### zotero_get_item Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_key` | `string` | Yes | Zotero item key |

#### zotero_get_item Example Input

```json
{
  "item_key": "ABCDE123"
}
```

#### zotero_get_item Output Contract

Returns a single Zotero item JSON object for the given `item_key`.

### zotero_children

Use when you need attachments or notes for a Zotero item.

#### zotero_children Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_key` | `string` | Yes | Parent Zotero item key |

#### zotero_children Example Input

```json
{
  "item_key": "ABCDE123"
}
```

#### zotero_children Output Contract

Returns a JSON array of child item objects (attachments, notes) for the specified parent item.

### zotero_update_item

Use when you need to update fields on an existing Zotero item.

#### zotero_update_item Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_key` | `string` | Yes | Zotero item key |
| `fields` | `record(string, any)` | Yes | Fields to update |

#### zotero_update_item Example Input

```json
{
  "item_key": "ABCDE123",
  "fields": {
    "title": "Updated Title"
  }
}
```

#### zotero_update_item Output Contract

Returns a JSON object detailing the `success`, `operation`, `stage`, and `item_key`. On error, returns an object with `error` or `details`.

### zotero_tags

Use when you need to inspect or edit Zotero item tags.

#### zotero_tags Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | `string` | Yes | 'list', 'add', or 'remove' |
| `item_key` | `string` | No | Item key for add/remove operations |
| `tags` | `array(string)` | No | Tags to add or remove |

#### zotero_tags Example Input

```json
{
  "action": "add",
  "item_key": "ABCDE123",
  "tags": ["machine-learning", "review"]
}
```

#### zotero_tags Output Contract

For `list`, returns a JSON array of all tags. For `add` or `remove`, returns a JSON object with `success`, `operation`, `stage`, and `item_key`.

### zotero_import

Use when you need to import a DOI, ISBN, or PMID into Zotero.

#### zotero_import Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | `string` | Yes | 'by_doi', 'by_isbn', or 'by_pmid' |
| `identifier` | `string` | Yes | Identifier to import |

#### zotero_import Example Input

```json
{
  "action": "by_doi",
  "identifier": "10.1234/5678"
}
```

#### zotero_import Output Contract

Returns a JSON object containing `success`, `operation`, `stage`, and the newly created `item_key`.

### zotero_batch_add

Use when you need to import many identifiers into Zotero at once.

#### zotero_batch_add Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identifiers` | `array(string)` | Yes | Identifiers to import in order |
| `id_type` | `string` | No | 'doi', 'isbn', or 'pmid' |
| `collection` | `string` | No | Collection key to add imported items into |
| `tags` | `array(string)` | No | Tags to add to imported items |
| `force` | `boolean` | No | Skip duplicate detection |

#### zotero_batch_add Example Input

```json
{
  "identifiers": ["10.1234/1", "10.1234/2"],
  "id_type": "doi"
}
```

#### zotero_batch_add Output Contract

Returns a JSON object with overall `success`, and arrays of `successful_imports` and `failed_imports`.

### zotero_export

Use when you need a text export of the Zotero library.

#### zotero_export Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | `string` | Yes | 'json', 'bibtex', 'csv', 'ris', or 'csljson' |
| `collection` | `string` | No | Optional collection key filter |

#### zotero_export Example Input

```json
{
  "action": "bibtex"
}
```

#### zotero_export Output Contract

Returns a string containing the library exported in the specified text format.

### zotero_collections

Use when you need to inspect collections or move an item into one.

#### zotero_collections Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | `string` | Yes | 'list' or 'move_item' |
| `item_key` | `string` | No | Item key |
| `collection_key` | `string` | No | Collection key |

#### zotero_collections Example Input

```json
{
  "action": "list"
}
```

#### zotero_collections Output Contract

For `list`, returns a JSON array of collection objects. For `move_item`, returns a JSON object indicating `success`.

### zotero_trash_items

Use when you need to move one or more Zotero items to trash.

#### zotero_trash_items Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_keys` | `array(string)` | Yes | Item keys to move to trash |

#### zotero_trash_items Example Input

```json
{
  "item_keys": ["ABCDE123", "FGHIJ456"]
}
```

#### zotero_trash_items Output Contract

Returns a JSON object indicating `success`, `operation`, `stage`, and the `item_keys` moved to trash.

### zotero_check_pdfs

Use when you need a summary of which Zotero items are missing PDFs.

#### zotero_check_pdfs Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `collection` | `string` | No | Optional collection key filter |

#### zotero_check_pdfs Example Input

```json
{
  "collection": "XYZ987"
}
```

#### zotero_check_pdfs Output Contract

Returns a JSON object listing items missing PDFs, grouped or formatted according to the check structure.

### zotero_crossref

Use when you need to match citation text against the local Zotero library.

#### zotero_crossref Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | `string` | Yes | Citation text in Author (Year) form |
| `collection` | `string` | No | Optional collection key filter |

#### zotero_crossref Example Input

```json
{
  "text": "Smith (2020)"
}
```

#### zotero_crossref Output Contract

Returns a JSON array of matching items from the local library.

### zotero_find_dois

Use when you need CrossRef-powered DOI backfilling for local Zotero items.

#### zotero_find_dois Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `apply` | `boolean` | No | Write matched DOIs back to Zotero |
| `limit` | `number` | No | Maximum items to process |
| `collection` | `string` | No | Collection key filter |

#### zotero_find_dois Example Input

```json
{
  "apply": true,
  "limit": 10
}
```

#### zotero_find_dois Output Contract

Returns a JSON object with counts of processed items, matched DOIs, and (if `apply` is true) successfully updated items.

### zotero_fetch_pdfs

Use when you need to discover or attach open-access PDFs for Zotero items.

#### zotero_fetch_pdfs Input

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dry_run` | `boolean` | No | Show matches without downloading |
| `limit` | `number` | No | Maximum items to process |
| `collection` | `string` | No | Collection key filter |
| `download_dir` | `string` | No | Directory to save PDFs into |
| `upload` | `boolean` | No | Upload fetched PDFs to Zotero storage |
| `sources` | `array(string)` | No | PDF sources to try in order |

#### zotero_fetch_pdfs Example Input

```json
{
  "dry_run": true,
  "limit": 5
}
```

#### zotero_fetch_pdfs Output Contract

Returns a JSON object summarizing the operation:
- `processed`: Integer count of candidates evaluated
- `found`: Integer count of matching open-access PDFs found
- `attached`: Integer count of PDFs successfully attached/linked to Zotero
- `not_found`: Integer count of items without an available open-access PDF
- `skipped_no_doi`: Integer count of items skipped due to a missing DOI
- `skipped_has_pdf`: Integer count of items skipped because they already had a PDF
- `dry_run`: Boolean matching the input flag
- `results`: Array of per-item objects detailing the discovery status (`key`, `title`, `doi`, `status`, and optionally `source`, `pdf_url`, `saved_to`, `attachment_result`, `upload_result`)

## Environment Variables

| Name | Required | Default | Controls |
|------|----------|---------|----------|
| `ZOTERO_PDF_EXTRACTOR` | No | `docling` | PDF text extraction engine (e.g., `docling`, `mineru`) |
| `ZOTERO_MINERU_CMD` | No | — | Path to `magic-pdf` binary if `ZOTERO_PDF_EXTRACTOR` is `mineru` |

## Dependencies

| Dependency | Purpose |
|------------|---------|
| Node.js / Bun | Plugin runtime |
| Python 3.12+ | CLI / MCP runtime |
| Zotero API | Data source |

## Development Setup

For contributors working on the plugin locally:

```bash
direnv allow .
just install
```

## Checks

```bash
direnv allow .
just check
```

For targeted runs, use the canonical `justfile` entrypoints:

```bash
just typecheck
just test
```

## License

MIT
