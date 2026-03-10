"""
Duplicate detection functions for Zotero library items.
"""

from pyzotero import zotero

from .client import _all_items
from .query import all_tags


def find_duplicates_by_title(zot: zotero.Zotero) -> dict[str, list[dict]]:
    """Find items with exact duplicate titles (case-insensitive).

    Returns: {normalised_title: [items...]}
    """
    return find_duplicates_by_field(zot, "title")


def find_fuzzy_duplicates_by_title(
    zot: zotero.Zotero,
    threshold: int = 85,
) -> list[list[dict]]:
    """Find near-duplicate items by title using fuzzy matching.

    Uses rapidfuzz.fuzz.token_sort_ratio to compare titles.  Two items are
    placed in the same group when their score is >= threshold.  Groups are
    built with a single-link clustering approach: an item joins a group if it
    scores >= threshold against *any* existing member of that group.

    Args:
        zot: Zotero client
        threshold: Minimum token_sort_ratio score (0–100) to consider two
                   titles as duplicates.  Defaults to 85.

    Returns:
        List of groups; each group is a list of items whose titles are
        mutually similar.  Only groups with two or more items are returned.
    """
    from rapidfuzz.fuzz import token_sort_ratio

    items = [
        item
        for item in _all_items(zot)
        if item["data"].get("itemType") not in {"attachment", "note"}
        and item["data"].get("title", "").strip()
    ]

    # groups: list of (list-of-items, list-of-lowercased-titles)
    groups: list[tuple[list[dict], list[str]]] = []

    for item in items:
        title = item["data"]["title"].strip().lower()
        placed = False
        for group_items, group_titles in groups:
            if any(token_sort_ratio(title, gt) >= threshold for gt in group_titles):
                group_items.append(item)
                group_titles.append(title)
                placed = True
                break
        if not placed:
            groups.append(([item], [title]))

    return [g_items for g_items, _ in groups if len(g_items) >= 2]


def find_duplicates_by_field(zot: zotero.Zotero, field: str) -> dict[str, list[dict]]:
    """Find items with duplicate values in a field.

    Returns: {field_value: [items...]}
    """
    from collections import defaultdict
    by_value: dict[str, list[dict]] = defaultdict(list)
    for item in _all_items(zot):
        value = item["data"].get(field, "")
        if value:
            by_value[value.lower() if isinstance(value, str) else value].append(item)
    return {k: v for k, v in by_value.items() if len(v) > 1}


def duplicate_dois(zot: zotero.Zotero) -> dict[str, list[dict]]:
    """Find items with duplicate DOIs."""
    return find_duplicates_by_field(zot, "DOI")


def duplicate_titles(zot: zotero.Zotero) -> dict[str, list[dict]]:
    """Find items with duplicate titles."""
    return find_duplicates_by_field(zot, "title")


def creator_name_variations(zot: zotero.Zotero) -> dict[str, list[str]]:
    """Find author names with format variations.

    Returns: {last_name: ["John Smith", "Smith, John", ...]}
    """
    from collections import defaultdict
    names: dict[str, list[str]] = defaultdict(list)
    for item in _all_items(zot):
        for creator in item["data"].get("creators", []):
            first = creator.get("firstName", "")
            last = creator.get("lastName", "")
            if first and last:
                names[last.lower()].append(f"{first} {last}")
    return {k: list(set(v)) for k, v in names.items() if len(set(v)) > 1}


def journal_name_variations(zot: zotero.Zotero) -> dict[str, list[str]]:
    """Find journal names with variations (abbreviations, typos, etc.).

    Returns: {normalized_name: ["Nature", "Nature (London)", ...]}
    """
    from collections import defaultdict
    import re
    journals: dict[str, list[str]] = defaultdict(list)
    for item in _all_items(zot, itemType="journalArticle"):
        journal = item["data"].get("publicationTitle", "")
        if journal:
            key = re.sub(r"[\s\-]+", " ", journal.lower().strip())
            journals[key].append(journal)
    return {k: list(set(v)) for k, v in journals.items() if len(set(v)) > 1}


def similar_tags(zot: zotero.Zotero, threshold: float = 0.8) -> dict[str, list[str]]:
    """Find similar tags (potential duplicates/typos).

    Returns: {tag: [similar_tags...]}
    """
    from difflib import SequenceMatcher
    tags = list(all_tags(zot).keys())
    result = {}
    for tag in tags:
        similar = [
            t for t in tags
            if t != tag and SequenceMatcher(None, t, tag).ratio() >= threshold
        ]
        if similar:
            result[tag] = similar
    return result
