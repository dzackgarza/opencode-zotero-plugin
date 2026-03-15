"""
Zotero Librarian

Composable tools for Zotero library management via the local API.
Requires Zotero 7+ running with local API enabled.

Modules:
    client       — get_zotero(), pagination helpers
    query        — read-only queries and searches
    items        — CRUD on items, tags, collections, attachments
    attachments  — file upload/download/extract
    notes        — note CRUD
    collections  — collection CRUD
    tags         — tag management
    batch        — bulk operations
    export       — JSON/CSV/BibTeX export
    import_      — DOI/ISBN/arXiv/BibTeX import
    stats        — library statistics
    sync         — sync status
    duplicates   — duplicate detection
    validation   — DOI/ISBN/ISSN validators
    arxiv        — arXiv search and download (optional)
    _dispatch    — JSON-in/JSON-out CLI dispatcher
    _cli         — Typer CLI entry point (zotero-lib)
"""

from .client import get_zotero

__version__ = "0.2.0"
