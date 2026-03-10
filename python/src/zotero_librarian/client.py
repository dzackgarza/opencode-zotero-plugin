"""
Zotero client initialization and core pagination helpers.
"""

from typing import Generator
from pyzotero import zotero


def get_zotero() -> zotero.Zotero:
    """Initialize Zotero client using local API.

    Requires Zotero 7+ running with local API enabled:
      Edit → Settings → Advanced → "Allow other applications to communicate with Zotero"
    """
    return zotero.Zotero(
        library_id="0",
        library_type="user",
        api_key="fake",
        local=True,
    )


def _all_items(zot: zotero.Zotero, **kwargs) -> Generator[dict, None, None]:
    """Fetch ALL items with automatic pagination.

    Zotero API limits to 100 items/request. This handles pagination.
    Yields items one at a time.
    """
    start = 0
    limit = 100
    while True:
        items = zot.items(start=start, limit=limit, **kwargs)
        if not items:
            break
        yield from items
        if len(items) < limit:
            break
        start += limit


def count_items(zot: zotero.Zotero) -> int:
    """Get total item count without fetching all items."""
    zot.items(limit=1)
    return int(zot.request.headers.get('Total-Results', 0))


def _get_library_with_children(zot: zotero.Zotero) -> list[dict]:
    """Fetch ALL items with their children in one batch operation.

    Returns items with '_children' key containing their attachments and notes.
    Caches result on zot object to avoid refetching.
    """
    # Return cached result if available
    if hasattr(zot, '_library_cache'):
        return zot._library_cache

    # Fetch all items
    items = list(_all_items(zot))
    items_by_key = {item['key']: item for item in items}

    # Fetch all attachments and notes in parallel (they're also items)
    attachments = list(_all_items(zot, itemType="attachment"))
    notes = list(_all_items(zot, itemType="note"))

    # Initialize _children on all items
    for item in items:
        item['_children'] = []

    # Group by parentItem
    for child in attachments + notes:
        parent_key = child['data'].get('parentItem')
        if parent_key and parent_key in items_by_key:
            items_by_key[parent_key]['_children'].append(child)

    # Cache for future calls
    zot._library_cache = items
    return items
