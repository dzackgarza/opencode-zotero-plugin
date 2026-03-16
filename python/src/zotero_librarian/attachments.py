from __future__ import annotations

"""
Attachment file operations for Zotero library items.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx
from pyzotero import zotero

from .connector import (
    ConnectorWriteError,
    FULLTEXT_ATTACH_PATH,
    MIN_LOCAL_PLUGIN_VERSION,
    endpoint_url,
    error_result,
    local_write,
    require_local_plugin_version,
)


FULLTEXT_ATTACH_URL = endpoint_url(FULLTEXT_ATTACH_PATH)
FULLTEXT_ATTACH_TIMEOUT = 30.0
FULLTEXT_ALLOWED_DIRS = (Path("/tmp"), Path("/var/tmp"))


def _is_fulltext_allowed_path(file_path: Path) -> bool:
    resolved = file_path.resolve()
    return any(resolved == allowed_dir or allowed_dir in resolved.parents for allowed_dir in FULLTEXT_ALLOWED_DIRS)


def _stage_file_for_fulltext_attach(file_path: Path) -> tuple[Path, bool]:
    if _is_fulltext_allowed_path(file_path):
        return file_path, False
    with tempfile.NamedTemporaryFile(
        prefix="zotero-fulltext-",
        suffix=file_path.suffix,
        dir="/tmp",
        delete=False,
    ) as staged_handle:
        staged_path = Path(staged_handle.name)
    shutil.copy2(file_path, staged_path)
    return staged_path, True


def attach_file_to_item(
    zot: zotero.Zotero,
    parent_item_key: str,
    file_path: str,
    *,
    title: str,
    operation: str,
) -> dict[str, Any]:
    source_file = Path(file_path)
    if not source_file.exists():
        return error_result(
            operation,
            "input_validation",
            f"File not found: {file_path}",
            details={"parent_item_key": parent_item_key, "file_path": file_path},
        )

    parent = zot.item(parent_item_key)
    if not parent:
        return error_result(
            operation,
            "lookup_parent_item",
            f"Parent item not found: {parent_item_key}",
            details={"parent_item_key": parent_item_key, "file_path": file_path},
        )

    if parent.get("library", {}).get("type") != "user":
        return error_result(
            operation,
            "fulltext_attach_library_scope",
            "The local fulltext attachment plugin currently supports My Library items only.",
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "library_type": parent.get("library", {}).get("type"),
            },
        )

    staged_path, staged_copy_created = _stage_file_for_fulltext_attach(source_file)
    payload = {
        "item_key": parent_item_key,
        "file_path": str(staged_path),
        "title": title,
    }

    try:
        plugin_info = require_local_plugin_version(
            MIN_LOCAL_PLUGIN_VERSION,
            operation=operation,
        )
        response = httpx.post(
            FULLTEXT_ATTACH_URL,
            json=payload,
            timeout=FULLTEXT_ATTACH_TIMEOUT,
        )
    except ConnectorWriteError as exc:
        return exc.to_dict()
    except httpx.HTTPError as exc:
        return error_result(
            operation,
            "fulltext_attach_request",
            f"Request to {FULLTEXT_ATTACH_URL} failed",
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "staged_file_path": str(staged_path),
                "exception_type": type(exc).__name__,
            },
        )
    finally:
        if staged_copy_created and staged_path.exists():
            staged_path.unlink()

    if response.status_code == 404 and "No endpoint found" in response.text:
        return error_result(
            operation,
            "fulltext_attach_endpoint",
            "The /fulltext-attach Zotero plugin endpoint is not available.",
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "status_code": response.status_code,
                "body": response.text,
            },
        )

    try:
        response_data = response.json()
    except ValueError:
        return error_result(
            operation,
            "parse_response",
            "The /fulltext-attach endpoint did not return valid JSON.",
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "status_code": response.status_code,
                "body": response.text,
            },
        )

    if not response_data.get("success"):
        return error_result(
            operation,
            "fulltext_attach_endpoint",
            response_data.get("error", "The /fulltext-attach endpoint reported a failure."),
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "status_code": response.status_code,
                "response": response_data,
            },
        )

    return {
        "success": True,
        "operation": operation,
        "stage": "completed",
        "parent_item_key": parent_item_key,
        "attachment_key": response_data.get("attachment_key"),
        "attachment_id": response_data.get("attachment_id"),
        "title": title,
        "file_path": file_path,
        "version": response_data.get("version", plugin_info["version"]),
        "message": response_data.get("message"),
    }


def upload_pdf(zot: zotero.Zotero, parent_item_key: str, pdf_path: str, title: str = None) -> dict:
    """Upload a PDF file as an attachment to an item.

    Uses the installed local `/fulltext-attach` plugin endpoint to attach the
    PDF to an existing item as a stored Zotero attachment. Files outside
    `/tmp` and `/var/tmp` are staged into `/tmp` before the request.

    Args:
        zot: Zotero client
        parent_item_key: Key of parent item to attach PDF to
        pdf_path: Path to the PDF file to upload
        title: Optional title for attachment (defaults to PDF filename)

    Returns:
        Dict with "success" (bool) and either "key" (str) on success or "error" (str) on failure
    """
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return error_result(
            "upload_pdf",
            "input_validation",
            f"PDF not found: {pdf_path}",
            details={"parent_item_key": parent_item_key, "pdf_path": pdf_path},
        )

    if not pdf_file.suffix.lower() == ".pdf":
        return error_result(
            "upload_pdf",
            "input_validation",
            f"File is not a PDF: {pdf_path}",
            details={"parent_item_key": parent_item_key, "pdf_path": pdf_path},
        )

    if title is None:
        title = pdf_file.name
    return attach_file_to_item(
        zot,
        parent_item_key,
        pdf_path,
        title=title,
        operation="upload_pdf",
    )


def download_attachment(zot: zotero.Zotero, attachment_key: str, output_path: str) -> dict:
    """Download an attachment file from Zotero to local storage.

    Retrieves the actual file content for an attachment item and saves it
    to the specified local path.

    Args:
        zot: Zotero client
        attachment_key: Key of the attachment item to download
        output_path: Local file path where the attachment will be saved

    Returns:
        Dict with "success" (bool) and either "message" (str) on success or "error" (str) on failure
    """
    from pathlib import Path
    import httpx

    try:
        # Get attachment item info
        attachment = zot.item(attachment_key)
        if not attachment:
            return {"success": False, "error": f"Attachment not found: {attachment_key}"}

        # Verify it's an attachment
        if attachment.get("data", {}).get("itemType") != "attachment":
            return {"success": False, "error": f"Item is not an attachment: {attachment_key}"}

        # Get the file download URL from local API
        download_url = f"http://localhost:23119/api/users/0/items/{attachment_key}/file"

        # Download the file
        response = httpx.get(
            download_url,
            headers={"Zotero-API-Key": "fake"},
            timeout=60.0,
        )

        if response.status_code != 200:
            return {"success": False, "error": f"Download failed with status {response.status_code}"}

        # Write to output path
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "wb") as f:
            f.write(response.content)

        return {"success": True, "message": f"Downloaded {len(response.content)} bytes to {output_path}"}

    except httpx.HTTPError as e:
        return {"success": False, "error": f"HTTP error during download: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_attachment(zot: zotero.Zotero, attachment_key: str) -> dict:
    """Delete an attachment from Zotero.

    Removes the attachment item and its associated file from Zotero.
    The file is moved to trash and can be recovered until trash is emptied.

    Args:
        zot: Zotero client
        attachment_key: Key of the attachment to delete

    Returns:
        Dict with "success" (bool) and either "message" (str) on success or "error" (str) on failure
    """
    try:
        # Verify the item exists and is an attachment
        attachment = zot.item(attachment_key)
        if not attachment:
            return {"success": False, "error": f"Attachment not found: {attachment_key}"}

        if attachment.get("data", {}).get("itemType") != "attachment":
            return {"success": False, "error": f"Item is not an attachment: {attachment_key}"}

        return local_write(
            "trash_item",
            payload={"item_key": attachment_key},
            operation="delete_attachment",
        )

    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_text_from_pdf(zot: zotero.Zotero, attachment_key: str) -> dict:
    """Extract text content from a PDF attachment.

    Downloads the PDF and extracts its text content using pdfplumber.
    Returns the full text content as a string.

    Args:
        zot: Zotero client
        attachment_key: Key of the PDF attachment to extract text from

    Returns:
        Dict with "success" (bool) and either "text" (str) on success or "error" (str) on failure

    Note:
        Requires pdfplumber package: pip install pdfplumber
    """
    import tempfile
    import os

    try:
        # Get attachment item info
        attachment = zot.item(attachment_key)
        if not attachment:
            return {"success": False, "error": f"Attachment not found: {attachment_key}"}

        # Verify it's a PDF attachment
        item_data = attachment.get("data", {})
        if item_data.get("itemType") != "attachment":
            return {"success": False, "error": f"Item is not an attachment: {attachment_key}"}

        content_type = item_data.get("contentType", "")
        if content_type != "application/pdf":
            return {"success": False, "error": f"Attachment is not a PDF (content type: {content_type})"}

        # Try to import pdfplumber
        try:
            import pdfplumber
        except ImportError:
            return {"success": False, "error": "pdfplumber not installed. Run: pip install pdfplumber"}

        # Download the PDF to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            download_result = download_attachment(zot, attachment_key, tmp_path)
            if not download_result["success"]:
                return download_result

            # Extract text using pdfplumber
            text_parts = []
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            full_text = "\n\n".join(text_parts)
            return {"success": True, "text": full_text, "pages": len(text_parts)}

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        return {"success": False, "error": str(e)}


def _slugify(text: str, max_len: int = 80) -> str:
    """Convert text to a slug suitable for a filename stem.

    Lowercases, replaces spaces with underscores, strips non-alphanumeric
    characters (except underscores), and truncates to max_len characters.
    """
    import re
    text = text.lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w]", "", text)  # \w matches [a-zA-Z0-9_]
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len]


def rename_pdf_attachments(
    zot: zotero.Zotero,
    *,
    dry_run: bool = True,
    collection_key: str | None = None,
) -> list[dict[str, Any]]:
    """Rename PDF attachment titles based on their parent item's title.

    Policy: slugify parent title (lowercase, spaces→underscores, strip
    non-alphanumeric except underscore), truncate to 80 chars, append ".pdf".
    Only the attachment's *title* field is updated — the stored filename on
    disk is not renamed.

    Args:
        zot: Zotero client
        dry_run: When True (default), report planned renames without writing.
        collection_key: Optional collection key to restrict scope.

    Returns:
        List of dicts with 'key', 'old_title', 'new_title', and optionally
        'result' (the update_item_fields response) when dry_run=False.
    """
    from .items import update_item_fields

    # Collect PDF attachments with their parent titles
    if collection_key:
        # Get collection items and then their PDF children
        candidates = []
        for item in zot.collection_items_top(collection_key):
            parent_title = item["data"].get("title", "") or item["key"]
            slug = _slugify(parent_title)
            if not slug:
                slug = item["key"].lower()
            new_title = slug + ".pdf"
            children = zot.children(item["key"])
            for child in children:
                cdata = child.get("data", {})
                if (
                    cdata.get("itemType") == "attachment"
                    and cdata.get("contentType") == "application/pdf"
                ):
                    candidates.append(
                        {
                            "key": child["key"],
                            "old_title": cdata.get("title", ""),
                            "new_title": new_title,
                        }
                    )
    else:
        candidates = []
        from .client import _get_library_with_children

        for item in _get_library_with_children(zot):
            if item["data"].get("itemType") in {"attachment", "note"}:
                continue
            parent_title = item["data"].get("title", "") or item["key"]
            slug = _slugify(parent_title)
            if not slug:
                slug = item["key"].lower()
            new_title = slug + ".pdf"
            for child in item.get("_children", []):
                cdata = child.get("data", {})
                if (
                    cdata.get("itemType") == "attachment"
                    and cdata.get("contentType") == "application/pdf"
                ):
                    candidates.append(
                        {
                            "key": child["key"],
                            "old_title": cdata.get("title", ""),
                            "new_title": new_title,
                        }
                    )

    results: list[dict[str, Any]] = []
    for entry in candidates:
        record: dict[str, Any] = {
            "key": entry["key"],
            "old_title": entry["old_title"],
            "new_title": entry["new_title"],
        }
        if not dry_run and entry["old_title"] != entry["new_title"]:
            record["result"] = update_item_fields(
                zot, entry["key"], {"title": entry["new_title"]}
            )
        results.append(record)

    return results


def extract_and_attach_text(
    zot: zotero.Zotero,
    item_key: str,
    *,
    extractor: str = "pdftotext",
) -> dict[str, Any]:
    """Extract text from a PDF attachment and upload it as a .txt attachment.

    Finds the first PDF attachment child of item_key, runs pdftotext
    (from poppler-utils) to extract text, saves it to a temp file, and
    uploads it via upload_pdf (which handles the /fulltext-attach endpoint).

    Requires: pdftotext (poppler-utils) installed and on PATH.

    Args:
        zot: Zotero client
        item_key: Key of the parent Zotero item.
        extractor: Extraction command to use.  Currently only "pdftotext"
                   is supported.

    Returns:
        Dict with 'success' bool and relevant details.  If no PDF attachment
        exists, returns a structured error result rather than raising.
    """
    import subprocess
    import tempfile
    import os
    from pathlib import Path as _Path

    operation = "extract_and_attach_text"

    if extractor != "pdftotext":
        return error_result(
            operation,
            "input_validation",
            f"Unsupported extractor: {extractor!r}.  Only 'pdftotext' is supported.",
            details={"item_key": item_key, "extractor": extractor},
        )

    # Locate PDF attachment
    try:
        children = zot.children(item_key)
    except Exception as exc:
        from .connector import result_from_exception
        return result_from_exception(operation, exc)

    pdf_attachment = next(
        (
            c
            for c in children
            if c["data"].get("itemType") == "attachment"
            and c["data"].get("contentType") == "application/pdf"
        ),
        None,
    )

    if pdf_attachment is None:
        return error_result(
            operation,
            "locate_pdf",
            f"No PDF attachment found for item {item_key}.",
            details={"item_key": item_key},
        )

    # Resolve path on disk: ~/Zotero/storage/<att_key>/<filename>
    att_data = pdf_attachment["data"]
    att_key = pdf_attachment["key"]
    filename = att_data.get("filename", "")
    if not filename:
        return error_result(
            operation,
            "locate_pdf",
            f"PDF attachment {att_key} has no filename recorded.",
            details={"item_key": item_key, "attachment_key": att_key},
        )

    pdf_path = _Path.home() / "Zotero" / "storage" / att_key / filename
    if not pdf_path.exists():
        return error_result(
            operation,
            "locate_pdf",
            f"PDF file not found on disk: {pdf_path}",
            details={
                "item_key": item_key,
                "attachment_key": att_key,
                "pdf_path": str(pdf_path),
            },
        )

    # Run pdftotext
    try:
        proc = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            check=True,
            text=True,
        )
        extracted_text = proc.stdout
    except FileNotFoundError:
        return error_result(
            operation,
            "pdftotext_not_found",
            "pdftotext is not installed or not on PATH.  Install poppler-utils.",
            details={"item_key": item_key, "pdf_path": str(pdf_path)},
        )
    except subprocess.CalledProcessError as exc:
        return error_result(
            operation,
            "pdftotext_failed",
            f"pdftotext exited with code {exc.returncode}: {exc.stderr.strip()}",
            details={
                "item_key": item_key,
                "pdf_path": str(pdf_path),
                "stderr": exc.stderr,
            },
        )

    # Save to a temp .txt file and upload
    stem = _Path(filename).stem
    txt_title = stem + ".txt"

    with tempfile.NamedTemporaryFile(
        prefix="zotero-text-",
        suffix=".txt",
        dir="/tmp",
        delete=False,
        mode="w",
        encoding="utf-8",
    ) as tmp:
        tmp.write(extracted_text)
        tmp_path = tmp.name

    try:
        # upload_pdf / attach_file_to_item works for any file; txt upload is fine
        upload_result = attach_file_to_item(
            zot,
            item_key,
            tmp_path,
            title=txt_title,
            operation=operation,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not upload_result.get("success"):
        return upload_result

    return {
        **upload_result,
        "operation": operation,
        "item_key": item_key,
        "attachment_key": att_key,
        "txt_title": txt_title,
        "characters_extracted": len(extracted_text),
    }


def replace_attachment(zot: zotero.Zotero, attachment_key: str, new_file_path: str) -> dict:
    """Replace the file content of an existing attachment.

    Updates the file content for an attachment item while preserving
    all metadata (title, tags, notes, relations).

    Args:
        zot: Zotero client
        attachment_key: Key of the attachment to replace
        new_file_path: Path to the new file to upload

    Returns:
        Dict with "success" (bool) and either "message" (str) on success or "error" (str) on failure
    """
    try:
        # Get the attachment item
        attachment = zot.item(attachment_key)
        if not attachment:
            return {"success": False, "error": f"Attachment not found: {attachment_key}"}

        # Verify it's an attachment
        if attachment.get("data", {}).get("itemType") != "attachment":
            return {"success": False, "error": f"Item is not an attachment: {attachment_key}"}

        # Check new file exists
        new_file = Path(new_file_path)
        if not new_file.exists():
            return {"success": False, "error": f"File not found: {new_file_path}"}

        return local_write(
            "relink_attachment_file",
            payload={"attachment_key": attachment_key, "file_path": new_file_path},
            operation="replace_attachment",
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_arxiv_pdfs(
    zot: zotero.Zotero,
    key: str | None = None,
    min_similarity: float = 0.7,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Fetch and attach arXiv PDFs for items missing them.

    Phases:
      1. Extract arXiv ID from Extra field, DOI, or URL.
      2. If not found, use arxiv title search with min_similarity threshold.
      3. Download PDF and attach to item, update Extra field.

    Args:
        zot: Zotero client.
        key: Specific item key to process. If None, processes all items.
        min_similarity: Threshold for title search fallback (0.0 to 1.0).
        dry_run: If True, do not download or attach anything.

    Returns:
        Dict with stats and results.
    """
    import re
    import time
    from pathlib import Path
    from .client import _get_library_with_children
    from .items import update_item_fields
    from .enrichment import _item_has_pdf
    from .arxiv import search_arxiv_papers, download_arxiv_paper

    def _jaccard_similarity(s1: str, s2: str) -> float:
        set1 = set(re.findall(r'\w+', s1.lower()))
        set2 = set(re.findall(r'\w+', s2.lower()))
        if not set1 and not set2:
            return 1.0
        return len(set1.intersection(set2)) / len(set1.union(set2))

    def _extract_arxiv_id(item: dict) -> str | None:
        data = item.get("data", {})

        # 1. Extra field
        extra = data.get("extra", "")
        match = re.search(r"(?i)arxiv:\s*([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", extra)
        if match:
            return match.group(1)

        # 2. DOI
        doi = data.get("DOI", "")
        match = re.search(r"(?i)10\.48550/arxiv\.([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", doi)
        if match:
            return match.group(1)

        # 3. URL
        url = data.get("url", "")
        match = re.search(r"(?i)arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)", url)
        if match:
            return match.group(1)

        return None

    candidates = []
    if key:
        item = zot.item(key)
        if not item:
            return {"error": f"Item {key} not found."}
        children = zot.children(key)
        if not _item_has_pdf(children):
            candidates.append(item)
    else:
        for item in _get_library_with_children(zot):
            if item["data"].get("itemType") in {"attachment", "note"}:
                continue
            if not _item_has_pdf(item.get("_children", [])):
                candidates.append(item)

    results = []
    processed = 0
    attached = 0
    not_found = 0

    last_api_call = 0.0

    def _rate_limit():
        nonlocal last_api_call
        now = time.time()
        elapsed = now - last_api_call
        if elapsed < 3.0:
            time.sleep(3.0 - elapsed)
        last_api_call = time.time()

    for item in candidates:
        processed += 1
        item_key = item["key"]
        title = item["data"].get("title", "")

        entry: dict[str, Any] = {"key": item_key, "title": title}

        arxiv_id = _extract_arxiv_id(item)

        if not arxiv_id and title:
            _rate_limit()
            try:
                search_results = search_arxiv_papers(query=f'ti:"{title}"', max_results=5)
            except Exception:
                search_results = []

            best_match = None
            best_sim = 0.0

            for paper in search_results:
                sim = _jaccard_similarity(title, paper["title"])
                if sim >= min_similarity and sim > best_sim:
                    best_sim = sim
                    best_match = paper

            if best_match:
                arxiv_id = best_match["id"]
                entry["similarity"] = round(best_sim, 3)
                entry["search_matched"] = True

        if not arxiv_id:
            entry["status"] = "not_found"
            not_found += 1
            results.append(entry)
            continue

        entry["arxiv_id"] = arxiv_id

        if dry_run:
            entry["status"] = "found_dry_run"
            results.append(entry)
            continue

        _rate_limit()
        try:
            download_result = download_arxiv_paper(arxiv_id, convert_to_markdown=False)
            if not download_result.get("success"):
                entry["status"] = "download_failed"
                entry["error"] = download_result.get("error")
                results.append(entry)
                continue

            pdf_path = download_result.get("pdf_path")
            if not pdf_path:
                # download_arxiv_paper returns markdown_path-only when the paper
                # was already converted and cached; the PDF still exists on disk.
                from .arxiv import DEFAULT_STORAGE_PATH
                candidate = DEFAULT_STORAGE_PATH / f"{arxiv_id}.pdf"
                if candidate.exists():
                    pdf_path = str(candidate)
                else:
                    entry["status"] = "no_pdf_path"
                    entry["error"] = "download_arxiv_paper returned no pdf_path"
                    results.append(entry)
                    continue

            upload_result = attach_file_to_item(
                zot,
                item_key,
                pdf_path,
                title=f"arXiv {arxiv_id} PDF",
                operation="fetch_arxiv_pdfs",
            )
            if upload_result.get("success"):
                entry["status"] = "attached"
                attached += 1

                extra = item["data"].get("extra", "")
                if f"arXiv: {arxiv_id}" not in extra:
                    new_extra = f"{extra}\nArXiv: {arxiv_id}".strip()
                    update_item_fields(zot, item_key, {"extra": new_extra})
            else:
                entry["status"] = "attach_failed"
                entry["error"] = upload_result.get("error", "Unknown error")
            # Do NOT delete the PDF: download_arxiv_paper stores it in the
            # persistent ~/.arxiv-papers cache; deleting it forces re-download.

        except Exception as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)

        results.append(entry)

    return {
        "processed": processed,
        "attached": attached,
        "not_found": not_found,
        "dry_run": dry_run,
        "results": results,
    }
