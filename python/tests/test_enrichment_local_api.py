"""Live tests for local enrichment helpers."""

import json

from zotero_librarian.enrichment import check_pdfs, crossref_citations
from zotero_librarian.export import export_to_csljson, export_to_ris
from zotero_librarian.query import get_children


def _first_citable_item(items: list[dict]) -> dict:
    for item in items:
        item_type = item["data"].get("itemType")
        if item_type in {"attachment", "note"}:
            continue
        creators = item["data"].get("creators", [])
        date = item["data"].get("date", "")
        if creators and date[:4].isdigit():
            return item
    raise AssertionError("Expected at least one citable library item with creators and a year")


def _first_titled_item(items: list[dict]) -> dict:
    for item in items:
        item_type = item["data"].get("itemType")
        title = item["data"].get("title", "")
        if item_type not in {"attachment", "note"} and title:
            return item
    raise AssertionError("Expected at least one titled top-level library item")


def _has_pdf(children: list[dict]) -> bool:
    return any(
        child["data"].get("itemType") == "attachment"
        and child["data"].get("contentType") == "application/pdf"
        for child in children
    )


def _ris_exportable_items(items: list[dict]) -> list[dict]:
    return [
        item
        for item in items
        if item["data"].get("itemType") not in {"attachment", "note"}
    ]


class TestEnrichmentLocalApi:
    def test_get_children_matches_local_api(self, zot, first_item):
        assert [child["key"] for child in get_children(zot, first_item["key"])] == [
            child["key"] for child in zot.children(first_item["key"])
        ]

    def test_check_pdfs_matches_collection_children(self, zot, sample_collection, sample_collection_items):
        summary = check_pdfs(zot, collection=sample_collection["key"])
        missing_keys = sorted(
            item["key"]
            for item in sample_collection_items
            if not _has_pdf(zot.children(item["key"]))
        )

        assert summary["total"] == len(sample_collection_items)
        assert summary["without_pdf"] == len(missing_keys)
        assert summary["with_pdf"] + summary["without_pdf"] == summary["total"]
        assert sorted(item["key"] for item in summary["missing"]) == missing_keys

    def test_crossref_finds_constructed_library_citation(self, zot, sample_collection, sample_collection_items):
        item = _first_citable_item(sample_collection_items)
        creator = item["data"]["creators"][0]
        author = creator.get("lastName", creator.get("name", "")).split()[-1]
        year = item["data"]["date"][:4]

        result = crossref_citations(zot, f"{author} ({year})", collection=sample_collection["key"])

        assert any(match["item_key"] == item["key"] for match in result["found"])
        assert result["total_citations"] == 1

    def test_export_to_csljson_contains_known_item_title(self, zot, sample_collection, sample_collection_items):
        item = _first_titled_item(sample_collection_items)
        exported = json.loads(export_to_csljson(zot, collection_key=sample_collection["key"]))

        assert any(entry.get("title") == item["data"]["title"] for entry in exported)
        assert len(exported) == len(sample_collection_items)

    def test_export_to_ris_contains_known_item_title(self, zot, sample_collection, sample_collection_items):
        item = _first_titled_item(sample_collection_items)
        exported = export_to_ris(zot, collection_key=sample_collection["key"])
        exportable_items = _ris_exportable_items(sample_collection_items)

        assert item["data"]["title"] in exported
        assert exported.count("TY  -") == len(exportable_items)
