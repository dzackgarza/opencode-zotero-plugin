from __future__ import annotations

"""Sync status and conflict resolution helpers for Zotero library."""

from typing import Any

from pyzotero import zotero

from .client import _all_items
from .connector import error_result, result_from_exception


def _sync_headers(zot: zotero.Zotero) -> dict[str, str]:
    zot.items(limit=1)
    headers = getattr(zot.request, "headers", {})
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _sync_error_result(operation: str, exc: Exception) -> dict[str, Any]:
    result = result_from_exception(operation, exc)
    result.update(
        {
            "synced": False,
            "last_sync_version": None,
            "total_items": 0,
            "conflicts": 0,
        }
    )
    return result


def get_sync_status(zot: zotero.Zotero) -> dict[str, Any]:
    """Check sync status of the library."""
    try:
        headers = _sync_headers(zot)
    except Exception as exc:
        return _sync_error_result("get_sync_status", exc)
    return {
        "success": True,
        "synced": True,
        "last_sync_version": headers.get("last-modified-version") or None,
        "total_items": int(headers.get("total-results", "0")),
        "conflicts": 0,
        "error": None,
    }


def get_last_sync(zot: zotero.Zotero) -> dict[str, Any]:
    """Get last sync timestamp."""
    try:
        headers = _sync_headers(zot)
    except Exception as exc:
        result = result_from_exception("get_last_sync", exc)
        result.update({"version": None, "timestamp": None})
        return result
    return {
        "success": True,
        "version": headers.get("last-modified-version") or None,
        "timestamp": None,
    }


def check_conflicts(zot: zotero.Zotero) -> list[dict[str, Any]]:
    """Find sync conflicts in the library."""
    conflicts: list[dict[str, Any]] = []
    for item in _all_items(zot):
        version = item.get("version", 0)
        if version == 0:
            conflicts.append(
                {
                    "key": item.get("key", ""),
                    "title": item.get("data", {}).get("title", ""),
                    "conflict_type": "version_zero",
                    "versions": [version],
                }
            )
    return conflicts


def resolve_conflict(zot: zotero.Zotero, item_key: str, keep_version: str = "local") -> dict[str, Any]:
    """Resolve a sync conflict for an item."""
    if keep_version not in {"local", "remote"}:
        return error_result(
            "resolve_conflict",
            "input_validation",
            f"Invalid keep_version: {keep_version}",
            details={"item_key": item_key, "keep_version": keep_version},
        )
    try:
        item = zot.item(item_key)
    except Exception as exc:
        return result_from_exception("resolve_conflict", exc)
    if keep_version == "remote":
        return error_result(
            "resolve_conflict",
            "remote_resolution_unavailable",
            "Remote conflict resolution is not available through the local Zotero integration.",
            details={"item_key": item_key, "keep_version": keep_version},
        )
    return error_result(
        "resolve_conflict",
        "existing_item_write_surface",
        "Local conflict resolution writes are not wired through the Zotero connector yet.",
        details={
            "item_key": item_key,
            "keep_version": keep_version,
            "item_type": item.get("data", {}).get("itemType"),
        },
    )
