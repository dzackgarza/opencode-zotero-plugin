"""JSON-in/JSON-out CLI dispatcher for local Zotero operations."""

import json
import sys

from .attachments import extract_and_attach_text, rename_pdf_attachments
from .batch import batch_delete_items
from .cleanup import clean_missing_pdfs, delete_all_notes, delete_snapshots
from .client import count_items, get_zotero
from .connector import result_from_exception
from .duplicates import duplicate_dois, duplicate_titles, find_fuzzy_duplicates_by_title
from .enrichment import (
    batch_add_identifiers,
    check_pdfs,
    crossref_citations,
    fetch_pdfs,
    find_missing_dois,
    update_missing_dois,
)
from .export import export_collection, export_to_bibtex, export_to_csljson, export_to_csv, export_to_json, export_to_ris
from .import_ import import_by_doi, import_by_isbn, import_by_pmid
from .items import (
    add_tags_to_item,
    delete_item,
    move_item_to_collection,
    remove_tags_from_item,
    update_item_fields,
)
from .query import (
    all_items,
    all_tags,
    find_notes,
    get_children,
    get_collections,
    get_item,
    get_item_by_doi,
    get_item_by_key,
    items_not_in_collection,
    items_without_pdf,
    items_without_tags,
    search_advanced,
    search_by_author,
    search_by_title,
)
from .stats import attachment_summary, items_per_type, items_per_year, library_summary, pdf_status, tag_cloud
from .validation import items_with_invalid_doi


TOOLS = {
    "count_items": lambda zot, a: count_items(zot),
    "all_items": lambda zot, a: list(all_items(zot)),
    "get_item": lambda zot, a: get_item(zot, a["item_key"]),
    "get_item_by_key": lambda zot, a: get_item_by_key(zot, a["key"]),
    "get_item_by_doi": lambda zot, a: get_item_by_doi(zot, a["doi"]),
    "get_children": lambda zot, a: get_children(zot, a["item_key"]),
    "get_collections": lambda zot, a: get_collections(zot),
    "all_tags": lambda zot, a: all_tags(zot),
    "items_without_pdf": lambda zot, a: items_without_pdf(zot),
    "items_without_tags": lambda zot, a: list(items_without_tags(zot)),
    "items_not_in_collection": lambda zot, a: list(items_not_in_collection(zot)),
    "search_by_title": lambda zot, a: search_by_title(zot, a["query"]),
    "search_by_author": lambda zot, a: search_by_author(zot, a["name"]),
    "search_advanced": lambda zot, a: search_advanced(zot, a["filters"]),
    "duplicate_dois": lambda zot, a: duplicate_dois(zot),
    "duplicate_titles": lambda zot, a: duplicate_titles(zot),
    "find_fuzzy_duplicates_by_title": lambda zot, a: find_fuzzy_duplicates_by_title(
        zot,
        threshold=a.get("threshold", 85),
    ),
    "items_with_invalid_doi": lambda zot, a: list(items_with_invalid_doi(zot)),
    "find_notes": lambda zot, a: find_notes(zot),
    "update_item_fields": lambda zot, a: update_item_fields(zot, a["item_key"], a["fields"]),
    "add_tags_to_item": lambda zot, a: add_tags_to_item(zot, a["item_key"], a["tags"]),
    "remove_tags_from_item": lambda zot, a: remove_tags_from_item(zot, a["item_key"], a["tags"]),
    "move_item_to_collection": lambda zot, a: move_item_to_collection(zot, a["item_key"], a["collection_key"]),
    "delete_item": lambda zot, a: delete_item(zot, a["item_key"]),
    "delete_items": lambda zot, a: batch_delete_items(zot, a["item_keys"]),
    "library_summary": lambda zot, a: library_summary(zot),
    "items_per_type": lambda zot, a: items_per_type(zot),
    "items_per_year": lambda zot, a: items_per_year(zot),
    "tag_cloud": lambda zot, a: tag_cloud(zot),
    "attachment_summary": lambda zot, a: attachment_summary(zot),
    "pdf_status": lambda zot, a: pdf_status(zot),
    "check_pdfs": lambda zot, a: check_pdfs(zot, collection=a.get("collection")),
    "crossref_citations": lambda zot, a: crossref_citations(zot, a["text"], collection=a.get("collection")),
    "find_missing_dois": lambda zot, a: find_missing_dois(
        zot,
        apply=a.get("apply", False),
        limit=a.get("limit"),
        collection=a.get("collection"),
    ),
    "update_missing_dois": lambda zot, a: update_missing_dois(
        zot,
        apply=a.get("apply", False),
        limit=a.get("limit"),
    ),
    "delete_snapshots": lambda zot, a: delete_snapshots(
        zot,
        dry_run=a.get("dry_run", True),
    ),
    "delete_all_notes": lambda zot, a: delete_all_notes(
        zot,
        dry_run=a.get("dry_run", True),
    ),
    "clean_missing_pdfs": lambda zot, a: clean_missing_pdfs(
        zot,
        dry_run=a.get("dry_run", True),
        storage_root=a.get("storage_root"),
    ),
    "rename_pdf_attachments": lambda zot, a: rename_pdf_attachments(
        zot,
        dry_run=a.get("dry_run", True),
        collection_key=a.get("collection_key"),
    ),
    "extract_and_attach_text": lambda zot, a: extract_and_attach_text(
        zot,
        a["item_key"],
        extractor=a.get("extractor", "pdftotext"),
    ),
    "fetch_pdfs": lambda zot, a: fetch_pdfs(
        zot,
        dry_run=a.get("dry_run", False),
        limit=a.get("limit"),
        collection=a.get("collection"),
        download_dir=a.get("download_dir"),
        upload=a.get("upload", False),
        sources=a.get("sources"),
    ),
    "import_by_doi": lambda zot, a: import_by_doi(zot, a["doi"]),
    "import_by_isbn": lambda zot, a: import_by_isbn(zot, a["isbn"]),
    "import_by_pmid": lambda zot, a: import_by_pmid(zot, a["pmid"]),
    "batch_add_identifiers": lambda zot, a: batch_add_identifiers(
        zot,
        identifiers=a["identifiers"],
        id_type=a.get("id_type", "doi"),
        collection=a.get("collection"),
        tags=a.get("tags"),
        force=a.get("force", False),
    ),
    "export_to_json": lambda zot, a: export_to_json(zot, filepath=a.get("filepath")),
    "export_to_bibtex": lambda zot, a: export_to_bibtex(zot, filepath=a.get("filepath")),
    "export_to_csv": lambda zot, a: export_to_csv(zot, filepath=a.get("filepath")),
    "export_collection": lambda zot, a: export_collection(
        zot,
        collection_key=a["collection_key"],
        filepath=a.get("filepath"),
        format=a.get("format", "json"),
    ),
    "export_to_ris": lambda zot, a: export_to_ris(
        zot,
        collection_key=a.get("collection"),
        filepath=a.get("filepath"),
    ),
    "export_to_csljson": lambda zot, a: export_to_csljson(
        zot,
        collection_key=a.get("collection"),
        filepath=a.get("filepath"),
    ),
}


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python -m zotero_librarian._dispatch <tool_name> [json_args]"}))
        sys.exit(1)

    tool_name = sys.argv[1]
    args_json = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        args = json.loads(args_json)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"Invalid JSON args: {exc}"}))
        sys.exit(1)

    if tool_name not in TOOLS:
        print(json.dumps({"error": f"Unknown tool: {tool_name}", "available": sorted(TOOLS.keys())}))
        sys.exit(1)

    try:
        result = TOOLS[tool_name](get_zotero(), args)
        if isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps(result_from_exception(tool_name, exc), default=str, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
