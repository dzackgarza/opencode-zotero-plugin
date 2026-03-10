"""Integration tests for zotero_librarian tools. Require Zotero running."""
from zotero_librarian.client import count_items
from zotero_librarian.query import (
    all_items, all_items_by_type, get_item, get_attachments,
    get_notes, get_citations, get_collections, all_tags,
    items_without_pdf, items_without_attachments, items_without_tags,
    items_not_in_collection, items_without_abstract, items_missing_required_fields,
    items_without_cites, items_without_cited_by, preprints_without_doi, items_with_notes,
    empty_collections, single_item_collections,
)
from zotero_librarian.duplicates import duplicate_dois, duplicate_titles, creator_name_variations, journal_name_variations, similar_tags
from zotero_librarian.validation import (
    validate_doi, validate_isbn, validate_issn,
    items_with_invalid_doi, items_with_invalid_isbn, items_with_invalid_issn,
    items_with_broken_urls, items_with_placeholder_titles,
)
from zotero_librarian.items import attachment_info, check_item_completeness


# Fixtures live in conftest.py


class TestNavigation:
    def test_count_items(self, zot):
        assert count_items(zot) > 0

    def test_all_items(self, all_items_list):
        assert len(all_items_list) > 0
        assert "key" in all_items_list[0]
        assert "data" in all_items_list[0]

    def test_get_item(self, zot, first_item):
        item = get_item(zot, first_item["key"])
        assert item["key"] == first_item["key"]

    def test_get_attachments(self, zot, first_item):
        assert isinstance(get_attachments(zot, first_item["key"]), list)

    def test_get_notes(self, zot, first_item):
        assert isinstance(get_notes(zot, first_item["key"]), list)

    def test_get_citations(self, zot, first_item):
        cites = get_citations(zot, first_item["key"])
        assert "cites" in cites and "citedBy" in cites

    def test_get_collections(self, zot):
        assert isinstance(get_collections(zot), list)

    def test_all_tags(self, zot):
        assert isinstance(all_tags(zot), dict)


class TestMissingContent:
    def test_items_without_pdf(self, zot):
        assert isinstance(items_without_pdf(zot), list)

    def test_items_without_attachments(self, zot):
        assert isinstance(items_without_attachments(zot), list)

    def test_items_without_tags(self, zot):
        assert isinstance(list(items_without_tags(zot)), list)

    def test_items_not_in_collection(self, zot):
        assert isinstance(list(items_not_in_collection(zot)), list)

    def test_items_without_abstract(self, zot):
        assert isinstance(list(items_without_abstract(zot)), list)

    def test_items_with_notes(self, zot):
        assert isinstance(items_with_notes(zot), list)

    def test_preprints_without_doi(self, zot):
        assert isinstance(list(preprints_without_doi(zot)), list)


class TestCollections:
    def test_empty_collections(self, zot):
        assert isinstance(empty_collections(zot), list)

    def test_single_item_collections(self, zot):
        assert isinstance(single_item_collections(zot), list)


class TestDuplicates:
    def test_duplicate_dois(self, zot):
        assert isinstance(duplicate_dois(zot), dict)

    def test_duplicate_titles(self, zot):
        assert isinstance(duplicate_titles(zot), dict)

    def test_creator_name_variations(self, zot):
        assert isinstance(creator_name_variations(zot), dict)

    def test_journal_name_variations(self, zot):
        assert isinstance(journal_name_variations(zot), dict)

    def test_similar_tags(self, zot):
        assert isinstance(similar_tags(zot, threshold=0.8), dict)


class TestValidation:
    def test_validate_doi_valid(self):
        assert validate_doi("10.1000/test") is True

    def test_validate_doi_invalid(self):
        assert validate_doi("invalid") is False

    def test_validate_isbn_valid(self):
        assert validate_isbn("978-0-123456-78-9") is True

    def test_validate_issn_valid(self):
        assert validate_issn("1234-5678") is True

    def test_items_with_invalid_doi(self, zot):
        assert isinstance(list(items_with_invalid_doi(zot)), list)

    def test_items_with_invalid_isbn(self, zot):
        assert isinstance(list(items_with_invalid_isbn(zot)), list)

    def test_items_with_invalid_issn(self, zot):
        assert isinstance(list(items_with_invalid_issn(zot)), list)

    def test_items_with_broken_urls(self, zot):
        assert isinstance(list(items_with_broken_urls(zot)), list)

    def test_items_with_placeholder_titles(self, zot):
        assert isinstance(list(items_with_placeholder_titles(zot)), list)


class TestInspection:
    def test_attachment_info(self, zot, first_item):
        assert isinstance(attachment_info(zot, first_item["key"]), list)

    def test_check_item_completeness(self, zot, first_item):
        result = check_item_completeness(zot, first_item["key"], ["title", "date"])
        assert "complete" in result and "missing" in result
