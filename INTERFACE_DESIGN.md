# Interface Design — Zotero Librarian

A two-tier interface: simple tools for everyday work, deeper tools for detailed library manipulation.

---

## Tier 1: Everyday Tools (`agents.py`)

High-level agent interface. All methods return complete data without truncation.

### Library Overview

| Method | Returns |
|--------|---------|
| `stats()` | Item count, collection count, tag count, items with/without PDF |
| `quality_issues()` | All quality problems grouped by type |
| `collections()` | All collections with item counts |
| `tags()` | All tags with frequency counts |

### Search

| Method | Returns |
|--------|---------|
| `search_title(query)` | Items where title contains query |
| `search_author(name)` | Items where author name matches |
| `search_abstract(query)` | Items where abstract contains query |
| `search_fulltext(query)` | Items matching query in any field or attachment content |
| `search_by_year(year)` | Items published in specific year |
| `search_by_tag(tag)` | Items with specific tag |
| `search_by_collection(key)` | Items in specific collection |

### Find Issues

| Method | Returns |
|--------|---------|
| `without_pdf()` | Items missing PDF attachments |
| `without_attachments()` | Items without any attachments |
| `without_tags()` | Untagged items |
| `not_in_collection()` | Items not filed in any collection |
| `duplicate_titles()` | Items grouped by identical title |
| `duplicate_dois()` | Items grouped by identical DOI |

### Item Operations

| Method | Returns |
|--------|---------|
| `get(key)` | Single item by key |
| `attachments(key)` | Attachments for item |
| `add_tags(key, tags)` | API response |
| `remove_tags(key, tags)` | API response |
| `add_to_collection(key, coll)` | API response |
| `move_to_collection(key, coll)` | API response |
| `update(key, fields)` | API response |
| `delete(key)` | API response |

### arXiv Import

| Method | Returns |
|--------|---------|
| `arxiv_search(query)` | Papers matching query |
| `arxiv_import(id)` | Imported item |
| `arxiv_download(id, dir)` | Local file path |

---

## Tier 2: Deep Tools (`_dev/src/zotero_librarian/`)

Low-level primitives for detailed library manipulation.

### Core Primitives

| Function | Purpose |
|----------|---------|
| `get_zotero()` | Initialize local API client |
| `all_items(zot)` | Generator: all items |
| `all_items_by_type(zot, type)` | Generator: items by type |
| `count_items(zot)` | Total item count |
| `get_item(zot, key)` | Single item by key |
| `get_attachments(zot, key)` | Attachments for item |
| `get_notes(zot, key)` | Notes for item |
| `get_citations(zot, key)` | Citation relations |

### Query Primitives

| Function | Purpose |
|----------|---------|
| `items_without_pdf(zot)` | Items missing PDFs |
| `items_without_attachments(zot)` | Items without attachments |
| `items_without_tags(zot)` | Untagged items |
| `items_not_in_collection(zot)` | Orphaned items |
| `items_missing_required_fields(zot, type, fields)` | Incomplete items |
| `duplicate_dois(zot)` | Duplicate DOI groups |
| `duplicate_titles(zot)` | Duplicate title groups |

### Write Primitives

| Function | Purpose |
|----------|---------|
| `update_item_fields(zot, key, fields)` | Update metadata |
| `add_tags_to_item(zot, key, tags)` | Add tags |
| `remove_tags_from_item(zot, key, tags)` | Remove tags |
| `move_item_to_collection(zot, key, coll)` | Move to collection |
| `attach_pdf(zot, parent, path)` | Attach PDF |
| `attach_url(zot, parent, url)` | Attach URL |
| `attach_note(zot, parent, text)` | Add note |
| `upload_pdf(zot, parent, path)` | Upload PDF to storage |
| `download_attachment(zot, key, path)` | Download attachment |
| `delete_item(zot, key)` | Move to trash |

---

## Gaps to Fill

### Tier 1 (Everyday Tools)

| Tool | Status |
|------|--------|
| `add_doi(doi)` | Missing |
| `add_isbn(isbn)` | Missing |
| `export_bibtex(collection)` | Missing |
| `lookup(citekey)` | Missing |

### Tier 2 (Deep Tools)

| Tool | Status |
|------|--------|
| `find_duplicate_titles_fuzzy(zot, threshold)` | Partial (exact only) |
| `clean_missing_pdfs(zot)` | Missing |
| `rename_pdf_attachments(zot)` | Missing |
| `delete_snapshots(zot)` | Missing |
| `pdf_status(zot)` | Missing |
| `update_missing_dois(zot)` | Missing |

---

## File Structure

```
zotero/
├── agents.py              # Tier 1: Everyday interface
├── justfile               # Quick commands
├── _dev/
│   ├── src/
│   │   └── zotero_librarian/
│   │       ├── __init__.py    # Tier 2: Deep primitives
│   │       └── arxiv_tools.py # arXiv integration
│   ├── scripts/
│   │   └── manage.py          # CLI commands
│   └── tests/
└── scripts/
    └── zotero.py              # Legacy Web API (deprecated)
```

---

## Design Principles

1. Tier 1 for 90% of work — simple, composable, agent-friendly
2. Tier 2 for custom workflows — full control, no abstraction
3. No truncation — all methods return complete data
4. Non-destructive by default — preview changes, require confirmation
5. Local API first — Web API only when necessary (external services)
