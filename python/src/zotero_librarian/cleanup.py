"""
Cleanup operations for Zotero library: snapshots, notes, and dangling PDF records.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyzotero import zotero

from .client import _all_items
from .items import trash_item


def trash_snapshots(
    zot: zotero.Zotero,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Find and trash HTML snapshot attachments.

    Targets attachments where contentType == "text/html" or where
    linkMode == "imported_file" and the filename ends with ".html".

    Args:
        zot: Zotero client
        dry_run: When True (default), report matches without trashing anything.

    Returns:
        Dict with:
            - dry_run: bool
            - count: number of snapshots found (or trashed when dry_run=False)
            - items: list of dicts with 'key', 'title', 'filename', 'contentType'
            - results: list of trash operation results (empty when dry_run=True)
    """
    snapshots: list[dict[str, Any]] = []

    for att in _all_items(zot, itemType="attachment"):
        data = att.get("data", {})
        content_type = data.get("contentType", "")
        link_mode = data.get("linkMode", "")
        filename = data.get("filename", "") or ""

        is_html_content_type = content_type == "text/html"
        is_imported_html_file = (
            link_mode == "imported_file" and filename.lower().endswith(".html")
        )

        if is_html_content_type or is_imported_html_file:
            snapshots.append(
                {
                    "key": att["key"],
                    "title": data.get("title", ""),
                    "filename": filename,
                    "contentType": content_type,
                    "linkMode": link_mode,
                }
            )

    results: list[dict[str, Any]] = []
    if not dry_run:
        for snap in snapshots:
            result = trash_item(zot, snap["key"])
            results.append({"key": snap["key"], **result})

    return {
        "dry_run": dry_run,
        "count": len(snapshots),
        "items": snapshots,
        "results": results,
    }


def trash_all_notes(
    zot: zotero.Zotero,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Find and trash all note items (top-level and child notes).

    Args:
        zot: Zotero client
        dry_run: When True (default), report matches without trashing anything.

    Returns:
        Dict with:
            - dry_run: bool
            - count: number of notes found (or trashed when dry_run=False)
            - items: list of dicts with 'key', 'parent_key', 'snippet'
            - results: list of trash operation results (empty when dry_run=True)
    """
    import re

    notes: list[dict[str, Any]] = []

    for note in _all_items(zot, itemType="note"):
        data = note.get("data", {})
        raw = data.get("note", "") or ""
        # Brief plain-text snippet for identification
        snippet = re.sub(r"<[^>]+>", " ", raw)[:120].strip()
        notes.append(
            {
                "key": note["key"],
                "parent_key": data.get("parentItem"),
                "snippet": snippet,
            }
        )

    results: list[dict[str, Any]] = []
    if not dry_run:
        for note_info in notes:
            result = trash_item(zot, note_info["key"])
            results.append({"key": note_info["key"], **result})

    return {
        "dry_run": dry_run,
        "count": len(notes),
        "items": notes,
        "results": results,
    }


def clean_missing_pdfs(
    zot: zotero.Zotero,
    *,
    dry_run: bool = True,
    storage_root: str | None = None,
) -> dict[str, Any]:
    """Find and trash PDF attachment records whose file is missing on disk.

    Checks ~/Zotero/storage/<attachment_key>/<filename> for each PDF attachment.
    If the file does not exist locally, the attachment record is trashed.

    Args:
        zot: Zotero client
        dry_run: When True (default), report matches without trashing anything.
        storage_root: Override for Zotero storage directory.
                      Defaults to ~/Zotero/storage.

    Returns:
        Dict with:
            - dry_run: bool
            - count: number of dangling records found (or trashed when dry_run=False)
            - items: list of dicts with 'key', 'filename', 'expected_path'
            - results: list of trash operation results (empty when dry_run=True)
    """
    if storage_root is None:
        base = Path.home() / "Zotero" / "storage"
    else:
        base = Path(storage_root)

    dangling: list[dict[str, Any]] = []

    for att in _all_items(zot, itemType="attachment"):
        data = att.get("data", {})
        content_type = data.get("contentType", "")
        if content_type != "application/pdf":
            continue

        # Linked attachments live outside ~/Zotero/storage/ intentionally — skip them
        link_mode = data.get("linkMode", "")
        if link_mode in ("linked_file", "linked_url"):
            continue

        filename = data.get("filename", "") or ""
        if not filename:
            continue

        expected_path = base / att["key"] / filename
        if not expected_path.exists():
            dangling.append(
                {
                    "key": att["key"],
                    "filename": filename,
                    "expected_path": str(expected_path),
                }
            )

    results: list[dict[str, Any]] = []
    if not dry_run:
        for record in dangling:
            result = trash_item(zot, record["key"])
            results.append({"key": record["key"], **result})

    return {
        "dry_run": dry_run,
        "count": len(dangling),
        "items": dangling,
        "results": results,
    }
