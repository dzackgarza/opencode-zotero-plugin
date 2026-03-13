from __future__ import annotations

"""
Item inspection and write operations for Zotero library items.
"""

from typing import Any
from pyzotero import zotero

import re as _re

from .connector import error_result, local_write, result_from_exception
from .query import get_item, get_attachments

_ITEM_KEY_RE = _re.compile(r"^[A-Z0-9]{8}$")


def _validate_item_key(operation: str, item_key: str) -> dict[str, Any] | None:
    """Return an error_result if item_key is not a valid 8-char alphanumeric Zotero key."""
    if not _ITEM_KEY_RE.match(item_key):
        return error_result(
            operation,
            "key_validation",
            f"Invalid item key: {item_key!r}. Expected 8 uppercase alphanumeric characters.",
            details={"item_key": item_key},
        )
    return None


def _noop_result(operation: str, item_key: str) -> dict[str, Any]:
    return {
        "success": True,
        "operation": operation,
        "stage": "noop",
        "item_key": item_key,
    }


def _merge_details(result: dict[str, Any], **details: Any) -> dict[str, Any]:
    merged = dict(result)
    merged_details = dict(merged.get("details", {}))
    merged_details.update(details)
    merged["details"] = merged_details
    return merged


def _normalized_tags(tags: list[str], *, operation: str) -> tuple[list[str] | None, dict[str, Any] | None]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str):
            return None, error_result(
                operation,
                "input_validation",
                "Tags must be strings.",
                details={"tags": tags},
            )
        cleaned = tag.strip()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    return normalized, None


def attachment_info(zot: zotero.Zotero, item_key: str) -> list[dict]:
    """Get file info for all attachments of an item."""
    attachments = get_attachments(zot, item_key)
    return [
        {
            "key": a["key"],
            "title": a["data"].get("title", ""),
            "contentType": a["data"].get("contentType", ""),
            "filename": a["data"].get("filename", ""),
            "md5": a["data"].get("md5", ""),
        }
        for a in attachments
    ]


def check_item_completeness(
    zot: zotero.Zotero,
    item_key: str,
    required_fields: list[str]
) -> dict[str, Any]:
    """Check if an item has all required fields."""
    item = get_item(zot, item_key)
    missing = [f for f in required_fields if not item["data"].get(f)]
    return {
        "key": item_key,
        "title": item["data"].get("title", ""),
        "complete": len(missing) == 0,
        "missing": missing,
    }


def update_item_fields(zot: zotero.Zotero, item_key: str, fields: dict[str, Any]) -> dict:
    """Update fields on an existing item.

    Args:
        zot: Zotero client
        item_key: Key of item to update
        fields: Dict of field names and values to update

    Returns:
        Response from Zotero API
    """
    if err := _validate_item_key("update_item_fields", item_key):
        return err
    try:
        get_item(zot, item_key)
    except Exception as exc:
        return result_from_exception("update_item_fields", exc)
    if not fields:
        return _noop_result("update_item_fields", item_key)
    return local_write(
        "update_item_fields",
        payload={"item_key": item_key, "fields": fields},
        operation="update_item_fields",
    )


def add_tags_to_item(zot: zotero.Zotero, item_key: str, tags: list[str]) -> dict:
    """Add tags to an item.

    Args:
        zot: Zotero client
        item_key: Key of item to update
        tags: List of tag strings to add

    Returns:
        Response from Zotero API
    """
    try:
        item = get_item(zot, item_key)
    except Exception as exc:
        return result_from_exception("add_tags_to_item", exc)
    normalized_tags, validation_error = _normalized_tags(tags, operation="add_tags_to_item")
    if validation_error:
        return validation_error
    if not normalized_tags:
        return _noop_result("add_tags_to_item", item_key)
    existing_tags = [
        tag.get("tag", "").strip()
        for tag in item.get("data", {}).get("tags", [])
        if tag.get("tag", "").strip()
    ]
    final_tags = existing_tags.copy()
    for tag in normalized_tags:
        if tag not in final_tags:
            final_tags.append(tag)
    if final_tags == existing_tags:
        return _noop_result("add_tags_to_item", item_key)
    return _merge_details(
        local_write(
            "set_item_tags",
            payload={"item_key": item_key, "tags": final_tags},
            operation="add_tags_to_item",
        ),
        item_key=item_key,
        tags=normalized_tags,
    )


def remove_tags_from_item(zot: zotero.Zotero, item_key: str, tags: list[str]) -> dict:
    """Remove tags from an item.

    Args:
        zot: Zotero client
        item_key: Key of item to update
        tags: List of tag strings to remove

    Returns:
        Response from Zotero API
    """
    try:
        item = get_item(zot, item_key)
    except Exception as exc:
        return result_from_exception("remove_tags_from_item", exc)
    normalized_tags, validation_error = _normalized_tags(tags, operation="remove_tags_from_item")
    if validation_error:
        return validation_error
    if not normalized_tags:
        return _noop_result("remove_tags_from_item", item_key)
    existing_tags = [
        tag.get("tag", "").strip()
        for tag in item.get("data", {}).get("tags", [])
        if tag.get("tag", "").strip()
    ]
    final_tags = [tag for tag in existing_tags if tag not in set(normalized_tags)]
    if final_tags == existing_tags:
        return _noop_result("remove_tags_from_item", item_key)
    return _merge_details(
        local_write(
            "set_item_tags",
            payload={"item_key": item_key, "tags": final_tags},
            operation="remove_tags_from_item",
        ),
        item_key=item_key,
        tags=normalized_tags,
    )


def move_item_to_collection(zot: zotero.Zotero, item_key: str, collection_key: str) -> dict:
    """Move an item to a collection.

    Args:
        zot: Zotero client
        item_key: Key of item to move
        collection_key: Key of target collection

    Returns:
        Response from Zotero API
    """
    try:
        get_item(zot, item_key)
        zot.collection(collection_key)
    except Exception as exc:
        return result_from_exception("move_item_to_collection", exc)
    return _merge_details(
        local_write(
            "set_item_collections",
            payload={"item_key": item_key, "collection_keys": [collection_key]},
            operation="move_item_to_collection",
        ),
        item_key=item_key,
        collection_key=collection_key,
    )


def add_item_to_collection(zot: zotero.Zotero, item_key: str, collection_key: str) -> dict:
    """Add an item to a collection (keeps existing collections).

    Args:
        zot: Zotero client
        item_key: Key of item to add
        collection_key: Key of target collection

    Returns:
        Response from Zotero API
    """
    try:
        item = get_item(zot, item_key)
        zot.collection(collection_key)
    except Exception as exc:
        return result_from_exception("add_item_to_collection", exc)
    existing_collections = list(item.get("data", {}).get("collections", []))
    if collection_key in existing_collections:
        return _noop_result("add_item_to_collection", item_key)
    return _merge_details(
        local_write(
            "set_item_collections",
            payload={"item_key": item_key, "collection_keys": existing_collections + [collection_key]},
            operation="add_item_to_collection",
        ),
        item_key=item_key,
        collection_key=collection_key,
    )


def remove_item_from_collection(zot: zotero.Zotero, item_key: str, collection_key: str) -> dict:
    """Remove an item from a collection.

    Args:
        zot: Zotero client
        item_key: Key of item to update
        collection_key: Key of collection to remove from

    Returns:
        Response from Zotero API
    """
    try:
        item = get_item(zot, item_key)
    except Exception as exc:
        return result_from_exception("remove_item_from_collection", exc)
    existing_collections = list(item.get("data", {}).get("collections", []))
    final_collections = [key for key in existing_collections if key != collection_key]
    if final_collections == existing_collections:
        return _noop_result("remove_item_from_collection", item_key)
    return _merge_details(
        local_write(
            "set_item_collections",
            payload={"item_key": item_key, "collection_keys": final_collections},
            operation="remove_item_from_collection",
        ),
        item_key=item_key,
        collection_key=collection_key,
    )


def attach_pdf(zot: zotero.Zotero, parent_item_key: str, pdf_path: str, title: str = None) -> dict:
    """Attach a PDF file to an item.

    Args:
        zot: Zotero client
        parent_item_key: Key of parent item
        pdf_path: Path to PDF file
        title: Optional title for attachment (defaults to PDF filename)

    Returns:
        Response from Zotero API with new attachment key
    """
    from pathlib import Path

    from .attachments import attach_file_to_item

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return error_result(
            "attach_pdf",
            "input_validation",
            f"PDF not found: {pdf_path}",
            details={"parent_item_key": parent_item_key, "pdf_path": pdf_path},
        )

    if title is None:
        title = pdf_file.name
    return attach_file_to_item(
        zot,
        parent_item_key,
        pdf_path,
        title=title,
        operation="attach_pdf",
    )


def attach_url(zot: zotero.Zotero, parent_item_key: str, url: str, title: str = None) -> dict:
    """Attach a URL/link to an item.

    Args:
        zot: Zotero client
        parent_item_key: Key of parent item
        url: URL to attach
        title: Optional title for attachment

    Returns:
        Response from Zotero API
    """
    if title is None:
        title = url
    try:
        get_item(zot, parent_item_key)
    except Exception as exc:
        return result_from_exception("attach_url", exc)
    return _merge_details(
        local_write(
            "attach_url",
            payload={"parent_item_key": parent_item_key, "url": url, "title": title},
            operation="attach_url",
        ),
        parent_item_key=parent_item_key,
        title=title,
        url=url,
    )


def attach_note(zot: zotero.Zotero, parent_item_key: str, note_text: str, title: str = None) -> dict:
    """Add a note to an item.

    Args:
        zot: Zotero client
        parent_item_key: Key of parent item
        note_text: Note content (supports HTML)
        title: Optional title for note

    Returns:
        Response from Zotero API
    """
    try:
        get_item(zot, parent_item_key)
    except Exception as exc:
        return result_from_exception("attach_note", exc)
    return _merge_details(
        local_write(
            "attach_note",
            payload={
                "parent_item_key": parent_item_key,
                "note_text": note_text,
                "title": title,
            },
            operation="attach_note",
        ),
        parent_item_key=parent_item_key,
        title=title,
        note_length=len(note_text),
    )


def add_citation_relation(zot: zotero.Zotero, item_key: str, relation_type: str, target_uri: str) -> dict:
    """Add a citation relation (cites or citedBy).

    Args:
        zot: Zotero client
        item_key: Key of item to update
        relation_type: "cites" or "citedBy"
        target_uri: URI of related item (DOI, Zotero URI, etc.)

    Returns:
        Response from Zotero API
    """
    try:
        item = get_item(zot, item_key)
    except Exception as exc:
        return result_from_exception("add_citation_relation", exc)
    relations = dict(item.get("data", {}).get("relations", {}))
    current_values = relations.get(relation_type, [])
    if isinstance(current_values, str):
        current_values = [current_values]
    if target_uri in current_values:
        return _noop_result("add_citation_relation", item_key)
    relations[relation_type] = current_values + [target_uri]
    return _merge_details(
        local_write(
            "update_item_fields",
            payload={"item_key": item_key, "fields": {"relations": relations}},
            operation="add_citation_relation",
        ),
        item_key=item_key,
        relation_type=relation_type,
        target_uri=target_uri,
    )


def trash_item(zot: zotero.Zotero, item_key: str) -> dict:
    """Move an item to trash.

    Args:
        zot: Zotero client
        item_key: Key of item to trash

    Returns:
        Response from Zotero API

    Note: This moves the item to trash. To permanently delete,
    the user must manually empty trash in the Zotero UI.
    """
    try:
        get_item(zot, item_key)
    except Exception as exc:
        return result_from_exception("trash_item", exc)
    return local_write(
        "trash_item",
        payload={"item_key": item_key},
        operation="trash_item",
    )


def convert_item_type(zot: zotero.Zotero, item_key: str, new_type: str) -> dict:
    """Convert an item to a different item type.

    Changes the item type while preserving all common fields between
    the old and new types. Some fields may be lost if not applicable
    to the new type.

    Args:
        zot: Zotero client
        item_key: Key of the item to convert
        new_type: New item type (e.g., "bookSection", "journalArticle")

    Returns:
        Dict with "success" (bool) and either "key" (str) on success or "error" (str) on failure
    """
    # Fields common to most item types
    common_fields = [
        "title",
        "creators",
        "date",
        "DOI",
        "ISBN",
        "ISSN",
        "url",
        "abstractNote",
        "tags",
        "collections",
        "relations",
        "extra",
        "language",
        "rights",
        "accessDate",
        "libraryCatalog",
        "callNumber",
        "archive",
        "archiveLocation",
        "notes",
        "attachments",
    ]

    try:
        # Get the item
        item = zot.item(item_key)
        if not item:
            return {"success": False, "error": f"Item not found: {item_key}"}

        # Create new item data with new type
        old_data = item["data"]
        new_data = {"itemType": new_type}

        # Copy common fields
        for field in common_fields:
            if field in old_data:
                new_data[field] = old_data[field]

        # Type-specific field mappings
        field_mappings = {
            # From journalArticle
            ("journalArticle", "bookSection"): {
                "publicationTitle": "bookTitle",
                "journalAbbreviation": "bookAbbreviation",
            },
            # From book to bookSection
            ("book", "bookSection"): {
                "publicationTitle": "bookTitle",
                "place": "place",
                "publisher": "publisher",
                "edition": "edition",
                "series": "series",
                "seriesNumber": "seriesNumber",
            },
            # From conferencePaper to journalArticle
            ("conferencePaper", "journalArticle"): {
                "proceedingsTitle": "publicationTitle",
                "conferenceName": "extra",
            },
        }

        # Apply field mappings based on old and new type
        old_type = old_data.get("itemType", "")
        mapping_key = (old_type, new_type)
        if mapping_key in field_mappings:
            for old_field, new_field in field_mappings[mapping_key].items():
                if old_field in old_data:
                    if new_field == "extra":
                        # Append to extra field
                        existing_extra = new_data.get("extra", "")
                        if existing_extra:
                            new_data["extra"] = f"{existing_extra}\n{old_field}: {old_data[old_field]}"
                        else:
                            new_data["extra"] = f"{old_field}: {old_data[old_field]}"
                    else:
                        new_data[new_field] = old_data[old_field]

        # Update the item with new type
        return _merge_details(
            local_write(
                "replace_item_json",
                payload={"item_key": item_key, "item_json": new_data},
                operation="convert_item_type",
            ),
            item_key=item_key,
            new_type=new_type,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def transfer_relations(zot: zotero.Zotero, from_key: str, to_key: str) -> dict:
    """Copy all relations from one item to another.

    Transfers all citation relations (cites, citedBy) and other relations
    from the source item to the target item.

    Args:
        zot: Zotero client
        from_key: Key of the source item (relations are copied from here)
        to_key: Key of the target item (relations are copied to here)

    Returns:
        Dict with "success" (bool), "transferred" (int), and either "message" (str) or "error" (str)
    """
    try:
        # Get both items
        from_item = zot.item(from_key)
        to_item = zot.item(to_key)

        if not from_item:
            return {"success": False, "error": f"Source item not found: {from_key}"}
        if not to_item:
            return {"success": False, "error": f"Target item not found: {to_key}"}

        # Get relations from source
        from_relations = from_item["data"].get("relations", {})
        to_relations = to_item["data"].get("relations", {})

        transferred = 0

        # Copy each relation type
        for relation_type, relation_values in from_relations.items():
            if isinstance(relation_values, str):
                relation_values = [relation_values]

            if relation_type not in to_relations:
                to_relations[relation_type] = []
            elif isinstance(to_relations[relation_type], str):
                to_relations[relation_type] = [to_relations[relation_type]]

            # Add values that don't already exist
            for value in relation_values:
                if value not in to_relations[relation_type]:
                    to_relations[relation_type].append(value)
                    transferred += 1

        return _merge_details(
            local_write(
                "update_item_fields",
                payload={"item_key": to_key, "fields": {"relations": to_relations}},
                operation="transfer_relations",
            ),
            from_key=from_key,
            to_key=to_key,
            transferred=transferred,
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def copy_item(zot: zotero.Zotero, item_key: str) -> dict:
    """Duplicate an item with all its attachments and notes.

    Creates a complete copy of an item including all child items
    (attachments, notes) and relations.

    Args:
        zot: Zotero client
        item_key: Key of the item to copy

    Returns:
        Dict with "success" (bool), "new_key" (str), and either "message" (str) or "error" (str)
    """
    try:
        get_item(zot, item_key)
    except Exception as exc:
        return result_from_exception("copy_item", exc)
    return _merge_details(
        local_write(
            "copy_item",
            payload={"item_key": item_key},
            operation="copy_item",
        ),
        item_key=item_key,
    )


def merge_items(zot: zotero.Zotero, source_key: str, target_key: str) -> dict:
    """Merge source item into target item.

    Transfers all relations, attachments, notes, and tags from the source
    item to the target item, then moves the source to trash.

    Args:
        zot: Zotero client
        source_key: Key of the source item (will be merged and deleted)
        target_key: Key of the target item (will receive all data)

    Returns:
        Dict with "success" (bool), "transferred" (dict with counts), and either "message" (str) or "error" (str)
    """
    try:
        get_item(zot, source_key)
        get_item(zot, target_key)
    except Exception as exc:
        return result_from_exception("merge_items", exc)
    return _merge_details(
        local_write(
            "merge_items",
            payload={"source_key": source_key, "target_key": target_key},
            operation="merge_items",
        ),
        source_key=source_key,
        target_key=target_key,
    )
