# Zotero Plugin — Available Tools

## Local API Tools (`_dev/`) — Primary

**Requires Zotero 7+ running with local API enabled:**
Edit → Settings → Advanced → "Allow other applications to communicate with Zotero"

### Setup

```bash
# Install dependencies
cd _dev && uv sync

# Use just commands
just stats
just quality

# Or use Python API
from agents import ZoteroAgent
lib = ZoteroAgent()
```

---

### Library Overview

| Tool | Description | Example |
|------|-------------|---------|
| `library_stats()` | Item counts, collections, attachment rates | `lib.library_stats()` |
| `find_quality_issues()` | All quality issues grouped by type | `lib.find_quality_issues()` |
| `list_collections()` | All collections with item counts | `lib.list_collections()` |
| `list_tags()` | All tags with frequency counts | `lib.list_tags()` |
| `find_empty_collections()` | Collections with no items | `lib.find_empty_collections()` |
| `find_single_item_collections()` | Collections with exactly one item | `lib.find_single_item_collections()` |

**just commands:** `just stats`, `just quality`, `just list-collections`, `just list-tags`

---

### Search and Query

| Tool | Description | Example |
|------|-------------|---------|
| `search_by_title(query)` | Search items by title substring | `lib.search_by_title("transformer")` |
| `search_by_author(name)` | Search items by author name | `lib.search_by_author("Vaswani")` |
| `search_by_abstract(query)` | Search items by abstract substring | `lib.search_by_abstract("attention")` |
| `search_fulltext(query)` | Full-text search across all fields | `search_fulltext(zot, "neural network")` |
| `search_by_year(year)` | Filter items by publication year | `search_by_year(zot, 2024)` |
| `search_by_year_range(start, end)` | Filter items by year range | `search_by_year_range(zot, 2020, 2024)` |
| `search_by_collection(key)` | Get all items in a collection | `search_by_collection(zot, "ABC123")` |
| `search_by_tag(tag)` | Get all items with a tag | `search_by_tag(zot, "important")` |
| `search_advanced(filters)` | Advanced multi-field search | `search_advanced(zot, {"author": "X", "year": 2024})` |
| `search_notes(query)` | Search note content | `search_notes(zot, "todo")` |

---

### Find Items by Missing Content

| Tool | Description | Example |
|------|-------------|---------|
| `find_items_without_pdf()` | Items missing PDF attachments | `lib.find_items_without_pdf()` |
| `find_items_without_attachments()` | Items without any attachments | `lib.find_items_without_attachments()` |
| `find_items_without_tags()` | Items without tags | `lib.find_items_without_tags()` |
| `find_items_not_in_collection()` | Items not filed in any collection | `lib.find_items_not_in_collection()` |
| `items_without_abstract()` | Items missing abstracts | — |
| `items_missing_required_fields()` | Items missing required fields by type | — |
| `items_without_cites()` / `items_without_cited_by()` | Items without citation relations | — |
| `preprints_without_doi()` | Preprints missing DOIs | — |

**just commands:** `just find-no-pdf`

---

### Duplicate Detection

| Tool | Description | Example |
|------|-------------|---------|
| `find_duplicates_by_title()` | Items with duplicate titles | `lib.find_duplicates_by_title()` |
| `find_duplicates_by_doi()` | Items with duplicate DOIs | `lib.find_duplicates_by_doi()` |
| `find_name_variations()` | Author name format variations | `lib.find_name_variations()` |
| `find_journal_variations()` | Journal name variations | `lib.find_journal_variations()` |
| `find_similar_tags()` | Similar tags (typos/variations) | `lib.find_similar_tags()` |

**just commands:** `just find-duplicates`, `just find-similar-tags`

---

### Validation

| Tool | Description | Example |
|------|-------------|---------|
| `items_with_invalid_doi()` | Items with invalid DOI format | — |
| `items_with_invalid_isbn()` | Items with invalid ISBN format | — |
| `items_with_invalid_issn()` | Items with invalid ISSN format | — |
| `items_with_broken_urls()` | Items with malformed URLs | — |
| `items_with_placeholder_titles()` | Items with placeholder titles | — |

---

### Item Operations

| Tool | Description | Example |
|------|-------------|---------|
| `get_item(key)` | Get single item by key | `lib.get_item("VNPN6FHT")` |
| `get_attachments(key)` | Get attachment info for item | `lib.get_attachments("VNPN6FHT")` |
| `add_tags(key, tags)` | Add tags to item | `lib.add_tags("VNPN6FHT", ["important"])` |
| `remove_tags(key, tags)` | Remove tags from item | `lib.remove_tags("VNPN6FHT", ["unread"])` |
| `add_to_collection(key, coll)` | Add item to collection | `lib.add_to_collection("VNPN6FHT", "ABC123")` |
| `move_to_collection(key, coll)` | Move item to collection | `lib.move_to_collection("VNPN6FHT", "ABC123")` |
| `remove_from_collection(key, coll)` | Remove item from collection | `lib.remove_from_collection("VNPN6FHT", "ABC123")` |
| `update_fields(key, fields)` | Update item metadata | `lib.update_fields("VNPN6FHT", {"title": "New Title"})` |
| `delete_item(key)` | Move item to trash | `lib.delete_item("VNPN6FHT")` |

---

### Attachment Operations

| Tool | Description | Example |
|------|-------------|---------|
| `upload_pdf(parent_key, path)` | Upload PDF to Zotero storage | `upload_pdf(zot, "ABC123", "/path/to/file.pdf")` |
| `download_attachment(key, path)` | Download attachment to local file | `download_attachment(zot, "XYZ789", "/path/to/save.pdf")` |
| `delete_attachment(key)` | Delete attachment (move to trash) | `delete_attachment(zot, "XYZ789")` |
| `extract_text_from_pdf(key)` | Extract text from PDF attachment | `extract_text_from_pdf(zot, "XYZ789")` |
| `attach_url(parent, url)` | Attach URL/link to item | `attach_url(zot, "ABC123", "https://...")` |
| `attach_note(parent, text)` | Add note to item | `attach_note(zot, "ABC123", "Note text")` |

---

### arXiv Tools (`arxiv_tools.py`)

| Tool | Description | Example |
|------|-------------|---------|
| `search_arxiv_papers(query)` | Search arXiv papers | `search_arxiv_papers("transformer attention")` |
| `download_arxiv_paper(id)` | Download paper PDF | `download_arxiv_paper("2301.12345")` |
| `list_downloaded_papers(dir)` | List local downloaded papers | `list_downloaded_papers("~/papers")` |
| `read_arxiv_paper(id, dir)` | Read paper content | `read_arxiv_paper("2301.12345", "~/papers")` |
| `get_arxiv_paper_metadata(id)` | Get paper metadata | `get_arxiv_paper_metadata("2301.12345")` |
| `import_arxiv_paper(id)` | Import paper to Zotero | `import_arxiv_paper("2301.12345")` |
| `export_papers_to_json()` | Export papers to JSON | — |
| `import_papers_from_json()` | Import papers from JSON | — |

---

## Legacy Web API Tools (`scripts/zotero.py`) — Deprecated

**Requires environment variables:**
```bash
ZOTERO_API_KEY   # Create at https://www.zotero.org/settings/keys/new
ZOTERO_USER_ID   # Numeric user ID (or ZOTERO_GROUP_ID for group libraries)
```

All commands use: `python3 scripts/zotero.py <command> [options]`

### Read Operations

| Command | Description | Local API Equivalent |
|---------|-------------|---------------------|
| `items` | List top-level library items | ✅ `all_items()`, `library_stats()` |
| `search` | Search items by query string | ✅ `search_fulltext()`, `search_by_title()`, `search_by_author()` |
| `get` | Get full item details + attachments | ✅ `get_item()`, `get_attachments()` |
| `collections` | List all collections | ✅ `list_collections()` |
| `tags` | List all tags | ✅ `list_tags()` |
| `children` | List attachments/notes for an item | ✅ `get_attachments()`, `get_notes()` |
| `check-pdfs` | Report which items have/lack PDFs | ✅ `find_items_without_pdf()` |

### Add Operations

| Command | Description | Local API Equivalent |
|---------|-------------|---------------------|
| `add-doi` | Add item by DOI | ❌ No analogue (arXiv import only) |
| `add-isbn` | Add item by ISBN | ❌ No analogue |
| `add-pmid` | Add item by PubMed ID | ❌ No analogue |
| `batch-add` | Add multiple items from file | ❌ No analogue |

### Update Operations

| Command | Description | Local API Equivalent |
|---------|-------------|---------------------|
| `update` | Modify item metadata/tags | ✅ `update_fields()`, `add_tags()`, `remove_tags()` |
| `find-dois` | Find & add missing DOIs via CrossRef | ❌ No analogue |
| `fetch-pdfs` | Fetch open-access PDFs (Unpaywall, etc.) | ❌ No analogue |

### Delete Operations

| Command | Description | Local API Equivalent |
|---------|-------------|---------------------|
| `delete` | Move items to trash | ✅ `delete_item()` |

### Export Operations

| Command | Description | Local API Equivalent |
|---------|-------------|---------------------|
| `export` | Export as BibTeX/RIS/CSL-JSON | ❌ No analogue |

### Analysis Operations

| Command | Description | Local API Equivalent |
|---------|-------------|---------------------|
| `crossref` | Cross-reference citations vs library | ❌ No analogue |

---

## Global Flags (Legacy)

| Flag | Description |
|------|-------------|
| `--json` | JSON output (for scripting with `items`, `search`, `get`) |
| `--limit N` | Max items to return (default 25) |
| `--sort FIELD` | Sort by `dateModified`, `title`, `creator`, `date` |
| `--direction asc\|desc` | Sort direction |
| `--collection KEY` | Filter by or add to collection |
| `--type TYPE` | Filter by item type (e.g., `journalArticle`, `book`) |
| `--tags "tag1,tag2"` | Add tags when creating items |
| `--force` | Skip duplicate detection on add commands |

---

## Legacy Workflows

### Add a paper by DOI
```bash
python3 zotero.py add-doi "10.1093/jamia/ocaa037" --tags "review"
```

### Bulk add from file
```bash
python3 zotero.py batch-add dois.txt --type doi --tags "imported"
```

### Export bibliography
```bash
python3 zotero.py export --format bibtex --output refs.bib
```

### Update tags
```bash
python3 zotero.py update VNPN6FHT --add-tags "important" --remove-tags "unread"
```

### Find missing DOIs (dry-run first)
```bash
python3 zotero.py find-dois --limit 20      # Preview
python3 zotero.py find-dois --apply         # Actually write
```

### Fetch open-access PDFs
```bash
python3 zotero.py fetch-pdfs --dry-run --limit 10   # Preview
python3 zotero.py fetch-pdfs --limit 20             # Attach as linked URLs
python3 zotero.py fetch-pdfs --upload --limit 10    # Upload to Zotero storage
```

### Scripting with JSON
```bash
python3 zotero.py --json items --limit 100 | jq '.items[].DOI'
python3 zotero.py --json get VNPN6FHT | jq '.title'
```

---

## Notes

### Local API Tools
- **Requires Zotero 7+** running with local API enabled
- **No truncation** — all functions return complete data
- **Non-destructive** — `delete_item()` moves to trash, doesn't permanently delete
- **Agent composes workflows** — library provides building blocks, not automation

### Legacy Web API Tools
- **Zero dependencies** — Python 3 stdlib only
- **Duplicate detection** enabled by default on `add-doi`, `add-isbn`, `add-pmid`
- **Dry-run by default** for `find-dois` and `fetch-pdfs` — use `--apply` to write
- **Rate limiting** built-in (1s between CrossRef/Unpaywall requests)
- **Input validation**: DOIs must be `10.xxxx/...`, item keys are 8-char alphanumeric

For troubleshooting, see [references/troubleshooting.md](references/troubleshooting.md).
