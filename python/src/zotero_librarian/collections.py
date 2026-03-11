from __future__ import annotations

"""Collection management functions for Zotero library."""

from typing import Any

from pyzotero import zotero

from .connector import error_result, local_write, result_from_exception


def _trash_write_result(operation: str, **details: Any) -> dict[str, Any]:
    return local_write(
        "trash_collection",
        payload={"collection_key": details["collection_key"]},
        operation=operation,
    )


def _collection_details(collection: dict[str, Any]) -> dict[str, Any]:
    data = collection.get("data", {})
    return {
        "collection_key": collection["key"],
        "collection_name": data.get("name", ""),
        "parent_key": data.get("parentCollection"),
    }


def _get_collection(zot: zotero.Zotero, collection_key: str) -> dict[str, Any]:
    return zot.collection(collection_key)


def create_collection(zot: zotero.Zotero, name: str, parent_key: str = None) -> dict[str, Any]:
    """Create a new collection."""
    cleaned_name = name.strip()
    if not cleaned_name:
        return error_result(
            "create_collection",
            "input_validation",
            "A non-empty collection name is required.",
            details={"name": name, "parent_key": parent_key},
        )

    if parent_key:
        try:
            _get_collection(zot, parent_key)
        except Exception as exc:
            return result_from_exception("create_collection", exc)

    return local_write(
        "create_collection",
        payload={"name": cleaned_name, "parent_key": parent_key},
        operation="create_collection",
    )


def trash_collection(zot: zotero.Zotero, collection_key: str) -> dict[str, Any]:
    """Move a collection to trash."""
    try:
        collection = _get_collection(zot, collection_key)
    except Exception as exc:
        return result_from_exception("trash_collection", exc)
    return _trash_write_result("trash_collection", **_collection_details(collection))


def rename_collection(zot: zotero.Zotero, collection_key: str, new_name: str) -> dict[str, Any]:
    """Rename a collection."""
    cleaned_name = new_name.strip()
    if not cleaned_name:
        return error_result(
            "rename_collection",
            "input_validation",
            "A non-empty collection name is required.",
            details={"collection_key": collection_key, "new_name": new_name},
        )
    try:
        _get_collection(zot, collection_key)
    except Exception as exc:
        return result_from_exception("rename_collection", exc)
    return local_write(
        "rename_collection",
        payload={"collection_key": collection_key, "new_name": cleaned_name},
        operation="rename_collection",
    )


def merge_collections(zot: zotero.Zotero, source_keys: list[str], target_key: str) -> dict[str, Any]:
    """Merge multiple collections into one."""
    normalized_sources = [key.strip() for key in source_keys if key and key.strip()]
    if not normalized_sources:
        return error_result(
            "merge_collections",
            "input_validation",
            "At least one source collection key is required.",
            details={"source_keys": source_keys, "target_key": target_key},
        )
    try:
        target_collection = _get_collection(zot, target_key)
        source_collections = [_get_collection(zot, source_key) for source_key in normalized_sources]
    except Exception as exc:
        return result_from_exception("merge_collections", exc)
    return local_write(
        "merge_collections",
        payload={"source_keys": normalized_sources, "target_key": target_key},
        operation="merge_collections",
    )


def move_collection(zot: zotero.Zotero, collection_key: str, new_parent_key: str | None) -> dict[str, Any]:
    """Move a collection to a new parent (or make it top-level)."""
    try:
        _get_collection(zot, collection_key)
        if new_parent_key:
            _get_collection(zot, new_parent_key)
    except Exception as exc:
        return result_from_exception("move_collection", exc)
    return local_write(
        "move_collection",
        payload={"collection_key": collection_key, "new_parent_key": new_parent_key},
        operation="move_collection",
    )
