[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/I2I57UKJ8)

# Zotero Librarian

Tools for managing your Zotero library.

## Quick Start

```bash
# View available commands
just

# Get library overview
just stats

# Identify quality issues
just quality
```

## Philosophy

These tools assist intelligent agents rather than providing simple automation.

### Design Principles

- **Readability**: Well-documented, self-contained Python.
- **Adaptability**: Modular design for easy modification.
- **Safety**: Non-destructive operations that identify issues before fixing.
- **Completeness**: No data truncation; returns full query results.

## Tools

### Library Overview

- `just stats`: Provides item counts, collections, and attachments.
- `just quality`: Lists all quality issues at a glance.

### Issue Detection

- `just find-no-pdf`: Identifies items missing PDF attachments.
- `just find-duplicates`: Lists items with duplicate titles.
- `just find-similar-tags`: Finds similar tags to identify typos or variations.

### Library Browsing

- `just list-collections`: Lists all collections with item counts.
- `just list-tags`: Lists all tags by frequency.

### Fixes

- `just tag-needs-pdf`: Tags all items missing PDFs.

### Python Environment

- `just shell`: Launches a Python REPL with the library loaded.

## Python API

```python
from agents import ZoteroAgent

lib = ZoteroAgent()

# Library overview
stats = lib.library_stats()
issues = lib.find_quality_issues()

# Detect problems
no_pdf = lib.find_items_without_pdf()
duplicates = lib.find_duplicates_by_title()

# Apply fixes with judgment
for item in no_pdf[:10]:
    lib.add_tags(item["key"], ["needs-pdf"])
```

## Requirements

- Zotero 7+ (running)
- Local API enabled: **Edit → Settings → Advanced → "Allow other applications to communicate with Zotero"**

## Installation

```bash
just install # Uses uv
```

## Project Structure

- `agents.py`: Main tool interface.
- `justfile`: Command shortcuts.
- `.venv/`: Python virtual environment.
- `_dev/`: Development source code, tests, and documentation.
