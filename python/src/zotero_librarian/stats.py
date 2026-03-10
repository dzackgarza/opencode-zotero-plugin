"""
Library statistics functions for Zotero.
"""

from typing import Any
from pyzotero import zotero

from .client import _all_items
from .query import all_tags


def items_per_type(zot: zotero.Zotero) -> dict[str, int]:
    """Count items by type.

    Returns a dictionary mapping item types to their counts.

    Args:
        zot: Zotero client

    Returns:
        Dict mapping item type names to counts, e.g., {"journalArticle": 42, "book": 15}
    """
    from collections import Counter

    type_counts: Counter = Counter()
    for item in _all_items(zot):
        item_type = item["data"].get("itemType", "unknown")
        type_counts[item_type] += 1

    return dict(type_counts)


def items_per_collection(zot: zotero.Zotero) -> dict[str, int]:
    """Count items per collection.

    Returns a dictionary mapping collection keys to their item counts.

    Args:
        zot: Zotero client

    Returns:
        Dict mapping collection keys to item counts
    """
    collections = zot.collections()
    result = {}
    for coll in collections:
        items = zot.collection_items(coll["key"])
        result[coll["key"]] = len(items)
    return result


def items_per_year(zot: zotero.Zotero) -> dict[str, int]:
    """Count items by year.

    Returns a dictionary mapping years to their item counts.
    Items without a valid year are grouped under "unknown".

    Args:
        zot: Zotero client

    Returns:
        Dict mapping year strings to counts, e.g., {"2024": 50, "2023": 35, "unknown": 10}
    """
    from collections import Counter

    year_counts: Counter = Counter()
    for item in _all_items(zot):
        date = item["data"].get("date", "") or ""
        if len(date) >= 4 and date[:4].isdigit():
            year_counts[date[:4]] += 1
        else:
            year_counts["unknown"] += 1

    return dict(year_counts)


def tag_cloud(zot: zotero.Zotero) -> dict[str, int]:
    """Get tag frequency for visualization.

    Returns all tags with their usage counts, suitable for creating
    tag clouds or visualizations.

    Args:
        zot: Zotero client

    Returns:
        Dict mapping tag names to usage counts, sorted by frequency (descending)
    """
    # all_tags already returns frequency counts
    tags = all_tags(zot)
    # Sort by frequency (descending)
    return dict(sorted(tags.items(), key=lambda x: x[1], reverse=True))


def library_summary(zot: zotero.Zotero) -> dict[str, Any]:
    """Get overall library statistics.

    Returns a comprehensive summary of the library including item counts,
    collection info, tag stats, and more.

    Args:
        zot: Zotero client

    Returns:
        Dict with library statistics including:
        - total_items: Total number of items
        - item_types: Count by item type
        - collections: Number of collections
        - tags: Number of unique tags
        - years: Year range (earliest, latest)
        - attachments: Number of attachments
        - notes: Number of notes
    """
    items = list(_all_items(zot))
    item_types = items_per_type(zot)
    collections = zot.collections()
    tags = all_tags(zot)

    # Find year range
    years = []
    for item in items:
        date = item["data"].get("date", "") or ""
        if len(date) >= 4 and date[:4].isdigit():
            years.append(int(date[:4]))

    # Count attachments and notes
    attachments = sum(1 for _ in _all_items(zot, itemType="attachment"))
    notes = sum(1 for _ in _all_items(zot, itemType="note"))

    return {
        "total_items": len(items),
        "item_types": item_types,
        "collections": len(collections),
        "tags": len(tags),
        "years": {
            "earliest": min(years) if years else None,
            "latest": max(years) if years else None,
        },
        "attachments": attachments,
        "notes": notes,
    }


def pdf_status(zot: zotero.Zotero) -> dict[str, Any]:
    """Get a PDF coverage aggregate report for the library.

    Iterates over all top-level items (non-attachment, non-note) and checks
    whether each has at least one PDF child attachment.

    Returns:
        Dict with:
            - total_items: total number of top-level content items
            - items_with_pdf: count of items that have at least one PDF attachment
            - items_without_pdf: count of items without any PDF attachment
            - pdf_coverage_pct: percentage of items with PDFs (0–100, rounded to 1 dp)
            - items_by_type: dict mapping itemType to count (top-level items only)
            - total_attachments: total number of attachment items
            - pdf_attachment_count: number of PDF attachments (contentType=application/pdf)
    """
    from collections import Counter

    # Use _get_library_with_children for efficient one-pass collection
    from .client import _get_library_with_children

    all_with_children = _get_library_with_children(zot)

    type_counts: Counter = Counter()
    total_items = 0
    items_with_pdf = 0
    items_without_pdf = 0

    for item in all_with_children:
        item_type = item["data"].get("itemType", "unknown")
        if item_type in {"attachment", "note"}:
            continue
        total_items += 1
        type_counts[item_type] += 1

        has_pdf = any(
            c["data"].get("itemType") == "attachment"
            and c["data"].get("contentType") == "application/pdf"
            for c in item.get("_children", [])
        )
        if has_pdf:
            items_with_pdf += 1
        else:
            items_without_pdf += 1

    pdf_coverage_pct = (
        round(items_with_pdf / total_items * 100, 1) if total_items > 0 else 0.0
    )

    # Attachment totals
    total_attachments = sum(1 for _ in _all_items(zot, itemType="attachment"))
    pdf_attachment_count = sum(
        1
        for att in _all_items(zot, itemType="attachment")
        if att["data"].get("contentType") == "application/pdf"
    )

    return {
        "total_items": total_items,
        "items_with_pdf": items_with_pdf,
        "items_without_pdf": items_without_pdf,
        "pdf_coverage_pct": pdf_coverage_pct,
        "items_by_type": dict(type_counts),
        "total_attachments": total_attachments,
        "pdf_attachment_count": pdf_attachment_count,
    }


def attachment_summary(zot: zotero.Zotero) -> dict[str, Any]:
    """Get attachment types and sizes summary.

    Returns statistics about attachments in the library including
    content types, file sizes, and link modes.

    Args:
        zot: Zotero client

    Returns:
        Dict with attachment statistics including:
        - total: Total number of attachments
        - by_content_type: Count by content type (PDF, HTML, etc.)
        - by_link_mode: Count by link mode (imported_file, linked_url, etc.)
        - total_size: Total file size in bytes (if available)
        - with_file: Number of attachments with files
        - without_file: Number of attachments without files
    """
    attachments = list(_all_items(zot, itemType="attachment"))

    by_content_type: dict[str, int] = {}
    by_link_mode: dict[str, int] = {}
    total_size = 0
    with_file = 0
    without_file = 0

    for att in attachments:
        data = att.get("data", {})

        # Count by content type
        content_type = data.get("contentType", "unknown")
        by_content_type[content_type] = by_content_type.get(content_type, 0) + 1

        # Count by link mode
        link_mode = data.get("linkMode", "unknown")
        by_link_mode[link_mode] = by_link_mode.get(link_mode, 0) + 1

        # Track file size if available
        file_size = data.get("fileSize", 0)
        if file_size:
            total_size += file_size
            with_file += 1
        else:
            without_file += 1

    return {
        "total": len(attachments),
        "by_content_type": by_content_type,
        "by_link_mode": by_link_mode,
        "total_size": total_size,
        "with_file": with_file,
        "without_file": without_file,
    }
