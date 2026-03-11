"""FastMCP server for Zotero library management."""

import sys
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from zotero_librarian.attachments import extract_and_attach_text, rename_pdf_attachments
from zotero_librarian.batch import batch_trash_items
from zotero_librarian.cleanup import clean_missing_pdfs, trash_all_notes, trash_snapshots
from zotero_librarian.client import count_items, get_zotero
from zotero_librarian.duplicates import duplicate_dois, duplicate_titles, find_fuzzy_duplicates_by_title
from zotero_librarian.enrichment import (
    batch_add_identifiers,
    check_pdfs,
    crossref_citations,
    fetch_pdfs,
    find_missing_dois,
    update_missing_dois,
)
from zotero_librarian.export import export_collection, export_to_bibtex, export_to_csljson, export_to_csv, export_to_json, export_to_ris
from zotero_librarian.import_ import import_by_doi, import_by_isbn, import_by_pmid
from zotero_librarian.items import add_tags_to_item, move_item_to_collection, remove_tags_from_item, trash_item, update_item_fields
from zotero_librarian.query import (
    all_tags,
    find_notes,
    get_children,
    get_collections,
    get_item,
    items_not_in_collection,
    items_without_pdf,
    items_without_tags,
    search_by_author,
    search_by_title,
)
from zotero_librarian.stats import attachment_summary, items_per_type, items_per_year, library_summary, pdf_status, tag_cloud
from zotero_librarian.validation import items_with_invalid_doi


mcp = FastMCP(
    name="zotero-librarian",
    instructions="Manage a local Zotero library, including search, tagging, imports, exports, and enrichment flows.",
)


def _zot():
    return get_zotero()


@mcp.tool()
def zotero_stats(
    action: Annotated[str, Field(description="'summary', 'types', 'years', 'tags', or 'attachments'")],
) -> dict:
    """Use when you need aggregate statistics about the local Zotero library."""
    zot = _zot()
    if action == "summary":
        return library_summary(zot)
    if action == "types":
        return items_per_type(zot)
    if action == "years":
        return items_per_year(zot)
    if action == "tags":
        return tag_cloud(zot)
    if action == "attachments":
        return attachment_summary(zot)
    return {"error": f"Unknown action: {action}"}


@mcp.tool()
def zotero_search(
    action: Annotated[
        str,
        Field(
            description="'by_title', 'by_author', 'without_pdf', 'without_tags', 'not_in_collection', 'duplicate_dois', 'duplicate_titles', or 'invalid_dois'",
        ),
    ],
    query: Annotated[str | None, Field(description="Search query for title/author modes")] = None,
) -> Any:
    """Use when you need to search or filter the local Zotero library."""
    zot = _zot()
    if action == "by_title":
        return search_by_title(zot, query or "")
    if action == "by_author":
        return search_by_author(zot, query or "")
    if action == "without_pdf":
        return items_without_pdf(zot)
    if action == "without_tags":
        return list(items_without_tags(zot))
    if action == "not_in_collection":
        return list(items_not_in_collection(zot))
    if action == "duplicate_dois":
        return duplicate_dois(zot)
    if action == "duplicate_titles":
        return duplicate_titles(zot)
    if action == "invalid_dois":
        return list(items_with_invalid_doi(zot))
    return {"error": f"Unknown action: {action}"}


@mcp.tool()
def zotero_get_item(item_key: Annotated[str, Field(description="Zotero item key")]) -> dict:
    """Use when you need the full local Zotero record for one item."""
    return get_item(_zot(), item_key)


@mcp.tool()
def zotero_children(item_key: Annotated[str, Field(description="Parent Zotero item key")]) -> list[dict]:
    """Use when you need attachments or notes for a Zotero item."""
    return get_children(_zot(), item_key)


@mcp.tool()
def zotero_update_item(
    item_key: Annotated[str, Field(description="Zotero item key")],
    fields: Annotated[dict, Field(description="Fields to update, e.g. {'title': 'New Title'}")],
) -> dict:
    """Use when you need to update fields on a Zotero item."""
    return update_item_fields(_zot(), item_key, fields)


@mcp.tool()
def zotero_tags(
    action: Annotated[str, Field(description="'list', 'add', or 'remove'")],
    item_key: Annotated[str | None, Field(description="Item key for add/remove operations")] = None,
    tags: Annotated[list[str] | None, Field(description="Tags to add or remove")] = None,
) -> Any:
    """Use when you need to inspect or edit Zotero item tags."""
    zot = _zot()
    if action == "list":
        return all_tags(zot)
    if action == "add" and item_key and tags:
        return add_tags_to_item(zot, item_key, tags)
    if action == "remove" and item_key and tags:
        return remove_tags_from_item(zot, item_key, tags)
    return {"error": "Invalid action or missing parameters"}


@mcp.tool()
def zotero_collections(
    action: Annotated[str, Field(description="'list' or 'move_item'")],
    item_key: Annotated[str | None, Field(description="Item key for move_item")] = None,
    collection_key: Annotated[str | None, Field(description="Collection key for move_item")] = None,
) -> Any:
    """Use when you need to inspect local collections or move an item into one."""
    zot = _zot()
    if action == "list":
        return get_collections(zot)
    if action == "move_item" and item_key and collection_key:
        return move_item_to_collection(zot, item_key, collection_key)
    return {"error": "Invalid action or missing parameters"}


@mcp.tool()
def zotero_import(
    action: Annotated[str, Field(description="'by_doi', 'by_isbn', or 'by_pmid'")],
    identifier: Annotated[str, Field(description="Identifier to import")],
) -> Any:
    """Use when you need to import a DOI, ISBN, or PMID into Zotero."""
    zot = _zot()
    if action == "by_doi":
        return import_by_doi(zot, identifier)
    if action == "by_isbn":
        return import_by_isbn(zot, identifier)
    if action == "by_pmid":
        return import_by_pmid(zot, identifier)
    return {"error": f"Unknown action: {action}"}


@mcp.tool()
def zotero_batch_add(
    identifiers: Annotated[list[str], Field(description="Identifiers to import in order")],
    id_type: Annotated[str, Field(description="'doi', 'isbn', or 'pmid'")] = "doi",
    collection: Annotated[str | None, Field(description="Collection key to add imported items into")] = None,
    tags: Annotated[str | None, Field(description="Comma-separated tags to add to imported items")] = None,
    force: Annotated[bool, Field(description="Skip duplicate detection")] = False,
) -> dict:
    """Use when you need to import many identifiers into Zotero at once."""
    return batch_add_identifiers(
        _zot(),
        identifiers=identifiers,
        id_type=id_type,
        collection=collection,
        tags=tags,
        force=force,
    )


@mcp.tool()
def zotero_export(
    action: Annotated[str, Field(description="'json', 'bibtex', 'csv', 'ris', or 'csljson'")],
    collection: Annotated[str | None, Field(description="Optional collection key filter")] = None,
) -> str:
    """Use when you need a text export of the Zotero library."""
    zot = _zot()
    if collection and action in {"json", "bibtex", "csv"}:
        return export_collection(zot, collection, format=action) or ""
    if action == "json":
        return export_to_json(zot) or ""
    if action == "bibtex":
        return export_to_bibtex(zot) or ""
    if action == "csv":
        return export_to_csv(zot) or ""
    if action == "ris":
        return export_to_ris(zot, collection_key=collection) or ""
    if action == "csljson":
        return export_to_csljson(zot, collection_key=collection) or ""
    return f'{{"error":"Unknown action: {action}"}}'


@mcp.tool()
def zotero_trash_items(item_keys: Annotated[list[str], Field(description="Item keys to move to trash")]) -> dict:
    """Use when you need to move one or more Zotero items to trash."""
    if len(item_keys) == 1:
        return trash_item(_zot(), item_keys[0])
    return batch_trash_items(_zot(), item_keys)


@mcp.tool()
def zotero_check_pdfs(
    collection: Annotated[str | None, Field(description="Optional collection key filter")] = None,
) -> dict:
    """Use when you need a summary of which Zotero items are missing PDFs."""
    return check_pdfs(_zot(), collection=collection)


@mcp.tool()
def zotero_crossref(
    text: Annotated[str, Field(description="Citation text in Author (Year) form")],
    collection: Annotated[str | None, Field(description="Optional collection key filter")] = None,
) -> dict:
    """Use when you need to match citation text against the local Zotero library."""
    return crossref_citations(_zot(), text, collection=collection)


@mcp.tool()
def zotero_find_dois(
    apply: Annotated[bool, Field(description="Write matched DOIs back to Zotero")] = False,
    limit: Annotated[int | None, Field(description="Maximum items to process")] = None,
    collection: Annotated[str | None, Field(description="Collection key filter")] = None,
) -> dict:
    """Use when you need CrossRef-powered DOI backfilling for local Zotero items."""
    return find_missing_dois(_zot(), apply=apply, limit=limit, collection=collection)


@mcp.tool()
def zotero_fetch_pdfs(
    dry_run: Annotated[bool, Field(description="Show matches without downloading")] = False,
    limit: Annotated[int | None, Field(description="Maximum items to process")] = None,
    collection: Annotated[str | None, Field(description="Collection key filter")] = None,
    download_dir: Annotated[str | None, Field(description="Directory to save PDFs into")] = None,
    upload: Annotated[bool, Field(description="Upload fetched PDFs to Zotero storage")] = False,
    sources: Annotated[list[str] | None, Field(description="PDF sources to try in order")] = None,
) -> dict:
    """Use when you need to discover or attach open-access PDFs for Zotero items."""
    return fetch_pdfs(
        _zot(),
        dry_run=dry_run,
        limit=limit,
        collection=collection,
        download_dir=download_dir,
        upload=upload,
        sources=sources,
    )


@mcp.tool()
def zotero_count() -> int:
    """Use when you only need the local Zotero item count."""
    return count_items(_zot())


@mcp.tool()
def zotero_find_notes() -> dict:
    """Use when you need all notes grouped by parent item, with HTML stripped and BibTeX citation keys extracted."""
    return find_notes(_zot())


@mcp.tool()
def zotero_fuzzy_duplicate_titles(
    threshold: Annotated[int, Field(description="Similarity threshold 0-100 (default 85)")] = 85,
) -> list:
    """Use when you need fuzzy/near-duplicate title detection across the local Zotero library."""
    return find_fuzzy_duplicates_by_title(_zot(), threshold=threshold)


@mcp.tool()
def zotero_pdf_status() -> dict:
    """Use when you need a PDF coverage aggregate report for the local Zotero library."""
    return pdf_status(_zot())


@mcp.tool()
def zotero_cleanup(
    action: Annotated[str, Field(description="'snapshots', 'notes', or 'missing_pdfs'")],
    dry_run: Annotated[bool, Field(description="Preview without modifying (default True)")] = True,
    storage_root: Annotated[str | None, Field(description="Override Zotero storage path (for missing_pdfs)")] = None,
) -> dict:
    """Use when you need to clean up HTML snapshots, all notes, or dangling PDF records in Zotero.

    Always defaults to dry_run=True for safety.
    """
    zot = _zot()
    if action == "snapshots":
        return trash_snapshots(zot, dry_run=dry_run)
    if action == "notes":
        return trash_all_notes(zot, dry_run=dry_run)
    if action == "missing_pdfs":
        return clean_missing_pdfs(zot, dry_run=dry_run, storage_root=storage_root)
    return {"error": f"Unknown action: {action}"}


@mcp.tool()
def zotero_rename_pdf_attachments(
    dry_run: Annotated[bool, Field(description="Preview renames without writing (default True)")] = True,
    collection_key: Annotated[str | None, Field(description="Restrict to a collection key")] = None,
) -> list:
    """Use when you need to normalise PDF attachment titles based on their parent item's title."""
    return rename_pdf_attachments(_zot(), dry_run=dry_run, collection_key=collection_key)


@mcp.tool()
def zotero_extract_and_attach_text(
    item_key: Annotated[str, Field(description="Parent Zotero item key")],
) -> dict:
    """Use when you need to extract Markdown text from a PDF attachment and attach it to the item."""
    return extract_and_attach_text(_zot(), item_key)


@mcp.tool()
def zotero_update_missing_dois(
    apply: Annotated[bool, Field(description="Write recovered DOIs back to Zotero")] = False,
    limit: Annotated[int | None, Field(description="Maximum items to process")] = None,
) -> list:
    """Use when you need to attempt DOI recovery for items tagged '⛔ No DOI found' via CrossRef."""
    return update_missing_dois(_zot(), apply=apply, limit=limit)


if __name__ == "__main__":
    mcp.run()
