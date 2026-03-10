"""Enrichment and batch operations for the local Zotero API."""

from __future__ import annotations

import difflib
import json
import re
import shutil
import tempfile
import time
from pathlib import Path

import httpx
from pyzotero import zotero

from .attachments import upload_pdf
from .client import _get_library_with_children
from .import_ import import_by_doi, import_by_isbn, import_by_pmid
from .items import attach_url, update_item_fields
from .query import get_item_by_doi, get_item_by_isbn

_DOI_ITEM_TYPES = {"journalArticle", "conferencePaper"}
_PDF_SOURCES = ("unpaywall", "semanticscholar", "doi")
_HTTP_TIMEOUT = 30.0
_CROSSREF_EMAIL = "zotero-lib@example.com"


def _top_level_items(
    zot: zotero.Zotero,
    collection: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    items: list[dict] = []
    for item in _iter_top_level_items(zot, collection=collection):
        items.append(item)
        if limit is not None and len(items) >= limit:
            break
    return items


def _iter_top_level_items(
    zot: zotero.Zotero,
    collection: str | None = None,
):
    start = 0
    page_size = 100
    while True:
        kwargs = {"start": start, "limit": page_size}
        if collection:
            page = zot.collection_items_top(collection, **kwargs)
        else:
            page = zot.top(**kwargs)
        if not page:
            break
        yield from page
        if len(page) < page_size:
            break
        start += page_size


def _item_data(item: dict) -> dict:
    return item.get("data", item)


def _existing_item_for_identifier(
    zot: zotero.Zotero,
    identifier: str,
    id_type: str,
) -> dict | None:
    if id_type == "doi":
        return get_item_by_doi(zot, identifier)
    if id_type == "isbn":
        return get_item_by_isbn(zot, identifier)
    if id_type == "pmid":
        needle = re.compile(rf"(?mi)^PMID:\s*{re.escape(identifier)}\s*$")
        for item in _top_level_items(zot):
            extra = item["data"].get("extra", "") or ""
            if needle.search(extra):
                return item
    return None


def _import_identifier(
    zot: zotero.Zotero,
    identifier: str,
    id_type: str,
    *,
    collection: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    if id_type == "doi":
        return import_by_doi(zot, identifier, collection=collection, tags=tags)
    if id_type == "isbn":
        return import_by_isbn(zot, identifier, collection=collection, tags=tags)
    if id_type == "pmid":
        return import_by_pmid(zot, identifier, collection=collection, tags=tags)
    raise ValueError(f"Unknown identifier type: {id_type}")


def batch_add_identifiers(
    zot: zotero.Zotero,
    identifiers: list[str],
    id_type: str = "doi",
    collection: str | None = None,
    tags: str | None = None,
    force: bool = False,
) -> dict:
    """Import many identifiers into Zotero through the local API."""
    counts = {"added": 0, "duplicate": 0, "failed": 0}
    results = []
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None
    for identifier in identifiers:
        existing = _existing_item_for_identifier(zot, identifier, id_type)
        if existing and not force:
            counts["duplicate"] += 1
            results.append(
                {
                    "identifier": identifier,
                    "status": "duplicate",
                    "existing": _item_data(existing),
                }
            )
            continue

        try:
            import_result = _import_identifier(
                zot,
                identifier,
                id_type,
                collection=collection,
                tags=tag_list,
            )
            if not import_result.get("success"):
                counts["failed"] += 1
                failure = {"identifier": identifier, "status": "failed", **import_result}
                results.append(
                    failure
                )
                continue

            item = zot.item(import_result["item_key"])
            added = {
                "identifier": identifier,
                "status": "added",
                "item": _item_data(item),
                "item_key": import_result["item_key"],
            }
            if import_result.get("warning"):
                added["warning"] = import_result["warning"]
            counts["added"] += 1
            results.append(added)
        except Exception as exc:
            counts["failed"] += 1
            results.append(
                {
                    "identifier": identifier,
                    "status": "failed",
                    "error": str(exc),
                }
            )

        time.sleep(1)

    return {**counts, "results": results}


def _item_has_pdf(children: list[dict]) -> bool:
    return any(
        child["data"].get("itemType") == "attachment"
        and child["data"].get("contentType") == "application/pdf"
        for child in children
    )


def check_pdfs(
    zot: zotero.Zotero,
    collection: str | None = None,
) -> dict:
    """Summarize which local Zotero items do or do not have PDFs."""
    if collection:
        items = _top_level_items(zot, collection=collection)
        children_by_key = {item["key"]: zot.children(item["key"]) for item in items}
    else:
        items = [
            item
            for item in _get_library_with_children(zot)
            if item["data"].get("itemType") not in {"attachment", "note"}
        ]
        children_by_key = {item["key"]: item.get("_children", []) for item in items}

    missing = []
    with_pdf = 0
    for item in items:
        if _item_has_pdf(children_by_key[item["key"]]):
            with_pdf += 1
        else:
            missing.append(
                {
                    "key": item["key"],
                    "title": item["data"].get("title", ""),
                    "doi": item["data"].get("DOI", ""),
                }
            )

    return {
        "total": len(items),
        "with_pdf": with_pdf,
        "without_pdf": len(missing),
        "missing": missing,
    }


def _match_citation_in_scope(items: list[dict], author: str, year: str) -> dict | None:
    needle = author.split()[0].lower().rstrip(",")
    for item in items:
        item_year = _extract_year(item["data"].get("date", "")) or ""
        if item_year != year:
            continue
        for creator in item["data"].get("creators", []):
            last_name = creator.get("lastName", creator.get("name", ""))
            if not last_name:
                continue
            candidate = last_name.lower().rstrip(",")
            if candidate == needle or candidate.startswith(needle[:4]) or needle.startswith(candidate[:4]):
                return item
    return None


def _match_citation_via_search(zot: zotero.Zotero, author: str, year: str) -> dict | None:
    query = f"{author.split()[0]} {year}"
    candidates = zot.items(q=query, qmode="titleCreatorYear", limit=25)
    return _match_citation_in_scope(
        [
            item
            for item in candidates
            if item["data"].get("itemType") not in {"attachment", "note"}
        ],
        author,
        year,
    )


def crossref_citations(
    zot: zotero.Zotero,
    text: str,
    collection: str | None = None,
) -> dict:
    """Match citation text against the local Zotero library."""
    patterns = [
        r"([A-Z][a-zé]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-zé]+))?)\s*\((\d{4})\)",
        r"([A-Z][a-zé]+(?:\s+(?:et\s+al\.|,?\s+(?:and|&)\s+[A-Z][a-zé]+))?),?\s+(\d{4})",
    ]

    citations: set[tuple[str, str]] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            citations.add((match.group(1).strip().rstrip(","), match.group(2)))

    if not citations:
        return {"error": "No citations found. Expected format: Author (Year)"}

    scoped_items = _top_level_items(zot, collection=collection) if collection else None

    found = []
    missing = []
    for author, year in sorted(citations):
        if scoped_items is not None:
            match = _match_citation_in_scope(scoped_items, author, year)
        else:
            match = _match_citation_via_search(zot, author, year)
        if match:
            found.append(
                {
                    "citation": f"{author} ({year})",
                    "item_key": match["key"],
                    "title": match["data"].get("title", ""),
                }
            )
        else:
            missing.append({"citation": f"{author} ({year})"})

    return {"total_citations": len(citations), "found": found, "missing": missing}


def _normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _normalize_text(a), _normalize_text(b)).ratio()


def _extract_year(date_str: str) -> str | None:
    match = re.match(r"(\d{4})", str(date_str))
    return match.group(1) if match else None


def _first_author_last(item_data: dict) -> str | None:
    creators = item_data.get("creators", [])
    if not creators:
        return None
    creator = creators[0]
    name = creator.get("lastName", creator.get("name", ""))
    return name.lower().strip() if name else None


def _crossref_search(title: str, first_author: str) -> list[dict]:
    response = httpx.get(
        "https://api.crossref.org/works",
        params={
            "query.bibliographic": title,
            "query.author": first_author,
            "rows": "3",
            "mailto": _CROSSREF_EMAIL,
        },
        timeout=_HTTP_TIMEOUT,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json().get("message", {}).get("items", [])


def _match_crossref_result(
    work: dict,
    zotero_title: str,
    zotero_year: str | None,
    zotero_first_author: str | None,
) -> tuple[str, dict] | None:
    crossref_title = " ".join(work.get("title", [""]))
    similarity = _title_similarity(zotero_title, crossref_title)
    if similarity < 0.85:
        return None

    issued = work.get("issued", {}).get("date-parts", [[]])
    crossref_year = str(issued[0][0]) if issued and issued[0] else None
    if zotero_year and crossref_year and zotero_year != crossref_year:
        return None
    if zotero_year and not crossref_year:
        return None

    if zotero_first_author:
        author_matches = any(
            zotero_first_author in author.get("family", "").lower()
            or author.get("family", "").lower() in zotero_first_author
            for author in work.get("author", [])
            if author.get("family")
        )
        if not author_matches:
            return None

    doi = work.get("DOI", "")
    if not doi:
        return None

    return doi, {"similarity": round(similarity * 100, 1)}


def find_missing_dois(
    zot: zotero.Zotero,
    apply: bool = False,
    limit: int | None = None,
    collection: str | None = None,
) -> dict:
    """Find and optionally add missing DOIs using CrossRef."""
    candidates = []
    skipped_has_doi = 0
    skipped_wrong_type = 0
    for item in _iter_top_level_items(zot, collection=collection):
        item_type = item["data"].get("itemType", "")
        if item_type not in _DOI_ITEM_TYPES:
            skipped_wrong_type += 1
            continue
        if item["data"].get("DOI", "").strip():
            skipped_has_doi += 1
            continue
        candidates.append(item)
        if limit is not None and len(candidates) >= limit:
            break

    results = []
    matched = 0
    unmatched = 0
    for item in candidates:
        title = item["data"].get("title", "")
        year = _extract_year(item["data"].get("date", ""))
        first_author = _first_author_last(item["data"])
        entry = {"key": item["key"], "title": title}

        if not title:
            entry["status"] = "skipped"
            entry["reason"] = "no title"
            unmatched += 1
            results.append(entry)
            continue

        works = _crossref_search(title, first_author or "")
        time.sleep(1)

        best_match = None
        for work in works:
            matched_result = _match_crossref_result(work, title, year, first_author)
            if matched_result:
                best_match = matched_result
                break

        if best_match:
            doi, info = best_match
            entry["status"] = "matched"
            entry["doi"] = doi
            entry["similarity"] = info["similarity"]
            matched += 1
            if apply:
                update_result = update_item_fields(zot, item["key"], {"DOI": doi})
                if update_result.get("success"):
                    entry["applied"] = True
                else:
                    entry["applied"] = False
                    entry["apply_result"] = update_result
        else:
            entry["status"] = "unmatched"
            unmatched += 1

        results.append(entry)

    return {
        "processed": len(candidates),
        "matched": matched,
        "unmatched": unmatched,
        "skipped_has_doi": skipped_has_doi,
        "skipped_wrong_type": skipped_wrong_type,
        "applied": apply,
        "results": results,
    }


_NO_DOI_TAG = "⛔ No DOI found"
_DOI_RECOVERED_TAG = "✅ DOI recovered"


def update_missing_dois(
    zot: zotero.Zotero,
    *,
    apply: bool = False,
    limit: int | None = None,
) -> list[dict]:
    """Attempt DOI recovery for items tagged '⛔ No DOI found' via CrossRef.

    For each tagged item, queries CrossRef by title + first author.  If a
    DOI is found and apply=True, writes the DOI to the item, removes the
    '⛔ No DOI found' tag, and adds '✅ DOI recovered'.

    Args:
        zot: Zotero client
        apply: When True, write DOIs and update tags in Zotero.
        limit: Maximum number of items to process.

    Returns:
        List of dicts with:
            - key: str
            - title: str
            - found_doi: str | None
            - applied: bool
            - error: str | None  (present only on failure)
    """
    from .items import add_tags_to_item, remove_tags_from_item, update_item_fields

    tagged_items = list(_iter_top_level_items(zot))
    candidates = [
        item
        for item in tagged_items
        if any(
            tag.get("tag", "") == _NO_DOI_TAG
            for tag in item["data"].get("tags", [])
        )
    ]

    if limit is not None:
        candidates = candidates[:limit]

    results = []
    for item in candidates:
        title = item["data"].get("title", "")
        first_author = _first_author_last(item["data"])
        year = _extract_year(item["data"].get("date", ""))
        entry: dict = {
            "key": item["key"],
            "title": title,
            "found_doi": None,
            "applied": False,
        }

        if not title:
            entry["error"] = "no title"
            results.append(entry)
            continue

        try:
            works = _crossref_search(title, first_author or "")
        except Exception as exc:
            entry["error"] = str(exc)
            results.append(entry)
            time.sleep(1)
            continue

        time.sleep(1)

        best_match = None
        for work in works:
            matched_result = _match_crossref_result(work, title, year, first_author)
            if matched_result:
                best_match = matched_result
                break

        if not best_match:
            results.append(entry)
            continue

        doi, _ = best_match
        entry["found_doi"] = doi

        if apply:
            try:
                update_result = update_item_fields(zot, item["key"], {"DOI": doi})
                if update_result.get("success"):
                    remove_tags_from_item(zot, item["key"], [_NO_DOI_TAG])
                    add_tags_to_item(zot, item["key"], [_DOI_RECOVERED_TAG])
                    entry["applied"] = True
                else:
                    entry["apply_error"] = update_result
            except Exception as exc:
                entry["apply_error"] = str(exc)

        results.append(entry)

    return results


def _try_unpaywall(doi: str) -> tuple[str, str] | None:
    response = httpx.get(
        f"https://api.unpaywall.org/v2/{doi}",
        params={"email": _CROSSREF_EMAIL},
        timeout=_HTTP_TIMEOUT,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    location = response.json().get("best_oa_location") or {}
    pdf_url = location.get("url_for_pdf")
    return (pdf_url, pdf_url) if pdf_url else None


def _try_semantic_scholar(doi: str) -> tuple[str, str] | None:
    response = httpx.get(
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
        params={"fields": "openAccessPdf"},
        timeout=_HTTP_TIMEOUT,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    pdf_url = (response.json().get("openAccessPdf") or {}).get("url")
    return (pdf_url, pdf_url) if pdf_url else None


def _try_doi_content_negotiation(doi: str) -> tuple[str, str] | None:
    response = httpx.head(
        f"https://doi.org/{doi}",
        headers={"Accept": "application/pdf"},
        timeout=_HTTP_TIMEOUT,
        follow_redirects=True,
    )
    if "application/pdf" in response.headers.get("Content-Type", ""):
        return str(response.url), f"https://doi.org/{doi}"
    return None


def _find_pdf_source(doi: str, sources: list[str]) -> tuple[str, str, str] | None:
    handlers = {
        "unpaywall": _try_unpaywall,
        "semanticscholar": _try_semantic_scholar,
        "doi": _try_doi_content_negotiation,
    }
    for source in sources:
        try:
            result = handlers[source](doi)
        except httpx.HTTPError:
            result = None
        if result:
            return result[0], result[1], source
        time.sleep(1)
    return None


def _download_pdf(url: str, destination: Path) -> bool:
    try:
        with httpx.stream(
            "GET",
            url,
            timeout=60.0,
            follow_redirects=True,
            headers={
                "User-Agent": f"Mozilla/5.0 (compatible; ZoteroLib/2.0; mailto:{_CROSSREF_EMAIL})",
                "Accept": "application/pdf,*/*",
            },
        ) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
    except httpx.HTTPError:
        return False

    with destination.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            destination.unlink(missing_ok=True)
            return False
    return True


def fetch_pdfs(
    zot: zotero.Zotero,
    dry_run: bool = False,
    limit: int | None = None,
    collection: str | None = None,
    download_dir: str | None = None,
    upload: bool = False,
    sources: list[str] | None = None,
) -> dict:
    """Find open-access PDFs and attach them to local Zotero items."""
    chosen_sources = list(sources or _PDF_SOURCES)
    invalid_sources = [source for source in chosen_sources if source not in _PDF_SOURCES]
    if invalid_sources:
        raise ValueError(f"Unknown source(s): {', '.join(invalid_sources)}")

    candidates = []
    skipped_no_doi = 0
    skipped_has_pdf = 0
    if collection is None and limit is None:
        items = [
            item
            for item in _get_library_with_children(zot)
            if item["data"].get("itemType") not in {"attachment", "note"}
        ]
        for item in items:
            doi = item["data"].get("DOI", "").strip()
            if not doi:
                skipped_no_doi += 1
                continue
            if _item_has_pdf(item.get("_children", [])):
                skipped_has_pdf += 1
                continue
            candidates.append(item)
    else:
        for item in _iter_top_level_items(zot, collection=collection):
            doi = item["data"].get("DOI", "").strip()
            if not doi:
                skipped_no_doi += 1
                continue
            children = zot.children(item["key"])
            if _item_has_pdf(children):
                skipped_has_pdf += 1
                continue
            candidates.append(item)
            if limit is not None and len(candidates) >= limit:
                break

    if download_dir and not dry_run:
        Path(download_dir).mkdir(parents=True, exist_ok=True)

    results = []
    found = 0
    attached = 0
    not_found = 0

    for item in candidates:
        doi = item["data"]["DOI"].strip()
        title = item["data"].get("title", "untitled")
        entry = {"key": item["key"], "title": title, "doi": doi}

        source = _find_pdf_source(doi, chosen_sources)
        if not source:
            entry["status"] = "not_found"
            not_found += 1
            results.append(entry)
            continue

        pdf_url, source_url, source_name = source
        entry["source"] = source_name
        entry["pdf_url"] = pdf_url
        found += 1

        if dry_run:
            entry["status"] = "found_dry_run"
            results.append(entry)
            continue

        filename = f"{re.sub(r'[^\\w]+', '_', title).strip('_') or item['key']}_{item['key']}.pdf"
        temp_dir = Path(tempfile.mkdtemp())
        temp_path = temp_dir / "download.pdf"

        try:
            downloaded = _download_pdf(pdf_url, temp_path)
            if not downloaded:
                entry["status"] = "download_failed"
                results.append(entry)
                continue
            if downloaded and download_dir:
                destination = Path(download_dir) / filename
                shutil.copy2(temp_path, destination)
                entry["saved_to"] = str(destination)

            if upload:
                upload_result = upload_pdf(zot, item["key"], str(temp_path), title=filename)
                if upload_result.get("success"):
                    entry["status"] = "uploaded"
                    entry["attachment_key"] = upload_result.get("key")
                    attached += 1
                    results.append(entry)
                    continue
                entry["upload_result"] = upload_result

            attach_response = attach_url(zot, item["key"], source_url, f"{title}.pdf")
            entry["attachment_result"] = attach_response
            if attach_response.get("success"):
                entry["status"] = "linked_url"
                attached += 1
            elif entry.get("saved_to"):
                entry["status"] = "saved_only"
            else:
                entry["status"] = "attach_failed"
            results.append(entry)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "processed": len(candidates),
        "found": found,
        "attached": attached,
        "not_found": not_found,
        "skipped_no_doi": skipped_no_doi,
        "skipped_has_pdf": skipped_has_pdf,
        "dry_run": dry_run,
        "results": results,
    }
