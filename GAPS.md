# GAPS.md — Missing Functionality

Tools that have **no equivalent** in the Local API (`_dev/`).

---

## Legacy Web API Gaps

Features from `scripts/zotero.py` (Web API) missing from Local API.

### `add-doi`, `add-isbn`, `add-pmid`, `batch-add`

**What exists:** —

**What's missing:** Add items by DOI, ISBN, or PubMed ID using Zotero's translation server or external APIs.

---

### `find-dois`

**What exists:** —

**What's missing:** Scan library for items missing DOIs, query CrossRef by title/author/year, add matching DOIs.

---

### `fetch-pdfs`

**What exists:** —

**What's missing:** Fetch open-access PDFs from Unpaywall, Semantic Scholar, or DOI content negotiation and attach to items.

---

### `export`

**What exists:** —

**What's missing:** Export library or collection as BibTeX, RIS, or CSL-JSON.

---

### `crossref`

**What exists:** —

**What's missing:** Extract `Author (Year)` citations from text file and match against library.

---

## Analysis Utilities

### `analysis.find_notes`

**What exists:** `items_with_notes()`, `get_notes()`, `search_notes()`

**What's missing:** BibTeX citation key extraction from Extra field, HTML stripping from note content, grouped reporting by parent item.

---

### `analysis.find_duplicate_titles` (fuzzy)

**What exists:** `find_duplicates_by_title()` — exact string match only

**What's missing:** Fuzzy matching using `rapidfuzz` for near-duplicate detection (≥95% similarity).

---

### `core.lookup`

**What exists:** —

**What's missing:** Bridge BibTeX citation keys ↔ Zotero internal keys via Better BibTeX JSON-RPC.

---

## Cleanup Utilities

### `cleanup.delete_snapshots`

**What exists:** —

**What's missing:** Purge HTML snapshot attachments (web page captures) via Web API.

---

### `cleanup.delete_all_notes`

**What exists:** —

**What's missing:** Mass-delete all items of type `note` via Web API.

---

### `cleanup.clean_missing_pdfs`

**What exists:** —

**What's missing:** Remove attachment records where PDF file is missing from `~/Zotero/storage/{attachment_key}/`.

---

## PDF Management & Extraction

### `pdf_management.pdf_status`

**What exists:** —

**What's missing:** Aggregate library statistics (PDF coverage, item types, attachment counts).

---

### `pdf_management.rename_pdf_attachments`

**What exists:** —

**What's missing:** Standardize PDF filenames to match parent item titles.

---

### `pdf_management.extract_and_attach_mineru`

**What exists:** —

**What's missing:** AI-powered PDF → Markdown extraction via MinerU, attach `.md` and `.json` outputs.

---

### `pdf_management.pdf_processor`

**What exists:** `extract_text_from_pdf()` — extracts text but doesn't attach

**What's missing:** PDF text extraction using `pdftotext`, attach `.txt` file back to item.

---

## Lifecycle & Offline Pipelines

### `scripts.offline_pipeline`

**What exists:** —

**What's missing:** Orchestrate Zotero → Fulltext → Embedding lifecycle with state tracking.

---

### `scripts.update_missing_dois`

**What exists:** —

**What's missing:** Recover missing DOIs for items tagged "⛔ No DOI found" via CrossRef/OpenAlex.

---

### `scripts.canonical_db_query`

**What exists:** —

**What's missing:** ChromaDB vector database queries (ID lookup, semantic similarity).

---

## Summary

| Category | ❌ Missing | ⚠️ Partial | Total |
|----------|-----------|-----------|-------|
| Legacy Web API | 5 | 0 | 5 |
| Analysis Utilities | 1 | 2 | 3 |
| Cleanup Utilities | 3 | 0 | 3 |
| PDF Management | 4 | 0 | 4 |
| Lifecycle Pipelines | 3 | 0 | 3 |
| **Total** | **16** | **2** | **18** |
