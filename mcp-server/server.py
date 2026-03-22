"""FastMCP server for Zotero library management."""

import json
import os
import subprocess
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

MANAGER_REPO = os.environ.get(
    "ZOTERO_LIBRARIAN_CLI_SPEC",
    "git+https://github.com/dzackgarza/zotero-manager.git",
)


def _run_dispatch(tool_name: str, args: dict) -> Any:
    cmd = [
        "uvx",
        "--from",
        MANAGER_REPO,
        "python",
        "-m",
        "zotero_librarian._dispatch",
        tool_name,
        json.dumps(args),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "error": result.stderr or f"Command failed with code {result.returncode}"
        }
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()


mcp = FastMCP(
    name="zotero-librarian",
    instructions="Manage a local Zotero library, including search, tagging, imports, exports, and enrichment flows.",
)


@mcp.tool()
def zotero_stats(
    action: Annotated[
        str, Field(description="'summary', 'types', 'years', 'tags', or 'attachments'")
    ],
) -> dict:
    """Use when you need aggregate statistics about the local Zotero library."""
    method_map = {
        "summary": "library_summary",
        "types": "items_per_type",
        "years": "items_per_year",
        "tags": "tag_cloud",
        "attachments": "attachment_summary",
    }
    tool_name = method_map.get(action)
    if not tool_name:
        return {"error": f"Unknown action: {action}"}
    return _run_dispatch(tool_name, {})


@mcp.tool()
def zotero_search(
    action: Annotated[
        str,
        Field(
            description="'by_title', 'by_author', 'without_pdf', 'without_tags', 'not_in_collection', 'duplicate_dois', 'duplicate_titles', or 'invalid_dois'",
        ),
    ],
    query: Annotated[
        str | None, Field(description="Search query for title/author modes")
    ] = None,
) -> Any:
    """Use when you need to search or filter the local Zotero library."""
    method_map = {
        "by_title": "search_by_title",
        "by_author": "search_by_author",
        "without_pdf": "items_without_pdf",
        "without_tags": "items_without_tags",
        "not_in_collection": "items_not_in_collection",
        "duplicate_dois": "duplicate_dois",
        "duplicate_titles": "duplicate_titles",
        "invalid_dois": "items_with_invalid_doi",
    }
    tool_name = method_map.get(action)
    if not tool_name:
        return {"error": f"Unknown action: {action}"}

    args = {}
    if query is not None:
        args["query"] = query

    return _run_dispatch(tool_name, args)


@mcp.tool()
def zotero_get_item(
    item_key: Annotated[str, Field(description="Zotero item key")],
) -> dict:
    """Use when you need the full local Zotero record for one item."""
    return _run_dispatch("get_item", {"item_key": item_key})


@mcp.tool()
def zotero_children(
    item_key: Annotated[str, Field(description="Parent Zotero item key")],
) -> list[dict]:
    """Use when you need attachments or notes for a Zotero item."""
    return _run_dispatch("get_children", {"item_key": item_key})


@mcp.tool()
def zotero_update_item(
    item_key: Annotated[str, Field(description="Zotero item key")],
    fields: Annotated[
        dict, Field(description="Fields to update, e.g. {'title': 'New Title'}")
    ],
) -> dict:
    """Use when you need to update fields on a Zotero item."""
    return _run_dispatch("update_item_fields", {"item_key": item_key, "fields": fields})


@mcp.tool()
def zotero_tags(
    action: Annotated[str, Field(description="'list', 'add', or 'remove'")],
    item_key: Annotated[
        str | None, Field(description="Item key for add/remove operations")
    ] = None,
    tags: Annotated[
        list[str] | None, Field(description="Tags to add or remove")
    ] = None,
) -> Any:
    """Use when you need to inspect or edit Zotero item tags."""
    method_map = {
        "list": "all_tags",
        "add": "add_tags_to_item",
        "remove": "remove_tags_from_item",
    }
    tool_name = method_map.get(action)
    if not tool_name:
        return {"error": f"Unknown action: {action}"}

    args = {}
    if item_key is not None:
        args["item_key"] = item_key
    if tags is not None:
        args["tags"] = tags

    return _run_dispatch(tool_name, args)


@mcp.tool()
def zotero_collections(
    action: Annotated[str, Field(description="'list' or 'move_item'")],
    item_key: Annotated[str | None, Field(description="Item key for move_item")] = None,
    collection_key: Annotated[
        str | None, Field(description="Collection key for move_item")
    ] = None,
) -> Any:
    """Use when you need to inspect local collections or move an item into one."""
    method_map = {
        "list": "get_collections",
        "move_item": "move_item_to_collection",
    }
    tool_name = method_map.get(action)
    if not tool_name:
        return {"error": f"Unknown action: {action}"}

    args = {}
    if item_key is not None:
        args["item_key"] = item_key
    if collection_key is not None:
        args["collection_key"] = collection_key

    return _run_dispatch(tool_name, args)


@mcp.tool()
def zotero_collections(
    action: Annotated[str, Field(description="'list' or 'move_item'")],
    item_key: Annotated[str | None, Field(description="Item key for move_item")] = None,
    collection_key: Annotated[
        str | None, Field(description="Collection key for move_item")
    ] = None,
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
    method_map = {
        "by_doi": "import_by_doi",
        "by_isbn": "import_by_isbn",
        "by_pmid": "import_by_pmid",
    }
    tool_name = method_map.get(action)
    if not tool_name:
        return {"error": f"Unknown action: {action}"}
    return _run_dispatch(tool_name, {"identifier": identifier})


@mcp.tool()
def zotero_batch_add(
    identifiers: Annotated[
        list[str], Field(description="Identifiers to import in order")
    ],
    id_type: Annotated[str, Field(description="'doi', 'isbn', or 'pmid'")] = "doi",
    collection: Annotated[
        str | None, Field(description="Collection key to add imported items into")
    ] = None,
    tags: Annotated[
        str | None, Field(description="Comma-separated tags to add to imported items")
    ] = None,
    force: Annotated[bool, Field(description="Skip duplicate detection")] = False,
) -> dict:
    """Use when you need to import many identifiers into Zotero at once."""
    return _run_dispatch(
        "batch_add_identifiers",
        {
            "identifiers": identifiers,
            "id_type": id_type,
            "collection": collection,
            "tags": tags,
            "force": force,
        },
    )


@mcp.tool()
def zotero_export(
    action: Annotated[
        str, Field(description="'json', 'bibtex', 'csv', 'ris', or 'csljson'")
    ],
    collection: Annotated[
        str | None, Field(description="Optional collection key filter")
    ] = None,
) -> str:
    """Use when you need a text export of the Zotero library."""
    method_map = {
        "json": "export_to_json",
        "bibtex": "export_to_bibtex",
        "csv": "export_to_csv",
        "ris": "export_to_ris",
        "csljson": "export_to_csljson",
    }
    tool_name = method_map.get(action)
    if not tool_name:
        return f'{{"error":"Unknown action: {action}"}}'

    args = {}
    if collection is not None:
        args["collection_key" if action in ["ris", "csljson"] else "collection"] = (
            collection
        )

    return _run_dispatch(tool_name, args)


@mcp.tool()
def zotero_delete_items(
    item_keys: Annotated[list[str], Field(description="Item keys to move to trash")],
) -> dict:
    """Use when you need to move one or more Zotero items to trash."""
    if len(item_keys) == 1:
        return _run_dispatch("delete_item", {"item_key": item_keys[0]})
    return _run_dispatch("batch_delete_items", {"item_keys": item_keys})


@mcp.tool()
def zotero_check_pdfs(
    collection: Annotated[
        str | None, Field(description="Optional collection key filter")
    ] = None,
) -> dict:
    """Use when you need a summary of which Zotero items are missing PDFs."""
    return _run_dispatch("check_pdfs", {"collection": collection})


@mcp.tool()
def zotero_crossref(
    text: Annotated[str, Field(description="Citation text in Author (Year) form")],
    collection: Annotated[
        str | None, Field(description="Optional collection key filter")
    ] = None,
) -> dict:
    """Use when you need to match citation text against the local Zotero library."""
    return _run_dispatch("crossref_citations", {"text": text, "collection": collection})


@mcp.tool()
def zotero_find_dois(
    apply: Annotated[
        bool, Field(description="Write matched DOIs back to Zotero")
    ] = False,
    limit: Annotated[int | None, Field(description="Maximum items to process")] = None,
    collection: Annotated[
        str | None, Field(description="Collection key filter")
    ] = None,
) -> dict:
    """Use when you need CrossRef-powered DOI backfilling for local Zotero items."""
    return _run_dispatch(
        "find_missing_dois", {"apply": apply, "limit": limit, "collection": collection}
    )


@mcp.tool()
def zotero_fetch_pdfs(
    dry_run: Annotated[
        bool, Field(description="Show matches without downloading")
    ] = False,
    limit: Annotated[int | None, Field(description="Maximum items to process")] = None,
    collection: Annotated[
        str | None, Field(description="Collection key filter")
    ] = None,
    download_dir: Annotated[
        str | None, Field(description="Directory to save PDFs into")
    ] = None,
    upload: Annotated[
        bool, Field(description="Upload fetched PDFs to Zotero storage")
    ] = False,
    sources: Annotated[
        list[str] | None, Field(description="PDF sources to try in order")
    ] = None,
) -> dict:
    """Use when you need to discover or attach open-access PDFs for Zotero items."""
    return _run_dispatch(
        "fetch_pdfs",
        {
            "dry_run": dry_run,
            "limit": limit,
            "collection": collection,
            "download_dir": download_dir,
            "upload": upload,
            "sources": sources,
        },
    )


@mcp.tool()
def zotero_count() -> int:
    """Use when you only need the local Zotero item count."""
    return _run_dispatch("count_items", {})


@mcp.tool()
def zotero_find_notes() -> dict:
    """Use when you need all notes grouped by parent item, with HTML stripped and BibTeX citation keys extracted."""
    return _run_dispatch("find_notes", {})


@mcp.tool()
def zotero_fuzzy_duplicate_titles(
    threshold: Annotated[
        int, Field(description="Similarity threshold 0-100 (default 85)")
    ] = 85,
) -> list:
    """Use when you need fuzzy/near-duplicate title detection across the local Zotero library."""
    return _run_dispatch("find_fuzzy_duplicates_by_title", {"threshold": threshold})


@mcp.tool()
def zotero_pdf_status() -> dict:
    """Use when you need a PDF coverage aggregate report for the local Zotero library."""
    return _run_dispatch("pdf_status", {})


@mcp.tool()
def zotero_cleanup(
    action: Annotated[
        str, Field(description="'snapshots', 'notes', or 'missing_pdfs'")
    ],
    dry_run: Annotated[
        bool, Field(description="Preview without modifying (default True)")
    ] = True,
    storage_root: Annotated[
        str | None, Field(description="Override Zotero storage path (for missing_pdfs)")
    ] = None,
) -> dict:
    """Use when you need to clean up HTML snapshots, all notes, or dangling PDF records in Zotero.

    Always defaults to dry_run=True for safety.
    """
    method_map = {
        "snapshots": "delete_snapshots",
        "notes": "delete_all_notes",
        "missing_pdfs": "clean_missing_pdfs",
    }
    tool_name = method_map.get(action)
    if not tool_name:
        return {"error": f"Unknown action: {action}"}

    args = {"dry_run": dry_run}
    if storage_root is not None:
        args["storage_root"] = storage_root

    return _run_dispatch(tool_name, args)


@mcp.tool()
def zotero_rename_pdf_attachments(
    dry_run: Annotated[
        bool, Field(description="Preview renames without writing (default True)")
    ] = True,
    collection_key: Annotated[
        str | None, Field(description="Restrict to a collection key")
    ] = None,
) -> list:
    """Use when you need to normalise PDF attachment titles based on their parent item's title."""
    return _run_dispatch(
        "rename_pdf_attachments", {"dry_run": dry_run, "collection_key": collection_key}
    )


@mcp.tool()
def zotero_extract_and_attach_text(
    item_key: Annotated[str, Field(description="Parent Zotero item key")],
) -> dict:
    """Use when you need to extract text from a PDF attachment and upload it as a .txt child.

    Requires pdftotext (poppler-utils) installed on the server host.
    """
    return _run_dispatch("extract_and_attach_text", {"item_key": item_key})


@mcp.tool()
def zotero_update_missing_dois(
    apply: Annotated[
        bool, Field(description="Write recovered DOIs back to Zotero")
    ] = False,
    limit: Annotated[int | None, Field(description="Maximum items to process")] = None,
) -> list:
    """Use when you need to attempt DOI recovery for items tagged '⛔ No DOI found' via CrossRef."""
    return _run_dispatch("update_missing_dois", {"apply": apply, "limit": limit})


if __name__ == "__main__":
    mcp.run()
