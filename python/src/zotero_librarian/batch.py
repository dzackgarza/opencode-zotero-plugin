from __future__ import annotations

"""
Batch operations for applying changes to multiple Zotero library items.
"""

from typing import Any
from pyzotero import zotero

from .items import (
    update_item_fields,
    add_tags_to_item,
    remove_tags_from_item,
    move_item_to_collection,
    delete_item,
)


def _record_batch_result(result: dict[str, list[str]], item_key: str, operation_result: dict[str, Any]) -> None:
    if operation_result.get("success", False):
        result["success"].append(item_key)
        return
    result["failed"].append(item_key)


def batch_update_items(
    zot: zotero.Zotero,
    item_keys: list[str],
    fields: dict[str, Any]
) -> dict[str, list[str]]:
    """Update fields on multiple items.

    Args:
        zot: Zotero client
        item_keys: List of item keys to update
        fields: Dict of field names and values to update on all items

    Returns:
        Dict with "success" and "failed" lists of item keys
    """
    result = {"success": [], "failed": []}
    for item_key in item_keys:
        try:
            _record_batch_result(result, item_key, update_item_fields(zot, item_key, fields))
        except Exception:
            result["failed"].append(item_key)
    return result


def batch_add_tags(
    zot: zotero.Zotero,
    item_keys: list[str],
    tags: list[str]
) -> dict[str, list[str]]:
    """Add tags to multiple items.

    Args:
        zot: Zotero client
        item_keys: List of item keys to update
        tags: List of tag strings to add to all items

    Returns:
        Dict with "success" and "failed" lists of item keys
    """
    result = {"success": [], "failed": []}
    for item_key in item_keys:
        try:
            _record_batch_result(result, item_key, add_tags_to_item(zot, item_key, tags))
        except Exception:
            result["failed"].append(item_key)
    return result


def batch_remove_tags(
    zot: zotero.Zotero,
    item_keys: list[str],
    tags: list[str]
) -> dict[str, list[str]]:
    """Remove tags from multiple items.

    Args:
        zot: Zotero client
        item_keys: List of item keys to update
        tags: List of tag strings to remove from all items

    Returns:
        Dict with "success" and "failed" lists of item keys
    """
    result = {"success": [], "failed": []}
    for item_key in item_keys:
        try:
            _record_batch_result(result, item_key, remove_tags_from_item(zot, item_key, tags))
        except Exception:
            result["failed"].append(item_key)
    return result


def batch_move_to_collection(
    zot: zotero.Zotero,
    item_keys: list[str],
    collection_key: str
) -> dict[str, list[str]]:
    """Move multiple items to a collection.

    Args:
        zot: Zotero client
        item_keys: List of item keys to move
        collection_key: Key of target collection

    Returns:
        Dict with "success" and "failed" lists of item keys
    """
    result = {"success": [], "failed": []}
    for item_key in item_keys:
        try:
            _record_batch_result(result, item_key, move_item_to_collection(zot, item_key, collection_key))
        except Exception:
            result["failed"].append(item_key)
    return result


def batch_delete_items(
    zot: zotero.Zotero,
    item_keys: list[str]
) -> dict[str, list[str]]:
    """Move multiple items to trash.

    Args:
        zot: Zotero client
        item_keys: List of item keys to delete

    Returns:
        Dict with "success" and "failed" lists of item keys

    Note: This moves items to trash. To permanently delete,
    the user must manually empty trash in the Zotero UI.
    """
    result = {"success": [], "failed": []}
    for item_key in item_keys:
        try:
            _record_batch_result(result, item_key, delete_item(zot, item_key))
        except Exception:
            result["failed"].append(item_key)
    return result
