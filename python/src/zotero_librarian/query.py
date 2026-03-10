"""
Query functions for Zotero library items, search, and filtering.
"""

from typing import Any, Generator
from pyzotero import zotero

from .client import get_zotero, _all_items, _get_library_with_children


def all_items(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Get all items in library."""
    yield from _all_items(zot)


def all_items_by_type(zot: zotero.Zotero, item_type: str) -> Generator[dict, None, None]:
    """Get all items of a specific type."""
    yield from _all_items(zot, itemType=item_type)


def get_item(zot: zotero.Zotero, item_key: str) -> dict:
    """Get a single item by key."""
    return zot.item(item_key)


def get_children(zot: zotero.Zotero, item_key: str) -> list[dict]:
    """Get all child items for a parent item."""
    return zot.children(item_key)


def get_attachments(zot: zotero.Zotero, item_key: str) -> list[dict]:
    """Get all attachments for an item."""
    item = zot.item(item_key)
    children = zot.children(item_key)
    return [c for c in children if c["data"]["itemType"] == "attachment"]


def _get_notes(item: dict) -> list[dict]:
    """Get notes for an item from cached _children."""
    return [
        c for c in item.get('_children', [])
        if c['data']['itemType'] == 'note'
    ]


def get_notes(zot: zotero.Zotero, item_key: str) -> list[dict]:
    """Get all notes for an item."""
    children = zot.children(item_key)
    return [c for c in children if c["data"]["itemType"] == "note"]


def get_citations(zot: zotero.Zotero, item_key: str) -> dict[str, list[str]]:
    """Get citation relations for an item.

    Returns: {"cites": [...], "citedBy": [...]}
    """
    item = zot.item(item_key)
    relations = item["data"].get("relations", {})
    return {
        "cites": relations.get("dc:relation:cites", []),
        "citedBy": relations.get("dc:relation:citedBy", []),
    }


def get_collections(zot: zotero.Zotero) -> list[dict]:
    """Get all collections with item counts."""
    collections = zot.collections()
    result = []
    for coll in collections:
        items = zot.collection_items(coll["key"])
        result.append({
            "key": coll["key"],
            "name": coll["data"]["name"],
            "item_count": len(items),
        })
    return result


def all_tags(zot: zotero.Zotero) -> dict[str, int]:
    """Get all tags with frequency counts."""
    from collections import Counter
    tags = []
    for item in _all_items(zot):
        for tag in item["data"].get("tags", []):
            tag_str = tag.get("tag", "")
            if tag_str:
                tags.append(tag_str)
    return dict(Counter(tags))


def items_without_pdf(zot: zotero.Zotero) -> list[dict]:
    """Find all items without a PDF attachment."""
    items = _get_library_with_children(zot)
    result = []
    for item in items:
        has_pdf = any(
            c['data'].get('contentType') == 'application/pdf'
            for c in item.get('_children', [])
            if c['data']['itemType'] == 'attachment'
        )
        if not has_pdf:
            result.append(item)
    return result


def items_without_attachments(zot: zotero.Zotero) -> list[dict]:
    """Find all items without any attachments."""
    items = _get_library_with_children(zot)
    return [
        item for item in items
        if not any(c['data']['itemType'] == 'attachment' for c in item.get('_children', []))
    ]


def items_without_tags(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find all items without tags."""
    for item in _all_items(zot):
        if not item["data"].get("tags"):
            yield item


def items_not_in_collection(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find all items not filed in any collection."""
    for item in _all_items(zot):
        if not item["data"].get("collections"):
            yield item


def items_without_field(zot: zotero.Zotero, field: str) -> Generator[dict, None, None]:
    """Find all items where a field is missing or empty."""
    for item in _all_items(zot):
        if not item["data"].get(field) or item["data"].get(field) == "":
            yield item


def items_without_abstract(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find all items without an abstract."""
    yield from items_without_field(zot, "abstractNote")


def items_missing_required_fields(
    zot: zotero.Zotero,
    item_type: str,
    fields: list[str]
) -> Generator[dict, None, None]:
    """Find items of a type missing required fields."""
    for item in _all_items(zot, itemType=item_type):
        if any(not item["data"].get(f) for f in fields):
            yield item


def items_without_cites(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find all items without 'cites' relations."""
    for item in _all_items(zot):
        cites = get_citations(zot, item["key"])
        if not cites["cites"]:
            yield item


def items_without_cited_by(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find all items without 'citedBy' relations."""
    for item in _all_items(zot):
        cites = get_citations(zot, item["key"])
        if not cites["citedBy"]:
            yield item


def preprints_without_doi(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find all preprints without a DOI (may be unpublished)."""
    for item in _all_items(zot, itemType="preprint"):
        if not item["data"].get("DOI"):
            yield item


def items_with_notes(zot: zotero.Zotero) -> list[dict]:
    """Find all items that have notes."""
    items = _get_library_with_children(zot)
    return [item for item in items if _get_notes(item)]


def empty_collections(zot: zotero.Zotero) -> list[dict]:
    """Find collections with no items."""
    return [c for c in get_collections(zot) if c["item_count"] == 0]


def single_item_collections(zot: zotero.Zotero) -> list[dict]:
    """Find collections with exactly one item."""
    return [c for c in get_collections(zot) if c["item_count"] == 1]


# =============================================================================
# Search/Query Tools
# =============================================================================

def search_by_title(zot: zotero.Zotero, query: str) -> list[dict]:
    """Search items by title substring (case-insensitive).

    Args:
        zot: Zotero client
        query: Substring to search for in item titles

    Returns:
        List of items with titles containing the query string
    """
    results = []
    for item in _all_items(zot):
        title = item["data"].get("title", "") or ""
        if query.lower() in title.lower():
            results.append(item)
    return results


def search_by_author(zot: zotero.Zotero, name: str) -> list[dict]:
    """Search items by author name (matches firstName or lastName).

    Args:
        zot: Zotero client
        name: Author name to search for (matches firstName or lastName)

    Returns:
        List of items with creators matching the name
    """
    results = []
    name_lower = name.lower()
    for item in _all_items(zot):
        creators = item["data"].get("creators", [])
        for creator in creators:
            first = creator.get("firstName", "") or ""
            last = creator.get("lastName", "") or ""
            if name_lower in first.lower() or name_lower in last.lower():
                results.append(item)
                break
    return results


def search_by_abstract(zot: zotero.Zotero, query: str) -> list[dict]:
    """Search items by abstract substring (case-insensitive).

    Args:
        zot: Zotero client
        query: Substring to search for in item abstracts

    Returns:
        List of items with abstracts containing the query string
    """
    results = []
    for item in _all_items(zot):
        abstract = item["data"].get("abstractNote", "") or ""
        if query.lower() in abstract.lower():
            results.append(item)
    return results


def search_fulltext(zot: zotero.Zotero, query: str, fields: list[str] = None) -> Generator[dict, None, None]:
    """Search items by full-text across multiple fields.

    Uses Zotero API's qmode=everything to search attachment content.

    Args:
        zot: Zotero client
        query: Substring to search for
        fields: Optional list of field names to search in addition to full-text.
                If None, searches everything via API.

    Yields:
        Items where query appears in full-text or specified fields

    Note:
        Returns ALL matching items. No limit.
        Requires Zotero 7+ with full-text indexing enabled.
    """
    if fields is None:
        # Use API's native full-text search
        yield from _all_items(zot, q=query, qmode='everything')
    else:
        # Search specific fields manually
        query_lower = query.lower()
        for item in _all_items(zot):
            data = item["data"]
            for field in fields:
                value = data.get(field, "") or ""
                if query_lower in value.lower():
                    yield item
                    break


def search_by_year(zot: zotero.Zotero, year: int) -> list[dict]:
    """Filter items by exact year.

    Args:
        zot: Zotero client
        year: Year to filter by (e.g., 2024)

    Returns:
        List of items from the specified year
    """
    results = []
    year_str = str(year)
    for item in _all_items(zot):
        date = item["data"].get("date", "") or ""
        if date.startswith(year_str):
            results.append(item)
    return results


def search_by_year_range(zot: zotero.Zotero, start_year: int, end_year: int) -> list[dict]:
    """Filter items by year range (inclusive).

    Args:
        zot: Zotero client
        start_year: Start year (inclusive)
        end_year: End year (inclusive)

    Returns:
        List of items within the year range
    """
    results = []
    for item in _all_items(zot):
        date = item["data"].get("date", "") or ""
        if len(date) >= 4:
            try:
                item_year = int(date[:4])
                if start_year <= item_year <= end_year:
                    results.append(item)
            except ValueError:
                continue
    return results


def search_by_collection(zot: zotero.Zotero, collection_key: str) -> list[dict]:
    """Get items in a collection.

    Args:
        zot: Zotero client
        collection_key: Key of the collection to query

    Returns:
        List of items in the specified collection
    """
    return list(_all_items(zot, collection=collection_key))


def search_by_tag(zot: zotero.Zotero, tag: str) -> list[dict]:
    """Get items with specific tag.

    Args:
        zot: Zotero client
        tag: Tag string to search for

    Returns:
        List of items with the specified tag
    """
    return list(_all_items(zot, tag=tag))


def search_advanced(zot: zotero.Zotero, filters: dict[str, Any]) -> list[dict]:
    """Combined search with multiple filters.

    Args:
        zot: Zotero client
        filters: Dict of filter criteria. Supported keys:
            - itemType: Filter by item type (e.g., "journalArticle")
            - year: Filter by exact year (int)
            - year_start: Filter by start year (inclusive)
            - year_end: Filter by end year (inclusive)
            - tag: Filter by tag
            - collection: Filter by collection key
            - query: Search title substring (case-insensitive)

    Returns:
        List of items matching all specified filters
    """
    # Build kwargs for Zotero API filtering
    kwargs = {}
    if "itemType" in filters:
        kwargs["itemType"] = filters["itemType"]
    if "tag" in filters:
        kwargs["tag"] = filters["tag"]
    if "collection" in filters:
        kwargs["collection"] = filters["collection"]

    # Fetch items with API-level filters
    items = list(_all_items(zot, **kwargs))

    # Apply additional filters that require post-processing
    results = []
    for item in items:
        # Year filter
        if "year" in filters:
            date = item["data"].get("date", "") or ""
            year_str = str(filters["year"])
            if not date.startswith(year_str):
                continue

        # Year range filter
        if "year_start" in filters or "year_end" in filters:
            date = item["data"].get("date", "") or ""
            if len(date) < 4:
                continue
            try:
                item_year = int(date[:4])
                if "year_start" in filters and item_year < filters["year_start"]:
                    continue
                if "year_end" in filters and item_year > filters["year_end"]:
                    continue
            except ValueError:
                continue

        # Title query filter
        if "query" in filters:
            title = item["data"].get("title", "") or ""
            if filters["query"].lower() not in title.lower():
                continue

        results.append(item)

    return results


def get_item_by_key(zot: zotero.Zotero, key: str) -> dict | None:
    """Get an item by its Zotero key.

    Retrieves a single item using its unique Zotero key.

    Args:
        zot: Zotero client
        key: The Zotero item key (e.g., "ABC123DEF")

    Returns:
        The item dict if found, None otherwise

    Example:
        item = get_item_by_key(zot, "ABC123DEF")
        if item:
            print(f"Found: {item['data']['title']}")
    """
    try:
        return zot.item(key)
    except Exception:
        return None


def get_item_by_doi(zot: zotero.Zotero, doi: str) -> dict | None:
    """Find an item by its DOI.

    Searches the library for an item with the specified DOI.

    Args:
        zot: Zotero client
        doi: Digital Object Identifier to search for

    Returns:
        The item dict if found, None otherwise
    """
    doi_clean = doi.strip().lower()
    for item in _all_items(zot):
        item_doi = item["data"].get("DOI", "") or ""
        if item_doi.lower() == doi_clean:
            return item
    return None


def get_item_by_isbn(zot: zotero.Zotero, isbn: str) -> dict | None:
    """Find an item by its ISBN.

    Searches the library for an item with the specified ISBN.

    Args:
        zot: Zotero client
        isbn: International Standard Book Number to search for

    Returns:
        The item dict if found, None otherwise
    """
    # Clean ISBN (remove hyphens and spaces)
    isbn_clean = isbn.replace("-", "").replace(" ", "")
    for item in _all_items(zot):
        item_isbn = item["data"].get("ISBN", "") or ""
        item_isbn_clean = item_isbn.replace("-", "").replace(" ", "")
        if item_isbn_clean == isbn_clean:
            return item
    return None


def get_orphaned_attachments(zot: zotero.Zotero) -> list[dict]:
    """Find attachments without a valid parent item.

    Identifies attachment items whose parent item no longer exists
    or has been deleted.

    Args:
        zot: Zotero client

    Returns:
        List of orphaned attachment items
    """
    orphans = []

    # Get all attachments
    for att in _all_items(zot, itemType="attachment"):
        parent_key = att["data"].get("parentItem")
        if parent_key:
            # Check if parent exists
            try:
                parent = zot.item(parent_key)
                if not parent:
                    orphans.append(att)
            except Exception:
                orphans.append(att)
        else:
            # Attachments without parentItem are standalone (may be intentional)
            # But we include them as potentially orphaned
            orphans.append(att)

    return orphans


def get_trash_items(zot: zotero.Zotero) -> list[dict]:
    """Get items in the trash.

    Retrieves all items that have been moved to trash but not
    permanently deleted.

    Args:
        zot: Zotero client

    Returns:
        List of items in trash

    Note:
        The local Zotero API may not directly support trash queries.
        This function attempts to use the deleted API endpoint.
        If not available, returns empty list.
    """
    try:
        # Try to get deleted items from the API
        # Note: This may not work with all Zotero configurations
        deleted = zot.deleted()
        if deleted:
            return deleted
        return []
    except Exception:
        # Trash API may not be available via local API
        return []


def _strip_html(html: str) -> str:
    """Remove HTML tags from a string, preserving text content."""
    import re
    # Replace block-level tags with newlines for readability
    html = re.sub(r"</?(p|div|br|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", html)
    # Collapse excess whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_citation_key(extra: str) -> str | None:
    """Extract BibTeX citation key from the Extra field (pattern: 'Citation Key: <key>')."""
    import re
    match = re.search(r"(?mi)^Citation Key:\s*(\S+)", extra)
    return match.group(1) if match else None


def find_notes(zot: zotero.Zotero) -> dict[str, Any]:
    """Find all notes grouped by parent item, with HTML stripped and citation keys extracted.

    For each parent item, extracts the BibTeX citation key from the Extra field
    (pattern: 'Citation Key: <key>') and strips HTML from note content.

    Returns a dict with:
        - groups: list of dicts, each with:
            - parent_key: str
            - parent_title: str
            - citation_key: str | None
            - notes: list of dicts with 'key', 'plain_text', 'raw_note'
        - total_notes: int
        - total_parents: int
    """
    from collections import defaultdict

    # Collect all notes
    all_notes: list[dict] = list(_all_items(zot, itemType="note"))
    notes_by_parent: dict[str, list[dict]] = defaultdict(list)
    orphan_notes: list[dict] = []

    for note in all_notes:
        parent_key = note.get("data", {}).get("parentItem")
        if parent_key:
            notes_by_parent[parent_key].append(note)
        else:
            orphan_notes.append(note)

    groups = []
    for parent_key, notes in notes_by_parent.items():
        try:
            parent_item = zot.item(parent_key)
            parent_data = parent_item.get("data", {})
        except Exception:
            parent_data = {}

        parent_title = parent_data.get("title", "")
        extra = parent_data.get("extra", "") or ""
        citation_key = _extract_citation_key(extra)

        note_entries = [
            {
                "key": n["key"],
                "raw_note": n.get("data", {}).get("note", ""),
                "plain_text": _strip_html(n.get("data", {}).get("note", "") or ""),
            }
            for n in notes
        ]
        groups.append(
            {
                "parent_key": parent_key,
                "parent_title": parent_title,
                "citation_key": citation_key,
                "notes": note_entries,
            }
        )

    # Include orphan notes under a sentinel group
    if orphan_notes:
        groups.append(
            {
                "parent_key": None,
                "parent_title": None,
                "citation_key": None,
                "notes": [
                    {
                        "key": n["key"],
                        "raw_note": n.get("data", {}).get("note", ""),
                        "plain_text": _strip_html(n.get("data", {}).get("note", "") or ""),
                    }
                    for n in orphan_notes
                ],
            }
        )

    total_notes = sum(len(g["notes"]) for g in groups)
    return {
        "groups": groups,
        "total_notes": total_notes,
        "total_parents": len(notes_by_parent),
    }
