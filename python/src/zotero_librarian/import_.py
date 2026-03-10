"""Import functions for adding items to Zotero library from external sources."""

from __future__ import annotations

from typing import Any

import httpx
from pyzotero import zotero

from .connector import ConnectorWriteError, error_result, import_text, local_write, result_from_exception, save_item
from .validation import validate_doi


def _import_success(
    operation: str,
    item_key: str,
    *,
    details: dict[str, Any] | None = None,
    warning: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "success": True,
        "operation": operation,
        "stage": "completed",
        "item_key": item_key,
        "details": details or {},
    }
    if warning:
        result["warning"] = warning
    return result


def _normalize_tags(tags: list[str] | None) -> list[str] | None:
    cleaned = [tag.strip() for tag in tags or [] if tag and tag.strip()]
    return cleaned or None


def _append_extra_lines(item: dict[str, Any], extra_lines: list[str] | None) -> None:
    if not extra_lines:
        return
    lines = [line.strip() for line in extra_lines if line and line.strip()]
    if not lines:
        return
    existing_extra = item.get("extra", "").strip()
    combined = [existing_extra] if existing_extra else []
    combined.extend(lines)
    item["extra"] = "\n".join(combined)


def import_by_doi(
    zot: zotero.Zotero,
    doi: str,
    *,
    collection: str | None = None,
    tags: list[str] | None = None,
    extra_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch item metadata from CrossRef by DOI and create Zotero item.

    Uses the CrossRef API to retrieve bibliographic metadata for a DOI
    and creates a new item in Zotero with the fetched data.

    Args:
        zot: Zotero client
        doi: Digital Object Identifier (DOI) to fetch metadata for

    Returns:
        The key of the created item, or None if the API request failed
    """
    if not validate_doi(doi):
        return error_result(
            "import_by_doi",
            "doi_validation",
            f"Invalid DOI format: {doi!r}. Expected pattern: 10.XXXX/...",
            details={"doi": doi},
        )

    url = f"https://api.crossref.org/works/{doi}"

    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code == 404:
            return error_result(
                "import_by_doi",
                "crossref_lookup",
                f"CrossRef did not find DOI {doi}",
                details={"doi": doi, "status_code": response.status_code},
            )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "ok" or "message" not in data:
            return error_result(
                "import_by_doi",
                "crossref_response",
                f"CrossRef returned an unexpected payload for DOI {doi}",
                details={"doi": doi, "payload_keys": sorted(data.keys())},
            )

        work = data["message"]
        item_type = work.get("type", "")

        # Map CrossRef types to Zotero item types
        type_mapping = {
            "journal-article": "journalArticle",
            "journal-issue": "journalArticle",
            "book": "book",
            "book-chapter": "bookSection",
            "book-part": "bookSection",
            "book-section": "bookSection",
            "proceedings-article": "conferencePaper",
            "proceedings": "conferencePaper",
            "dissertation": "thesis",
            "thesis": "thesis",
            "report": "report",
            "report-series": "report",
            "dataset": "document",
            "component": "document",
            "entry": "document",
            "reference-entry": "document",
        }
        zotero_type = type_mapping.get(item_type, "journalArticle")

        # Build Zotero item
        item = {
            "itemType": zotero_type,
            "title": work.get("title", [""])[0] if work.get("title") else "",
            "DOI": doi,
        }

        # Add authors/creators
        creators = []
        for author in work.get("author", []):
            creator = {"creatorType": "author"}
            if "given" in author:
                creator["firstName"] = author["given"]
            if "family" in author:
                creator["lastName"] = author["family"]
            if creator.get("firstName") or creator.get("lastName"):
                creators.append(creator)
        if creators:
            item["creators"] = creators

        # Add publication date
        if "published-print" in work:
            pub_date = work["published-print"]
        elif "published-online" in work:
            pub_date = work["published-online"]
        elif "created" in work:
            pub_date = work["created"]
        else:
            pub_date = None

        if pub_date and "date-parts" in pub_date:
            date_parts = pub_date["date-parts"][0]
            if len(date_parts) >= 1:
                year = str(date_parts[0])
                if len(date_parts) >= 2:
                    month = str(date_parts[1]).zfill(2)
                    if len(date_parts) >= 3:
                        day = str(date_parts[2]).zfill(2)
                        item["date"] = f"{year}-{month}-{day}"
                    else:
                        item["date"] = f"{year}-{month}"
                else:
                    item["date"] = year

        # Add journal/publication title
        if "container-title" in work and work["container-title"]:
            item["publicationTitle"] = work["container-title"][0]

        # Add volume, issue, pages
        if "volume" in work:
            item["volume"] = str(work["volume"])
        if "issue" in work:
            item["issue"] = str(work["issue"])
        if "page" in work:
            item["pages"] = work["page"]

        # Add publisher for books/reports
        if "publisher" in work:
            item["publisher"] = work["publisher"]

        # Add ISBN for books
        if "ISBN" in work and work["ISBN"]:
            item["ISBN"] = work["ISBN"][0]

        # Add ISSN for journals
        if "ISSN" in work and work["ISSN"]:
            item["ISSN"] = work["ISSN"][0]

        # Add abstract
        if "abstract" in work:
            item["abstractNote"] = work["abstract"]

        # Add URL
        if "URL" in work:
            item["url"] = work["URL"]
        elif "link" in work and work["link"]:
            for link in work["link"]:
                if link.get("content-type") == "text/html":
                    item["url"] = link["URL"]
                    break

        _append_extra_lines(item, extra_lines)
        result = save_item(
            zot,
            item,
            uri=item.get("url") or work.get("URL") or f"https://doi.org/{doi}",
            collection_key=collection,
            tags=_normalize_tags(tags),
            operation="import_by_doi",
        )
        return _import_success("import_by_doi", result["item_key"], details={"doi": doi})
    except Exception as exc:
        return result_from_exception("import_by_doi", exc)


def import_by_isbn(
    zot: zotero.Zotero,
    isbn: str,
    *,
    collection: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch item metadata by ISBN using Open Library API and create Zotero item.

    Uses the Open Library API to retrieve bibliographic metadata for an ISBN
    and creates a new item in Zotero with the fetched data.

    Args:
        zot: Zotero client
        isbn: International Standard Book Number (ISBN-10 or ISBN-13)

    Returns:
        The key of the created item, or None if the API request failed
    """
    # Clean ISBN (remove hyphens and spaces)
    clean_isbn = isbn.replace("-", "").replace(" ", "")

    url = f"https://openlibrary.org/isbn/{clean_isbn}.json"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        if not data or "error" in data:
            return error_result(
                "import_by_isbn",
                "openlibrary_lookup",
                f"Open Library did not return metadata for ISBN {clean_isbn}",
                details={"isbn": clean_isbn},
            )

        # Build Zotero book item
        item = {
            "itemType": "book",
            "ISBN": clean_isbn,
        }

        # Add title
        if "title" in data:
            item["title"] = data["title"]

        author_lookup_failures: list[str] = []
        # Add authors/creators
        creators = []
        for author_key in data.get("authors", []):
            if isinstance(author_key, dict):
                author_key = author_key.get("key", "")
            if author_key:
                # Fetch author details
                author_url = f"https://openlibrary.org{author_key}.json"
                try:
                    author_resp = httpx.get(author_url, timeout=5.0)
                    author_resp.raise_for_status()
                    author_data = author_resp.json()
                    creator = {"creatorType": "author"}
                    if "name" in author_data:
                        name = author_data["name"]
                        # Try to split into first/last name
                        parts = name.split(" ", 1)
                        if len(parts) == 2:
                            creator["firstName"] = parts[0]
                            creator["lastName"] = parts[1]
                        else:
                            creator["lastName"] = name
                        creators.append(creator)
                except httpx.HTTPError:
                    author_lookup_failures.append(str(author_key))

        # If no authors from API, try alternate_names or direct name
        if not creators and "authors" in data:
            for author_info in data["authors"]:
                if isinstance(author_info, dict) and "name" in author_info:
                    creator = {"creatorType": "author"}
                    name = author_info["name"]
                    parts = name.split(" ", 1)
                    if len(parts) == 2:
                        creator["firstName"] = parts[0]
                        creator["lastName"] = parts[1]
                    else:
                        creator["lastName"] = name
                    creators.append(creator)

        if creators:
            item["creators"] = creators

        # Add publication date
        if "publish_date" in data:
            date_str = data["publish_date"]
            # Try to extract year
            import re
            year_match = re.search(r"\b(\d{4})\b", date_str)
            if year_match:
                item["date"] = year_match.group(1)

        # Add publisher
        if "publishers" in data and data["publishers"]:
            publishers = data["publishers"]
            if isinstance(publishers, list):
                item["publisher"] = publishers[0]
            else:
                item["publisher"] = publishers

        # Add language
        if "languages" in data and data["languages"]:
            langs = data["languages"]
            if isinstance(langs, list) and langs:
                lang = langs[0]
                if isinstance(lang, dict):
                    lang = lang.get("key", "").split("/")[-1]
                item["language"] = lang

        # Add subjects as tags
        if "subjects" in data and data["subjects"]:
            subject_tags = [{"tag": str(s)} for s in data["subjects"][:10]]  # Limit to 10 tags
            if subject_tags:
                item["tags"] = subject_tags

        result = save_item(
            zot,
            item,
            uri=url,
            collection_key=collection,
            tags=_normalize_tags(tags),
            operation="import_by_isbn",
        )
        warning = None
        if author_lookup_failures:
            warning = f"Skipped {len(author_lookup_failures)} Open Library author lookups"
        return _import_success(
            "import_by_isbn",
            result["item_key"],
            details={"isbn": clean_isbn},
            warning=warning,
        )
    except httpx.HTTPError as exc:
        return error_result(
            "import_by_isbn",
            "openlibrary_lookup",
            f"Open Library lookup failed for ISBN {clean_isbn}",
            details={"isbn": clean_isbn, "exception_type": type(exc).__name__},
        )
    except Exception as exc:
        return result_from_exception("import_by_isbn", exc)


def import_by_pmid(
    zot: zotero.Zotero,
    pmid: str,
    *,
    collection: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch item metadata from PubMed and create a Zotero item.

    Prefers DOI import when PubMed provides one, and falls back to building
    a journal article item directly from the PubMed summary record.
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    try:
        response = httpx.get(
            url,
            params={"db": "pubmed", "id": pmid, "retmode": "json"},
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()

        summary = payload.get("result", {}).get(str(pmid))
        if not summary:
            return error_result(
                "import_by_pmid",
                "pubmed_lookup",
                f"PubMed did not return a summary for PMID {pmid}",
                details={"pmid": pmid},
            )

        article_ids = {
            article_id.get("idtype"): article_id.get("value", "")
            for article_id in summary.get("articleids", [])
        }
        doi = article_ids.get("doi", "").strip()
        if doi:
            doi_result = import_by_doi(
                zot,
                doi,
                collection=collection,
                tags=tags,
                extra_lines=[f"PMID: {pmid}"],
            )
            if doi_result["success"] or not doi_result["stage"].startswith("crossref_"):
                doi_result.setdefault("details", {})
                doi_result["details"]["pmid"] = pmid
                return doi_result

        creators = [
            {"creatorType": "author", "name": author["name"]}
            for author in summary.get("authors", [])
            if author.get("name")
        ]
        item = {
            "itemType": "journalArticle",
            "title": summary.get("title", ""),
            "creators": creators,
            "date": summary.get("pubdate", ""),
            "publicationTitle": summary.get("source", ""),
            "volume": summary.get("volume", ""),
            "issue": summary.get("issue", ""),
            "pages": summary.get("pages", ""),
            "ISSN": summary.get("issn", ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "extra": f"PMID: {pmid}",
        }

        result = save_item(
            zot,
            item,
            uri=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            collection_key=collection,
            tags=_normalize_tags(tags),
            operation="import_by_pmid",
        )
        return _import_success("import_by_pmid", result["item_key"], details={"pmid": pmid, "doi": doi})
    except httpx.HTTPError as exc:
        return error_result(
            "import_by_pmid",
            "pubmed_lookup",
            f"PubMed lookup failed for PMID {pmid}",
            details={"pmid": pmid, "exception_type": type(exc).__name__},
        )
    except Exception as exc:
        return result_from_exception("import_by_pmid", exc)


def import_by_arxiv(
    zot: zotero.Zotero,
    arxiv_id: str,
    *,
    collection: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch item metadata from arXiv API and create Zotero item.

    Uses the arXiv API to retrieve bibliographic metadata for an arXiv ID
    and creates a new item in Zotero with the fetched data.

    Args:
        zot: Zotero client
        arxiv_id: arXiv identifier (e.g., "2301.12345" or "hep-th/9901001")

    Returns:
        The key of the created item, or None if the API request failed
    """
    import re

    # Clean arXiv ID (remove prefix like arXiv:)
    clean_id = arxiv_id.replace("arXiv:", "").strip()

    url = f"http://export.arxiv.org/api/query?id_list={clean_id}"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()

        # Parse Atom XML response
        import xml.etree.ElementTree as ET

        # Define namespaces
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        root = ET.fromstring(response.text)
        entries = root.findall("atom:entry", ns)

        if not entries:
            return error_result(
                "import_by_arxiv",
                "arxiv_lookup",
                f"arXiv did not return metadata for {clean_id}",
                details={"arxiv_id": clean_id},
            )

        entry = entries[0]

        # Extract metadata
        def get_text(elem, namespace="atom"):
            el = entry.find(f"{namespace}:{elem}", ns)
            return el.text if el is not None else ""

        # Build Zotero preprint item
        item = {
            "itemType": "preprint",
            "title": get_text("title"),
            "archiveID": clean_id,
        }

        # Add authors/creators
        creators = []
        for author_elem in entry.findall("atom:author", ns):
            creator = {"creatorType": "author"}
            name_elem = author_elem.find("atom:name", ns)
            if name_elem is not None and name_elem.text:
                name = name_elem.text
                parts = name.split(" ", 1)
                if len(parts) == 2:
                    creator["firstName"] = parts[0]
                    creator["lastName"] = parts[1]
                else:
                    creator["lastName"] = name
                creators.append(creator)
        if creators:
            item["creators"] = creators

        # Add abstract
        summary = get_text("summary")
        if summary:
            # Clean up whitespace
            item["abstractNote"] = " ".join(summary.split())

        # Add publication date
        published = get_text("published")
        if published:
            # Parse ISO date format
            item["date"] = published[:10]  # YYYY-MM-DD

        # Add arXiv URL
        item["url"] = f"https://arxiv.org/abs/{clean_id}"

        # Add DOI if available
        doi_elem = entry.find("arxiv:doi", ns)
        if doi_elem is not None and doi_elem.text:
            item["DOI"] = doi_elem.text

        # Add journal reference if available
        journal_ref = entry.find("arxiv:journal_ref", ns)
        if journal_ref is not None and journal_ref.text:
            item["extra"] = f"Journal: {journal_ref.text}"

        # Add categories as tags
        category_tags = []
        for category in entry.findall("atom:category", ns):
            term = category.get("term", "")
            if term:
                category_tags.append({"tag": term})
        if category_tags:
            item["tags"] = category_tags

        result = save_item(
            zot,
            item,
            uri=item["url"],
            collection_key=collection,
            tags=_normalize_tags(tags),
            operation="import_by_arxiv",
        )
        return _import_success("import_by_arxiv", result["item_key"], details={"arxiv_id": clean_id})
    except httpx.HTTPError as exc:
        return error_result(
            "import_by_arxiv",
            "arxiv_lookup",
            f"arXiv lookup failed for {clean_id}",
            details={"arxiv_id": clean_id, "exception_type": type(exc).__name__},
        )
    except Exception as exc:
        return result_from_exception("import_by_arxiv", exc)


def import_from_bibtex(zot: zotero.Zotero, bibtex_content: str) -> list[str]:
    """Parse BibTeX content and create Zotero items.

    Parses BibTeX entries and creates corresponding items in Zotero.
    Supports common entry types and fields.

    Args:
        zot: Zotero client
        bibtex_content: BibTeX formatted string containing one or more entries

    Returns:
        List of keys for created items. Empty list if parsing failed.
    """
    if not bibtex_content.strip():
        return []
    imported = import_text(bibtex_content, operation="import_from_bibtex")
    return [item["key"] for item in imported if item.get("key")]


def import_from_json(zot: zotero.Zotero, json_data: str | list | dict) -> list[str]:
    """Import items from Zotero JSON format.

    Imports items from JSON in Zotero's native format. Accepts JSON string,
    list of items, or single item dict.

    Args:
        zot: Zotero client
        json_data: JSON string, list, or dict in Zotero format.

    Returns:
        List of keys for created/updated items. Empty list if import failed.
    """
    import json

    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data

    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        raise ConnectorWriteError(
            operation="import_from_json",
            stage="input_validation",
            message="Expected a JSON object or list of objects for Zotero import",
            details={"input_type": type(data).__name__},
        )

    created_keys: list[str] = []

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ConnectorWriteError(
                operation="import_from_json",
                stage="input_validation",
                message="Each JSON import entry must be an object",
                details={"index": index, "entry_type": type(item).__name__},
            )

        if "data" in item:
            item_data = item["data"].copy()
            if "key" in item:
                item_data["key"] = item["key"]
        else:
            item_data = item.copy()

        if item_data.get("key"):
            result = local_write(
                "replace_item_json",
                payload={"item_key": item_data["key"], "item_json": item_data},
                operation="import_from_json",
            )
            if not result.get("success"):
                raise ConnectorWriteError(
                    operation="import_from_json",
                    stage=result.get("stage", "replace_item_json"),
                    message=result.get("error", "Local JSON import update failed"),
                    details={"index": index, **result.get("details", {})},
                )
            created_keys.append(item_data["key"])
            continue

        if item_data.get("parentItem"):
            if item_data.get("itemType") == "note":
                result = local_write(
                    "attach_note",
                    payload={
                        "parent_item_key": item_data["parentItem"],
                        "note_text": item_data.get("note", ""),
                        "title": item_data.get("title"),
                    },
                    operation="import_from_json",
                )
                if not result.get("success"):
                    raise ConnectorWriteError(
                        operation="import_from_json",
                        stage=result.get("stage", "attach_note"),
                        message=result.get("error", "Local JSON child-note import failed"),
                        details={"index": index, **result.get("details", {})},
                    )
                created_keys.append(result.get("note_key"))
                continue

            raise ConnectorWriteError(
                operation="import_from_json",
                stage="unsupported_child_item",
                message="Local JSON import for this child item type is not wired yet",
                details={
                    "index": index,
                    "parentItem": item_data["parentItem"],
                    "itemType": item_data.get("itemType"),
                },
            )

        if not item_data.get("itemType"):
            raise ConnectorWriteError(
                operation="import_from_json",
                stage="input_validation",
                message="Local JSON import entries require itemType",
                details={"index": index},
            )

        result = save_item(
            zot,
            item_data,
            uri=item_data.get("url") or f"https://opencode.local/import-json/{index}",
            operation="import_from_json",
        )
        created_keys.append(result["item_key"])

    return created_keys
