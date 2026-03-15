"""Typer CLI for Zotero Librarian."""

import json
import sys
from pathlib import Path
from typing import Any

import typer

from .attachments import DEFAULT_PDF_EXTRACTOR
from ._dispatch import run_tool
from .client import get_zotero


def _emit(data: Any) -> None:
    if isinstance(data, str):
        print(data)
        return
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
        return
    print(data)


def _zot():
    return get_zotero()


def _run(tool_name: str, args: dict) -> None:
    _emit(run_tool(tool_name, args, zot=_zot()))


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [entry.strip() for entry in value.split(",") if entry.strip()]


app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help=(
        "Manage your local Zotero library from the command line.\n\n"
        "Setup:\n"
        "- Start Zotero 7+ and enable local API access.\n"
        "- Run commands through `uv run zotero-lib ...` or installed `zotero-lib`."
    ),
)

stats_app = typer.Typer(no_args_is_help=True, help="Aggregate library statistics.")
search_app = typer.Typer(no_args_is_help=True, help="Search and quality checks.")
collections_app = typer.Typer(no_args_is_help=True, help="Collection operations.")
tags_app = typer.Typer(no_args_is_help=True, help="Tag inspection and editing.")
import_app = typer.Typer(no_args_is_help=True, help="Import references into Zotero.")
export_app = typer.Typer(no_args_is_help=True, help="Export library data.")
cleanup_app = typer.Typer(no_args_is_help=True, help="Dry-run-safe cleanup tasks.")
sync_app = typer.Typer(no_args_is_help=True, help="Local Zotero sync status.")


@app.command(help="Return the total item count.")
def count() -> None:
    _run("count_items", {})


@app.command(help="Get a single item by key.")
def get(item_key: str) -> None:
    _run("get_item", {"item_key": item_key})


@app.command(help="Get child notes and attachments for an item.")
def children(item_key: str) -> None:
    _run("get_children", {"item_key": item_key})


@app.command(help="Update item fields from a JSON object string.")
def update(item_key: str, fields_json: str) -> None:
    _run("update_item_fields", {"item_key": item_key, "fields": json.loads(fields_json)})


@app.command("delete", help="Move one or more items to trash.")
def delete_items(item_keys: list[str]) -> None:
    if len(item_keys) == 1:
        _run("delete_item", {"item_key": item_keys[0]})
        return
    _run("delete_items", {"item_keys": item_keys})


@app.command("batch-add", help="Import identifiers from a file, one per line.")
def batch_add(
    file: Path,
    id_type: str = typer.Option("doi", help="Identifier type: doi, isbn, or pmid."),
    collection: str | None = typer.Option(None, help="Collection key."),
    tags: str | None = typer.Option(None, help="Comma-separated tags to add."),
    force: bool = typer.Option(False, help="Skip duplicate checks."),
) -> None:
    with file.open("r", encoding="utf-8") as handle:
        identifiers = [line.strip() for line in handle if line.strip() and not line.lstrip().startswith("#")]
    _run(
        "batch_add_identifiers",
        {
            "identifiers": identifiers,
            "id_type": id_type,
            "collection": collection,
            "tags": tags,
            "force": force,
        },
    )


@app.command("check-pdfs", help="Summarize missing PDF attachments.")
def check_pdfs(collection: str | None = typer.Option(None, help="Collection key filter.")) -> None:
    _run("check_pdfs", {"collection": collection})


@app.command(help="Cross-reference citation text from a file against your library.")
def crossref(file: Path, collection: str | None = typer.Option(None, help="Collection key filter.")) -> None:
    _run("crossref_citations", {"text": file.read_text(encoding="utf-8"), "collection": collection})


@app.command("find-dois", help="Find missing DOIs through CrossRef.")
def find_dois(
    apply: bool = typer.Option(False, help="Write matched DOIs back to Zotero."),
    limit: int | None = typer.Option(None, help="Maximum items to process."),
    collection: str | None = typer.Option(None, help="Collection key filter."),
) -> None:
    _run("find_missing_dois", {"apply": apply, "limit": limit, "collection": collection})


@app.command("fetch-pdfs", help="Find or attach open-access PDFs.")
def fetch_pdfs(
    dry_run: bool = typer.Option(False, help="Show matches without downloading."),
    limit: int | None = typer.Option(None, help="Maximum items to process."),
    collection: str | None = typer.Option(None, help="Collection key filter."),
    download_dir: str | None = typer.Option(None, help="Directory to save PDFs into."),
    upload: bool = typer.Option(False, help="Upload PDFs back into Zotero storage."),
    sources: str | None = typer.Option(None, help="Comma-separated source order."),
) -> None:
    _run(
        "fetch_pdfs",
        {
            "dry_run": dry_run,
            "limit": limit,
            "collection": collection,
            "download_dir": download_dir,
            "upload": upload,
            "sources": _split_csv(sources) or None,
        },
    )


@app.command("rename-pdfs", help="Rename PDF attachment titles from parent item titles.")
def rename_pdfs(
    apply: bool = typer.Option(False, help="Apply changes (default is preview)."),
    collection: str | None = typer.Option(None, help="Restrict to one collection key."),
) -> None:
    _run("rename_pdf_attachments", {"dry_run": not apply, "collection_key": collection})


@app.command("extract-text", help="Extract PDF text to Markdown and attach it as a child attachment.")
def extract_text(
    item_key: str,
    extractor: str = typer.Option(DEFAULT_PDF_EXTRACTOR, help="Markdown extractor backend."),
) -> None:
    _run("extract_and_attach_text", {"item_key": item_key, "extractor": extractor})


@app.command("update-dois", help="Retry DOI lookup for records tagged as missing DOI.")
def update_dois(
    apply: bool = typer.Option(False, help="Write recovered DOIs."),
    limit: int | None = typer.Option(None, help="Maximum items to process."),
) -> None:
    _run("update_missing_dois", {"apply": apply, "limit": limit})


@app.command(help="Low-level JSON bridge for wrappers (plugin/MCP adapters).")
def dispatch(
    tool_name: str,
    args_json: str = typer.Argument("{}", help="JSON object for tool arguments."),
) -> None:
    _run(tool_name, json.loads(args_json))


@stats_app.command(help="Library totals and high-level health metrics.")
def summary() -> None:
    _run("library_summary", {})


@stats_app.command(help="Count items by Zotero item type.")
def types() -> None:
    _run("items_per_type", {})


@stats_app.command(help="Count items by publication year.")
def years() -> None:
    _run("items_per_year", {})


@stats_app.command(help="Show a tag frequency map.")
def tags() -> None:
    _run("tag_cloud", {})


@stats_app.command(help="Summarize attachment coverage.")
def attachments() -> None:
    _run("attachment_summary", {})


@stats_app.command("pdf-status", help="Summarize PDF coverage ratios.")
def pdf_status() -> None:
    _run("pdf_status", {})


@search_app.command("by-title", help="Find items by title text.")
def search_by_title(query: str) -> None:
    _run("search_by_title", {"query": query})


@search_app.command("by-author", help="Find items by creator name.")
def search_by_author(name: str) -> None:
    _run("search_by_author", {"name": name})


@search_app.command("by-year", help="Find items by publication year.")
def search_by_year(year: int) -> None:
    _run("search_by_year", {"year": year})


@search_app.command("by-doi", help="Get one item by DOI.")
def search_by_doi(doi: str) -> None:
    _run("get_item_by_doi", {"doi": doi})


@search_app.command("without-pdf", help="List items without PDF attachments.")
def search_without_pdf() -> None:
    _run("items_without_pdf", {})


@search_app.command("without-tags", help="List items without any tags.")
def search_without_tags() -> None:
    _run("items_without_tags", {})


@search_app.command("not-in-collection", help="List items not assigned to collections.")
def search_not_in_collection() -> None:
    _run("items_not_in_collection", {})


@search_app.command("duplicate-dois", help="Find exact duplicate DOIs.")
def search_duplicate_dois() -> None:
    _run("duplicate_dois", {})


@search_app.command("duplicate-titles", help="Find exact duplicate titles.")
def search_duplicate_titles() -> None:
    _run("duplicate_titles", {})


@search_app.command("fuzzy-duplicate-titles", help="Find near-duplicate titles by similarity score.")
def search_fuzzy_duplicate_titles(threshold: int = typer.Option(85, help="Similarity threshold 0-100.")) -> None:
    _run("find_fuzzy_duplicates_by_title", {"threshold": threshold})


@search_app.command("invalid-dois", help="List items with malformed DOI values.")
def search_invalid_dois() -> None:
    _run("items_with_invalid_doi", {})


@search_app.command("notes", help="Group notes by parent item and extract citation keys.")
def search_notes() -> None:
    _run("find_notes", {})


@collections_app.command(help="List all collections.")
def collections_list() -> None:
    _run("get_collections", {})


@collections_app.command(help="Create a collection.")
def create(name: str, parent: str | None = typer.Option(None, help="Parent collection key.")) -> None:
    _run("create_collection", {"name": name, "parent": parent})


@collections_app.command(help="Move a collection to trash.")
def delete(collection_key: str) -> None:
    _run("delete_collection", {"key": collection_key})


@collections_app.command(help="Rename a collection.")
def rename(collection_key: str, name: str) -> None:
    _run("rename_collection", {"key": collection_key, "name": name})


@collections_app.command("move-item", help="Move an item into a collection.")
def move_item(item_key: str, collection_key: str) -> None:
    _run("move_item_to_collection", {"item_key": item_key, "collection_key": collection_key})


@collections_app.command("add-item", help="Add an item to a collection without removing existing memberships.")
def add_item(item_key: str, collection_key: str) -> None:
    _run("add_item_to_collection", {"item_key": item_key, "collection_key": collection_key})


@collections_app.command(help="Move a collection under a new parent.")
def move(collection_key: str, parent: str | None = typer.Option(None, help="New parent collection key.")) -> None:
    _run("move_collection", {"key": collection_key, "parent": parent})


@tags_app.command(help="List all tags and counts.")
def tags_list() -> None:
    _run("all_tags", {})


@tags_app.command(help="Add tags to one item.")
def add(item_key: str, tags: str) -> None:
    _run("add_tags_to_item", {"item_key": item_key, "tags": _split_csv(tags)})


@tags_app.command(help="Remove tags from one item.")
def remove(item_key: str, tags: str) -> None:
    _run("remove_tags_from_item", {"item_key": item_key, "tags": _split_csv(tags)})


@tags_app.command(help="Rename a tag globally.")
def rename(old_name: str, new_name: str) -> None:
    _run("rename_tag", {"old_name": old_name, "new_name": new_name})


@tags_app.command(help="Merge source tags into a target tag.")
def merge(sources: str, target: str) -> None:
    _run("merge_tags", {"sources": _split_csv(sources), "target": target})


@tags_app.command(help="Delete a tag globally.")
def delete(tag_name: str) -> None:
    _run("delete_tag", {"tag_name": tag_name})


@tags_app.command(help="List currently unused tags.")
def unused() -> None:
    _run("get_unused_tags", {})


@tags_app.command("delete-unused", help="Delete all currently unused tags.")
def delete_unused() -> None:
    _run("delete_unused_tags", {})


@import_app.command("doi", help="Import one DOI.")
def import_doi(doi: str) -> None:
    _run("import_by_doi", {"doi": doi})


@import_app.command("isbn", help="Import one ISBN.")
def import_isbn(isbn: str) -> None:
    _run("import_by_isbn", {"isbn": isbn})


@import_app.command("pmid", help="Import one PMID.")
def import_pmid(pmid: str) -> None:
    _run("import_by_pmid", {"pmid": pmid})


@import_app.command("arxiv", help="Import one arXiv identifier.")
def import_arxiv(arxiv_id: str) -> None:
    _run("import_by_arxiv", {"arxiv_id": arxiv_id})


@export_app.command("json", help="Export library as JSON.")
def export_json(
    collection: str | None = typer.Option(None, help="Collection key."),
    output: str | None = typer.Option(None, help="Output file path."),
) -> None:
    if collection:
        _run("export_collection", {"collection_key": collection, "filepath": output, "format": "json"})
        return
    _run("export_to_json", {"filepath": output})


@export_app.command("bibtex", help="Export library as BibTeX.")
def export_bibtex(
    collection: str | None = typer.Option(None, help="Collection key."),
    output: str | None = typer.Option(None, help="Output file path."),
) -> None:
    if collection:
        _run("export_collection", {"collection_key": collection, "filepath": output, "format": "bibtex"})
        return
    _run("export_to_bibtex", {"filepath": output})


@export_app.command("csv", help="Export library as CSV.")
def export_csv(
    collection: str | None = typer.Option(None, help="Collection key."),
    output: str | None = typer.Option(None, help="Output file path."),
) -> None:
    if collection:
        _run("export_collection", {"collection_key": collection, "filepath": output, "format": "csv"})
        return
    _run("export_to_csv", {"filepath": output})


@export_app.command("ris", help="Export library as RIS.")
def export_ris(
    collection: str | None = typer.Option(None, help="Collection key."),
    output: str | None = typer.Option(None, help="Output file path."),
) -> None:
    _run("export_to_ris", {"collection": collection, "filepath": output})


@export_app.command("csljson", help="Export library as CSL-JSON.")
def export_csljson(
    collection: str | None = typer.Option(None, help="Collection key."),
    output: str | None = typer.Option(None, help="Output file path."),
) -> None:
    _run("export_to_csljson", {"collection": collection, "filepath": output})


@cleanup_app.command(help="Delete HTML snapshots (dry-run by default).")
def snapshots(apply: bool = typer.Option(False, help="Apply changes instead of preview.")) -> None:
    _run("delete_snapshots", {"dry_run": not apply})


@cleanup_app.command(help="Delete notes (dry-run by default).")
def notes(apply: bool = typer.Option(False, help="Apply changes instead of preview.")) -> None:
    _run("delete_all_notes", {"dry_run": not apply})


@cleanup_app.command("missing-pdfs", help="Clean dangling missing-PDF records (dry-run by default).")
def missing_pdfs(
    apply: bool = typer.Option(False, help="Apply changes instead of preview."),
    storage_root: str | None = typer.Option(None, help="Override Zotero storage directory."),
) -> None:
    _run("clean_missing_pdfs", {"dry_run": not apply, "storage_root": storage_root})


@sync_app.command(help="Show sync status summary.")
def status() -> None:
    _run("get_sync_status", {})


@sync_app.command(help="Show timestamp of the last sync.")
def last() -> None:
    _run("get_last_sync", {})


app.add_typer(stats_app, name="stats")
app.add_typer(search_app, name="search")
app.add_typer(collections_app, name="collections")
app.add_typer(tags_app, name="tags")
app.add_typer(import_app, name="import")
app.add_typer(export_app, name="export")
app.add_typer(cleanup_app, name="cleanup")
app.add_typer(sync_app, name="sync")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
