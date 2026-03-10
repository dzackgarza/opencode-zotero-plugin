from __future__ import annotations

"""Note management functions for Zotero library items."""

import re
from typing import Any

from pyzotero import zotero

from .client import _all_items
from .connector import local_write, result_from_exception


def _noop_result(operation: str, note_key: str) -> dict[str, Any]:
    return {
        "success": True,
        "operation": operation,
        "stage": "noop",
        "note_key": note_key,
    }


def _trash_write_result(operation: str, **details: Any) -> dict[str, Any]:
    return local_write(
        "trash_item",
        payload={"item_key": details["note_key"]},
        operation=operation,
    )


def _get_note(zot: zotero.Zotero, note_key: str, *, operation: str) -> dict[str, Any]:
    try:
        note = zot.item(note_key)
    except Exception as exc:
        raise exc
    if note.get("data", {}).get("itemType") != "note":
        raise RuntimeError(f"Item is not a note: {note_key}")
    return note


def update_note(zot: zotero.Zotero, note_key: str, new_content: str) -> dict[str, Any]:
    """Update the content of an existing note."""
    try:
        note = _get_note(zot, note_key, operation="update_note")
    except Exception as exc:
        return result_from_exception("update_note", exc)
    if note.get("data", {}).get("note", "") == new_content:
        return _noop_result("update_note", note_key)
    return local_write(
        "update_note",
        payload={"note_key": note_key, "new_content": new_content},
        operation="update_note",
    )


def delete_note(zot: zotero.Zotero, note_key: str) -> dict[str, Any]:
    """Delete a note from Zotero."""
    try:
        note = _get_note(zot, note_key, operation="delete_note")
    except Exception as exc:
        return result_from_exception("delete_note", exc)
    return _trash_write_result(
        "delete_note",
        note_key=note_key,
        parent_item_key=note.get("data", {}).get("parentItem"),
    )


def get_all_notes(zot: zotero.Zotero) -> list[dict[str, Any]]:
    """Get all notes in the library.

    Fetches all note items from the library, including their content
    and parent item information.

    Args:
        zot: Zotero client

    Returns:
        List of note items with their data.
    """
    return list(_all_items(zot, itemType="note"))


def search_notes(zot: zotero.Zotero, query: str) -> list[dict[str, Any]]:
    """Search note content for text.

    Searches through all notes in the library for notes containing
    the specified query string (case-insensitive).

    Args:
        zot: Zotero client
        query: Text to search for in note content (case-insensitive)

    Returns:
        List of note items where the note content contains the query string.
    """
    results = []
    query_lower = query.lower()

    for note in _all_items(zot, itemType="note"):
        note_content = note.get("data", {}).get("note", "") or ""
        plain_text = re.sub(r"<[^>]+>", " ", note_content)
        if query_lower in plain_text.lower():
            results.append(note)

    return results
