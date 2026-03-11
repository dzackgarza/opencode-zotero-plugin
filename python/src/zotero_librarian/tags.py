from __future__ import annotations

"""Tag management functions for Zotero library."""

from typing import Any

from pyzotero import zotero

from .client import _all_items
from .connector import (
    ConnectorWriteError,
    error_result,
    local_write,
    require_local_plugin_version,
    result_from_exception,
)
from .settings import plugin_feature_minimum_version


DELETE_TAG_MIN_PLUGIN_VERSION = plugin_feature_minimum_version("delete_tag")


def _noop_result(operation: str, **details: Any) -> dict[str, Any]:
    return {
        "success": True,
        "operation": operation,
        "stage": "noop",
        **details,
    }


def _normalized_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = tag.strip()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized


def _matching_item_keys(zot: zotero.Zotero, tags: list[str]) -> list[str]:
    tag_set = set(tags)
    matched_keys: list[str] = []
    for item in _all_items(zot):
        current_tags = {
            tag.get("tag", "").strip()
            for tag in item.get("data", {}).get("tags", [])
            if tag.get("tag", "").strip()
        }
        if current_tags & tag_set:
            matched_keys.append(item["key"])
    return matched_keys


def _global_tag_names(zot: zotero.Zotero) -> set[str]:
    tags = zot.tags()
    names: set[str] = set()
    for tag in tags:
        if isinstance(tag, str):
            cleaned = tag.strip()
        else:
            cleaned = str(tag.get("tag", "")).strip()
        if cleaned:
            names.add(cleaned)
    return names


def _merge_details(result: dict[str, Any], **details: Any) -> dict[str, Any]:
    merged = dict(result)
    merged_details = dict(merged.get("details", {}))
    merged_details.update(details)
    merged["details"] = merged_details
    return merged


def merge_tags(zot: zotero.Zotero, source_tags: list[str], target_tag: str) -> dict[str, Any]:
    """Merge multiple tags into one across all items."""
    normalized_sources = _normalized_tags(source_tags)
    cleaned_target = target_tag.strip()
    if not normalized_sources:
        return error_result(
            "merge_tags",
            "input_validation",
            "At least one source tag is required.",
            details={"source_tags": source_tags, "target_tag": target_tag},
        )
    if not cleaned_target:
        return error_result(
            "merge_tags",
            "input_validation",
            "A non-empty target tag is required.",
            details={"source_tags": normalized_sources, "target_tag": target_tag},
        )
    try:
        matched_item_keys = _matching_item_keys(zot, normalized_sources)
    except Exception as exc:
        return result_from_exception("merge_tags", exc)
    if not matched_item_keys:
        return _noop_result(
            "merge_tags",
            updated_items=0,
            source_tags=normalized_sources,
            target_tag=cleaned_target,
        )
    return _merge_details(
        local_write(
            "merge_tags",
            payload={"source_tags": normalized_sources, "target_tag": cleaned_target},
            operation="merge_tags",
        ),
        source_tags=normalized_sources,
        target_tag=cleaned_target,
        matched_item_count=len(matched_item_keys),
        matched_item_keys=matched_item_keys[:25],
    )


def rename_tag(zot: zotero.Zotero, old_name: str, new_name: str) -> dict[str, Any]:
    """Rename a tag across all items."""
    cleaned_old_name = old_name.strip()
    cleaned_new_name = new_name.strip()
    if not cleaned_old_name:
        return error_result(
            "rename_tag",
            "input_validation",
            "A non-empty old tag name is required.",
            details={"old_name": old_name, "new_name": new_name},
        )
    if not cleaned_new_name:
        return error_result(
            "rename_tag",
            "input_validation",
            "A non-empty new tag name is required.",
            details={"old_name": cleaned_old_name, "new_name": new_name},
        )
    try:
        matched_item_keys = _matching_item_keys(zot, [cleaned_old_name])
    except Exception as exc:
        return result_from_exception("rename_tag", exc)
    if not matched_item_keys:
        return _noop_result(
            "rename_tag",
            updated_items=0,
            old_name=cleaned_old_name,
            new_name=cleaned_new_name,
        )
    return _merge_details(
        local_write(
            "rename_tag",
            payload={"old_name": cleaned_old_name, "new_name": cleaned_new_name},
            operation="rename_tag",
        ),
        old_name=cleaned_old_name,
        new_name=cleaned_new_name,
        matched_item_count=len(matched_item_keys),
        matched_item_keys=matched_item_keys[:25],
    )


def delete_tag(zot: zotero.Zotero, tag_name: str) -> dict[str, Any]:
    """Remove a tag from all items."""
    cleaned_tag_name = tag_name.strip()
    if not cleaned_tag_name:
        return error_result(
            "delete_tag",
            "input_validation",
            "A non-empty tag name is required.",
            details={"tag_name": tag_name},
        )
    try:
        matched_item_keys = _matching_item_keys(zot, [cleaned_tag_name])
    except Exception as exc:
        return result_from_exception("delete_tag", exc)
    if not matched_item_keys:
        return _noop_result(
            "delete_tag",
            updated_items=0,
            tag_name=cleaned_tag_name,
        )
    try:
        require_local_plugin_version(
            DELETE_TAG_MIN_PLUGIN_VERSION,
            operation="delete_tag",
        )
    except ConnectorWriteError as exc:
        return exc.to_dict()

    return _merge_details(
        local_write(
            "delete_tag",
            payload={"tag_name": cleaned_tag_name},
            operation="delete_tag",
        ),
        tag_name=cleaned_tag_name,
        matched_item_count=len(matched_item_keys),
        matched_item_keys=matched_item_keys[:25],
    )


def get_unused_tags(zot: zotero.Zotero) -> dict[str, Any]:
    """List tags not used by any item."""
    try:
        global_tags = _global_tag_names(zot)
        used_tags = {
            tag.get("tag", "").strip()
            for item in _all_items(zot)
            for tag in item.get("data", {}).get("tags", [])
            if tag.get("tag", "").strip()
        }
    except Exception as exc:
        return result_from_exception("get_unused_tags", exc)
    return {"success": True, "unused_tags": sorted(global_tags - used_tags)}


def delete_unused_tags(zot: zotero.Zotero) -> dict[str, Any]:
    """Remove all unused tags from the library."""
    unused_result = get_unused_tags(zot)
    if not unused_result["success"]:
        return unused_result
    unused_tags = unused_result["unused_tags"]
    if not unused_tags:
        return _noop_result("delete_unused_tags", deleted_count=0, unused_tag_count=0)
    return _merge_details(
        local_write(
            "delete_unused_tags",
            payload={},
            operation="delete_unused_tags",
        ),
        unused_tag_count=len(unused_tags),
        unused_tags=unused_tags[:25],
    )
