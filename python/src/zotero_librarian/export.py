"""
Export functions for Zotero library items (JSON, CSV, BibTeX).
"""

from pyzotero import zotero

from .client import _all_items


def _paged_formatted_export(
    zot: zotero.Zotero,
    fmt: str,
    collection_key: str = None,
) -> str:
    """Export items through Zotero's local formatted API endpoints."""
    import json

    start = 0
    limit = 100
    total = None

    if fmt == "csljson":
        documents = []
        while total is None or start < total:
            if collection_key:
                chunk = zot.collection_items_top(
                    collection_key,
                    start=start,
                    limit=limit,
                    format=fmt,
                )
            else:
                chunk = zot.top(start=start, limit=limit, format=fmt)

            text = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
            if text.strip():
                documents.extend(json.loads(text))

            headers = getattr(zot.request, "headers", {})
            total = int(headers.get("Total-Results", len(documents)))
            start += limit

            if len(documents) >= total:
                break

        return json.dumps(documents, indent=2, ensure_ascii=False)

    chunks = []
    while total is None or start < total:
        if collection_key:
            chunk = zot.collection_items_top(
                collection_key,
                start=start,
                limit=limit,
                format=fmt,
            )
        else:
            chunk = zot.top(start=start, limit=limit, format=fmt)

        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
        if text.strip():
            chunks.append(text)

        headers = getattr(zot.request, "headers", {})
        total = int(headers.get("Total-Results", len(chunks) * limit))
        start += limit

        if start >= total:
            break

    return "\n".join(chunks)


def export_to_json(zot: zotero.Zotero, items: list[dict] = None, filepath: str = None) -> str | None:
    """Export library items to JSON file.

    Exports complete item data including all fields, relations, and metadata.
    If no items provided, exports entire library.

    Args:
        zot: Zotero client
        items: Optional list of items to export. If None, exports all items
        filepath: Optional file path to write JSON. If None, returns JSON string

    Returns:
        JSON string if filepath is None, otherwise None (writes to file)
    """
    if items is None:
        items = list(_all_items(zot))

    # Convert to serializable format (ensure all data is included)
    export_data = []
    for item in items:
        # Create a clean copy with all relevant data
        item_export = {
            "key": item.get("key", ""),
            "version": item.get("version", 0),
            "data": item.get("data", {}),
            "relations": item.get("relations", {}),
        }
        # Include children if available (from cached library)
        if "_children" in item:
            item_export["_children"] = [
                {
                    "key": child.get("key", ""),
                    "version": child.get("version", 0),
                    "data": child.get("data", {}),
                }
                for child in item["_children"]
            ]
        export_data.append(item_export)

    import json
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False)

    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)
        return None
    return json_str


def export_to_csv(
    zot: zotero.Zotero,
    items: list[dict] = None,
    filepath: str = None,
    fields: list[str] = None
) -> str | None:
    """Export library items to CSV format.

    Exports selected fields for each item. If no fields specified, exports
    common bibliographic fields. If no items provided, exports entire library.

    Args:
        zot: Zotero client
        items: Optional list of items to export. If None, exports all items
        filepath: Optional file path to write CSV. If None, returns CSV string
        fields: Optional list of field names to export. Defaults to common fields.

    Returns:
        CSV string if filepath is None, otherwise None (writes to file)
    """
    if items is None:
        items = list(_all_items(zot))

    if fields is None:
        fields = [
            "title",
            "creator",
            "date",
            "itemType",
            "publicationTitle",
            "DOI",
            "url",
            "abstractNote",
            "tags",
        ]

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Write header
    writer.writerow(fields)

    # Write data rows
    for item in items:
        data = item.get("data", {})
        row = []
        for field in fields:
            value = data.get(field, "")
            # Handle creators specially - format as "LastName, FirstName"
            if field == "creator" and isinstance(value, list):
                creators = []
                for c in value:
                    first = c.get("firstName", "")
                    last = c.get("lastName", "")
                    if last and first:
                        creators.append(f"{last}, {first}")
                    elif last:
                        creators.append(last)
                    elif first:
                        creators.append(first)
                value = "; ".join(creators)
            # Handle tags - format as semicolon-separated list
            elif field == "tags" and isinstance(value, list):
                value = "; ".join(t.get("tag", "") for t in value if t.get("tag"))
            # Ensure value is string
            if value is None:
                value = ""
            elif not isinstance(value, str):
                value = str(value)
            row.append(value)
        writer.writerow(row)

    csv_str = output.getvalue()

    if filepath:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(csv_str)
        return None
    return csv_str


def export_to_bibtex(zot: zotero.Zotero, items: list[dict] = None, filepath: str = None) -> str | None:
    """Export library items to BibTeX format.

    Converts Zotero items to BibTeX entries. Supports common item types
    (journalArticle, book, incollection, conference, thesis, etc.).
    If no items provided, exports entire library.

    Args:
        zot: Zotero client
        items: Optional list of items to export. If None, exports all items
        filepath: Optional file path to write BibTeX. If None, returns BibTeX string

    Returns:
        BibTeX string if filepath is None, otherwise None (writes to file)
    """
    if items is None:
        items = list(_all_items(zot))

    def _format_bibtex_value(value: str) -> str:
        """Escape special characters for BibTeX."""
        if not value:
            return ""
        # Protect capitalization with braces
        value = str(value)
        return value

    def _get_bibtex_type(item_type: str) -> str:
        """Map Zotero item type to BibTeX type."""
        type_map = {
            "journalArticle": "article",
            "book": "book",
            "bookSection": "incollection",
            "conferencePaper": "inproceedings",
            "thesis": "phdthesis",
            "report": "techreport",
            "magazineArticle": "article",
            "newspaperArticle": "article",
            "webpage": "misc",
            "document": "misc",
            "manuscript": "unpublished",
            "preprint": "unpublished",
        }
        return type_map.get(item_type, "misc")

    def _format_creators(creators: list[dict]) -> str:
        """Format creators as BibTeX author string."""
        if not creators:
            return ""
        authors = []
        for c in creators:
            if c.get("creatorType") == "author":
                first = c.get("firstName", "")
                last = c.get("lastName", "")
                if last and first:
                    authors.append(f"{last}, {first}")
                elif last:
                    authors.append(last)
        return " and ".join(authors)

    bibtex_entries = []

    for item in items:
        data = item.get("data", {})
        item_type = data.get("itemType", "")
        bibtex_type = _get_bibtex_type(item_type)

        # Use item key as citation key, or generate from title/year
        cite_key = item.get("key", "")
        if not cite_key:
            continue

        # Build BibTeX fields
        fields = []

        # Author
        creators = data.get("creators", [])
        authors = _format_creators(creators)
        if authors:
            fields.append(f"  author = {{{authors}}}")

        # Title
        title = data.get("title", "")
        if title:
            fields.append(f"  title = {{{title}}}")

        # Journal/Publication
        pub_title = data.get("publicationTitle", "")
        if pub_title:
            fields.append(f"  journal = {{{pub_title}}}")

        # Year and Date
        date = data.get("date", "")
        if date:
            year = date[:4] if len(date) >= 4 else date
            fields.append(f"  year = {{{year}}}")

        # Volume
        volume = data.get("volume", "")
        if volume:
            fields.append(f"  volume = {{{volume}}}")

        # Issue/Number
        issue = data.get("issue", "")
        if issue:
            fields.append(f"  number = {{{issue}}}")

        # Pages
        pages = data.get("pages", "")
        if pages:
            fields.append(f"  pages = {{{pages}}}")

        # Publisher
        publisher = data.get("publisher", "")
        if publisher:
            fields.append(f"  publisher = {{{publisher}}}")

        # Address/Place
        place = data.get("place", "")
        if place:
            fields.append(f"  address = {{{place}}}")

        # DOI
        doi = data.get("DOI", "")
        if doi:
            fields.append(f"  doi = {{{doi}}}")

        # URL
        url = data.get("url", "")
        if url:
            fields.append(f"  url = {{{url}}}")

        # Abstract
        abstract = data.get("abstractNote", "")
        if abstract:
            # Escape curly braces in abstract
            abstract = abstract.replace("{", "\\{").replace("}", "\\}")
            fields.append(f"  abstract = {{{abstract}}}")

        # Type (for reports, thesis, etc.)
        if data.get("thesisType"):
            fields.append(f"  type = {{{data.get('thesisType')}}}")
        elif data.get("reportType"):
            fields.append(f"  type = {{{data.get('reportType')}}}")

        # ISBN
        isbn = data.get("ISBN", "")
        if isbn:
            fields.append(f"  isbn = {{{isbn}}}")

        # ISSN
        issn = data.get("ISSN", "")
        if issn:
            fields.append(f"  issn = {{{issn}}}")

        # Series
        series = data.get("series", "")
        if series:
            fields.append(f"  series = {{{series}}}")

        # Edition
        edition = data.get("edition", "")
        if edition:
            fields.append(f"  edition = {{{edition}}}")

        # Tags as keywords
        tags = data.get("tags", [])
        if tags:
            keywords = ", ".join(t.get("tag", "") for t in tags if t.get("tag"))
            if keywords:
                fields.append(f"  keywords = {{{keywords}}}")

        # Notes (first note only, as comment)
        notes = item.get("_children", [])
        notes = [c for c in notes if c.get("data", {}).get("itemType") == "note"]
        if notes:
            note_text = notes[0].get("data", {}).get("note", "")
            if note_text:
                # Strip HTML tags for plain text
                import re
                note_text = re.sub(r"<[^>]+>", "", note_text)
                note_text = note_text.replace("{", "\\{").replace("}", "\\}")
                fields.append(f"  annote = {{{note_text}}}")

        # Build entry
        entry_lines = [f" @{bibtex_type}{{{cite_key},"]
        entry_lines.append(",\n".join(fields))
        entry_lines.append("}")
        bibtex_entries.append("\n".join(entry_lines))

    bibtex_str = "\n\n".join(bibtex_entries)
    if bibtex_str:
        bibtex_str += "\n"

    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(bibtex_str)
        return None
    return bibtex_str


def export_collection(
    zot: zotero.Zotero,
    collection_key: str,
    filepath: str = None,
    format: str = "json"
) -> str | None:
    """Export a specific collection to file.

    Exports all items in a collection in the specified format.
    Supports json, csv, and bibtex formats.

    Args:
        zot: Zotero client
        collection_key: Key of the collection to export
        filepath: Optional file path to write output. If None, returns string
        format: Export format: "json", "csv", or "bibtex". Default is "json"

    Returns:
        Formatted string if filepath is None, otherwise None (writes to file)

    Raises:
        ValueError: If format is not one of "json", "csv", or "bibtex"
    """
    # Get collection items
    items = list(_all_items(zot, collection=collection_key))

    if format.lower() == "json":
        return export_to_json(zot, items=items, filepath=filepath)
    elif format.lower() == "csv":
        return export_to_csv(zot, items=items, filepath=filepath)
    elif format.lower() == "bibtex":
        return export_to_bibtex(zot, items=items, filepath=filepath)
    else:
        raise ValueError(f"Unknown format: {format}. Supported: json, csv, bibtex")


def export_to_ris(zot: zotero.Zotero, collection_key: str = None, filepath: str = None) -> str | None:
    """Export library items to RIS using the local Zotero API formatter."""
    ris_str = _paged_formatted_export(zot, "ris", collection_key=collection_key)
    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ris_str)
        return None
    return ris_str


def export_to_csljson(
    zot: zotero.Zotero,
    collection_key: str = None,
    filepath: str = None,
) -> str | None:
    """Export library items to CSL-JSON using the local Zotero API formatter."""
    csljson_str = _paged_formatted_export(zot, "csljson", collection_key=collection_key)
    if filepath:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(csljson_str)
        return None
    return csljson_str
