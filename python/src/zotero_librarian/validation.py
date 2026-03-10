"""
Validation functions for Zotero item fields (DOI, ISBN, ISSN, URLs).
"""

from typing import Generator
from pyzotero import zotero

from .client import _all_items


def validate_doi(doi: str) -> bool:
    """Check if DOI format is valid."""
    import re
    pattern = r"10\.\d{4,9}/[-._;()/:A-Z0-9]+"
    return bool(re.match(pattern, doi, re.IGNORECASE))


def validate_isbn(isbn: str) -> bool:
    """Check if ISBN format is valid (ISBN-10 or ISBN-13)."""
    import re
    isbn = isbn.replace("-", "").replace(" ", "")
    if len(isbn) == 10:
        return bool(re.match(r"\d{9}[\dX]", isbn))
    elif len(isbn) == 13:
        return bool(re.match(r"\d{13}", isbn))
    return False


def validate_issn(issn: str) -> bool:
    """Check if ISSN format is valid."""
    import re
    return bool(re.match(r"\d{4}-\d{3}[\dX]", issn))


def items_with_invalid_doi(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find items with invalid DOI format."""
    for item in _all_items(zot):
        doi = item["data"].get("DOI", "")
        if doi and not validate_doi(doi):
            yield item


def items_with_invalid_isbn(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find items with invalid ISBN format."""
    for item in _all_items(zot):
        isbn = item["data"].get("ISBN", "")
        if isbn and not validate_isbn(isbn):
            yield item


def items_with_invalid_issn(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find items with invalid ISSN format."""
    for item in _all_items(zot):
        issn = item["data"].get("ISSN", "")
        if issn and not validate_issn(issn):
            yield item


def items_with_broken_urls(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find items with malformed URLs."""
    import re
    url_pattern = re.compile(r"^https?://")
    for item in _all_items(zot):
        url = item["data"].get("url", "")
        if url and not url_pattern.match(url):
            yield item


def items_with_placeholder_text(
    zot: zotero.Zotero,
    field: str,
    patterns: list[str]
) -> Generator[dict, None, None]:
    """Find items with placeholder text in a field."""
    for item in _all_items(zot):
        value = item["data"].get(field, "") or ""
        if any(p.lower() in value.lower() for p in patterns):
            yield item


def items_with_placeholder_titles(zot: zotero.Zotero) -> Generator[dict, None, None]:
    """Find items with placeholder titles."""
    yield from items_with_placeholder_text(
        zot, "title", ["untitled", "[no title]", "todo", "tbd"]
    )
