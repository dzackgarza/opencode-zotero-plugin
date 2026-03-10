"""Human-friendly CLI for Zotero Librarian."""

import argparse
import json
import sys
from typing import Any

from .client import get_zotero


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def _zot():
    return get_zotero()


def cmd_count(_args) -> None:
    from .client import count_items

    print(count_items(_zot()))


def cmd_stats(args) -> None:
    from .stats import attachment_summary, items_per_type, items_per_year, library_summary, pdf_status, tag_cloud

    zot = _zot()
    if args.action == "summary":
        _print(library_summary(zot))
    elif args.action == "types":
        _print(items_per_type(zot))
    elif args.action == "years":
        _print(items_per_year(zot))
    elif args.action == "tags":
        _print(tag_cloud(zot))
    elif args.action == "attachments":
        _print(attachment_summary(zot))
    elif args.action == "pdf-status":
        _print(pdf_status(zot))


def cmd_search(args) -> None:
    from .duplicates import duplicate_dois, duplicate_titles, find_fuzzy_duplicates_by_title
    from .query import (
        find_notes,
        get_item_by_doi,
        items_not_in_collection,
        items_without_pdf,
        items_without_tags,
        search_by_author,
        search_by_title,
        search_by_year,
    )
    from .validation import items_with_invalid_doi

    zot = _zot()
    if args.action == "by-title":
        _print(search_by_title(zot, args.query))
    elif args.action == "by-author":
        _print(search_by_author(zot, args.query))
    elif args.action == "by-year":
        try:
            year = int(args.query)
        except (TypeError, ValueError):
            build_parser().error(f"'by-year' requires a numeric year, got: {args.query!r}")
        _print(search_by_year(zot, year))
    elif args.action == "by-doi":
        _print(get_item_by_doi(zot, args.query))
    elif args.action == "without-pdf":
        _print(items_without_pdf(zot))
    elif args.action == "without-tags":
        _print(list(items_without_tags(zot)))
    elif args.action == "not-in-collection":
        _print(list(items_not_in_collection(zot)))
    elif args.action == "duplicate-dois":
        _print(duplicate_dois(zot))
    elif args.action == "duplicate-titles":
        _print(duplicate_titles(zot))
    elif args.action == "fuzzy-duplicate-titles":
        if args.query:
            try:
                threshold = int(args.query)
            except ValueError:
                build_parser().error(f"'fuzzy-duplicate-titles' threshold must be an integer, got: {args.query!r}")
        else:
            threshold = 85
        _print(find_fuzzy_duplicates_by_title(zot, threshold=threshold))
    elif args.action == "invalid-dois":
        _print(list(items_with_invalid_doi(zot)))
    elif args.action == "notes":
        _print(find_notes(zot))


def cmd_get(args) -> None:
    from .query import get_item

    _print(get_item(_zot(), args.key))


def cmd_children(args) -> None:
    from .query import get_children

    _print(get_children(_zot(), args.key))


def cmd_collections(args) -> None:
    from .collections import create_collection, delete_collection, move_collection, rename_collection
    from .items import add_item_to_collection, move_item_to_collection
    from .query import get_collections

    zot = _zot()
    if args.action == "list":
        _print(get_collections(zot))
    elif args.action == "create":
        _print(create_collection(zot, args.name, args.parent))
    elif args.action == "delete":
        _print(delete_collection(zot, args.key))
    elif args.action == "rename":
        _print(rename_collection(zot, args.key, args.name))
    elif args.action == "move-item":
        _print(move_item_to_collection(zot, args.item_key, args.collection_key))
    elif args.action == "add-item":
        _print(add_item_to_collection(zot, args.item_key, args.collection_key))
    elif args.action == "move":
        _print(move_collection(zot, args.key, args.parent))


def cmd_tags(args) -> None:
    from .items import add_tags_to_item, remove_tags_from_item
    from .query import all_tags
    from .tags import delete_tag, delete_unused_tags, get_unused_tags, merge_tags, rename_tag

    zot = _zot()
    if args.action == "list":
        _print(all_tags(zot))
    elif args.action == "add":
        _print(add_tags_to_item(zot, args.item_key, args.tags.split(",")))
    elif args.action == "remove":
        _print(remove_tags_from_item(zot, args.item_key, args.tags.split(",")))
    elif args.action == "rename":
        _print(rename_tag(zot, args.old_name, args.new_name))
    elif args.action == "merge":
        _print(merge_tags(zot, args.sources.split(","), args.target))
    elif args.action == "delete":
        _print(delete_tag(zot, args.tag_name))
    elif args.action == "unused":
        _print(get_unused_tags(zot))
    elif args.action == "delete-unused":
        _print(delete_unused_tags(zot))


def cmd_import(args) -> None:
    from .import_ import import_by_arxiv, import_by_doi, import_by_isbn, import_by_pmid

    zot = _zot()
    if args.action == "doi":
        _print(import_by_doi(zot, args.identifier))
    elif args.action == "isbn":
        _print(import_by_isbn(zot, args.identifier))
    elif args.action == "pmid":
        _print(import_by_pmid(zot, args.identifier))
    elif args.action == "arxiv":
        _print(import_by_arxiv(zot, args.identifier))


def cmd_batch_add(args) -> None:
    from .enrichment import batch_add_identifiers

    with open(args.file, "r", encoding="utf-8") as handle:
        identifiers = [
            line.strip()
            for line in handle
            if line.strip() and not line.lstrip().startswith("#")
        ]

    _print(
        batch_add_identifiers(
            _zot(),
            identifiers=identifiers,
            id_type=args.id_type,
            collection=args.collection,
            tags=args.tags,
            force=args.force,
        )
    )


def cmd_export(args) -> None:
    from .export import export_collection, export_to_bibtex, export_to_csljson, export_to_csv, export_to_json, export_to_ris

    zot = _zot()
    filepath = args.output
    if args.collection and args.action in {"json", "csv", "bibtex"}:
        result = export_collection(zot, args.collection, filepath=filepath, format=args.action)
    elif args.action == "json":
        result = export_to_json(zot, filepath=filepath)
    elif args.action == "bibtex":
        result = export_to_bibtex(zot, filepath=filepath)
    elif args.action == "csv":
        result = export_to_csv(zot, filepath=filepath)
    elif args.action == "ris":
        result = export_to_ris(zot, collection_key=args.collection, filepath=filepath)
    elif args.action == "csljson":
        result = export_to_csljson(zot, collection_key=args.collection, filepath=filepath)
    else:
        raise ValueError(f"Unknown export action: {args.action}")

    if result:
        print(result)


def cmd_update(args) -> None:
    from .items import update_item_fields

    _print(update_item_fields(_zot(), args.key, json.loads(args.fields_json)))


def cmd_delete(args) -> None:
    from .batch import batch_delete_items
    from .items import delete_item

    zot = _zot()
    if len(args.keys) == 1:
        _print(delete_item(zot, args.keys[0]))
    else:
        _print(batch_delete_items(zot, args.keys))


def cmd_check_pdfs(_args) -> None:
    from .enrichment import check_pdfs

    _print(check_pdfs(_zot(), collection=_args.collection))


def cmd_crossref(args) -> None:
    from .enrichment import crossref_citations

    with open(args.file, "r", encoding="utf-8") as handle:
        _print(crossref_citations(_zot(), handle.read(), collection=args.collection))


def cmd_find_dois(args) -> None:
    from .enrichment import find_missing_dois

    _print(
        find_missing_dois(
            _zot(),
            apply=args.apply,
            limit=args.limit,
            collection=args.collection,
        )
    )


def cmd_fetch_pdfs(args) -> None:
    from .enrichment import fetch_pdfs

    sources = [entry.strip() for entry in args.sources.split(",")] if args.sources else None
    _print(
        fetch_pdfs(
            _zot(),
            dry_run=args.dry_run,
            limit=args.limit,
            collection=args.collection,
            download_dir=args.download_dir,
            upload=args.upload,
            sources=sources,
        )
    )


def cmd_cleanup(args) -> None:
    from .cleanup import clean_missing_pdfs, delete_all_notes, delete_snapshots

    zot = _zot()
    dry_run = not args.apply
    if args.action == "snapshots":
        _print(delete_snapshots(zot, dry_run=dry_run))
    elif args.action == "notes":
        _print(delete_all_notes(zot, dry_run=dry_run))
    elif args.action == "missing-pdfs":
        _print(clean_missing_pdfs(zot, dry_run=dry_run, storage_root=args.storage_root))


def cmd_rename_pdfs(args) -> None:
    from .attachments import rename_pdf_attachments

    _print(
        rename_pdf_attachments(
            _zot(),
            dry_run=not args.apply,
            collection_key=args.collection,
        )
    )


def cmd_extract_text(args) -> None:
    from .attachments import extract_and_attach_text

    _print(extract_and_attach_text(_zot(), args.item_key))


def cmd_update_dois(args) -> None:
    from .enrichment import update_missing_dois

    _print(
        update_missing_dois(
            _zot(),
            apply=args.apply,
            limit=args.limit,
        )
    )


def cmd_sync(args) -> None:
    from .sync import get_last_sync, get_sync_status

    zot = _zot()
    if args.action == "status":
        _print(get_sync_status(zot))
    elif args.action == "last":
        _print(get_last_sync(zot))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zotero-lib", description="Zotero library management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("count", help="Get total item count")

    stats = sub.add_parser("stats", help="Library statistics")
    stats.add_argument("action", choices=["summary", "types", "years", "tags", "attachments", "pdf-status"])

    search = sub.add_parser("search", help="Search and filter items")
    search.add_argument(
        "action",
        choices=[
            "by-title",
            "by-author",
            "by-year",
            "by-doi",
            "without-pdf",
            "without-tags",
            "not-in-collection",
            "duplicate-dois",
            "duplicate-titles",
            "fuzzy-duplicate-titles",
            "invalid-dois",
            "notes",
        ],
    )
    search.add_argument("query", nargs="?", help="Search query (for fuzzy-duplicate-titles: similarity threshold 0-100)")

    get = sub.add_parser("get", help="Get a single item by key")
    get.add_argument("key", help="Item key")

    children = sub.add_parser("children", help="Get child items for a parent item")
    children.add_argument("key", help="Parent item key")

    update = sub.add_parser("update", help="Update item fields from JSON")
    update.add_argument("key", help="Item key")
    update.add_argument("fields_json", help='Fields as JSON, e.g. \'{"title": "New Title"}\'')

    delete = sub.add_parser("delete", help="Move one or more items to trash")
    delete.add_argument("keys", nargs="+", help="Item key(s)")

    collections = sub.add_parser("collections", help="Collection management")
    collections.add_argument("action", choices=["list", "create", "delete", "rename", "move-item", "add-item", "move"])
    collections.add_argument("--key", help="Collection key")
    collections.add_argument("--name", help="Collection name")
    collections.add_argument("--parent", help="Parent collection key")
    collections.add_argument("--item-key", help="Item key")
    collections.add_argument("--collection-key", help="Target collection key")

    tags = sub.add_parser("tags", help="Tag management")
    tags.add_argument("action", choices=["list", "add", "remove", "rename", "merge", "delete", "unused", "delete-unused"])
    tags.add_argument("--item-key", help="Item key")
    tags.add_argument("--tags", help="Comma-separated tags")
    tags.add_argument("--old-name", help="Old tag name")
    tags.add_argument("--new-name", help="New tag name")
    tags.add_argument("--sources", help="Comma-separated source tags")
    tags.add_argument("--target", help="Target tag")
    tags.add_argument("--tag-name", help="Tag name")

    imports = sub.add_parser("import", help="Import items")
    imports.add_argument("action", choices=["doi", "isbn", "pmid", "arxiv"])
    imports.add_argument("identifier", help="Identifier to import")

    batch_add = sub.add_parser("batch-add", help="Import many identifiers from a file")
    batch_add.add_argument("file", help="File with one identifier per line")
    batch_add.add_argument("--id-type", default="doi", choices=["doi", "isbn", "pmid"])
    batch_add.add_argument("--collection", help="Collection key")
    batch_add.add_argument("--tags", help="Comma-separated tags")
    batch_add.add_argument("--force", action="store_true", help="Skip duplicate detection")

    export = sub.add_parser("export", help="Export library data")
    export.add_argument("action", choices=["json", "bibtex", "csv", "ris", "csljson"])
    export.add_argument("--collection", help="Collection key")
    export.add_argument("--output", "-o", help="Output file path")

    check_pdfs = sub.add_parser("check-pdfs", help="Summarize missing PDF attachments")
    check_pdfs.add_argument("--collection", help="Collection key")

    crossref = sub.add_parser("crossref", help="Cross-reference citation text against the library")
    crossref.add_argument("file", help="Text or markdown file")
    crossref.add_argument("--collection", help="Collection key")

    find_dois = sub.add_parser("find-dois", help="Find missing DOIs via CrossRef")
    find_dois.add_argument("--apply", action="store_true", help="Write matched DOIs back to Zotero")
    find_dois.add_argument("--limit", type=int, default=None, help="Maximum items to process")
    find_dois.add_argument("--collection", help="Collection key")

    fetch_pdfs = sub.add_parser("fetch-pdfs", help="Fetch open-access PDFs for items")
    fetch_pdfs.add_argument("--dry-run", action="store_true", help="Show matches without downloading")
    fetch_pdfs.add_argument("--limit", type=int, default=None, help="Maximum items to process")
    fetch_pdfs.add_argument("--collection", help="Collection key")
    fetch_pdfs.add_argument("--download-dir", help="Directory to save PDFs into")
    fetch_pdfs.add_argument("--upload", action="store_true", help="Upload PDFs to Zotero storage")
    fetch_pdfs.add_argument("--sources", help="Comma-separated PDF sources to try")

    cleanup = sub.add_parser("cleanup", help="Cleanup: snapshots, notes, or dangling PDF records")
    cleanup.add_argument("action", choices=["snapshots", "notes", "missing-pdfs"])
    cleanup.add_argument("--apply", action="store_true", help="Actually trash items (default: dry-run)")
    cleanup.add_argument("--storage-root", default=None, help="Override Zotero storage path (for missing-pdfs)")

    rename_pdfs = sub.add_parser("rename-pdfs", help="Rename PDF attachment titles from parent item title")
    rename_pdfs.add_argument("--apply", action="store_true", help="Actually write renames (default: dry-run)")
    rename_pdfs.add_argument("--collection", default=None, help="Restrict to a collection key")

    extract_text = sub.add_parser("extract-text", help="Extract PDF text and attach as .txt")
    extract_text.add_argument("item_key", help="Parent item key")

    update_dois = sub.add_parser("update-dois", help="Recover DOIs for items tagged '⛔ No DOI found'")
    update_dois.add_argument("--apply", action="store_true", help="Write recovered DOIs back to Zotero")
    update_dois.add_argument("--limit", type=int, default=None, help="Maximum items to process")

    sync = sub.add_parser("sync", help="Sync status")
    sync.add_argument("action", choices=["status", "last"])

    return parser


def main() -> None:
    args = build_parser().parse_args()

    handlers = {
        "count": cmd_count,
        "stats": cmd_stats,
        "search": cmd_search,
        "get": cmd_get,
        "children": cmd_children,
        "update": cmd_update,
        "delete": cmd_delete,
        "collections": cmd_collections,
        "tags": cmd_tags,
        "import": cmd_import,
        "batch-add": cmd_batch_add,
        "export": cmd_export,
        "check-pdfs": cmd_check_pdfs,
        "crossref": cmd_crossref,
        "find-dois": cmd_find_dois,
        "fetch-pdfs": cmd_fetch_pdfs,
        "cleanup": cmd_cleanup,
        "rename-pdfs": cmd_rename_pdfs,
        "extract-text": cmd_extract_text,
        "update-dois": cmd_update_dois,
        "sync": cmd_sync,
    }

    try:
        handlers[args.command](args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
