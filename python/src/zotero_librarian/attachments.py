from __future__ import annotations

"""
Attachment file operations for Zotero library items.
"""

import os
import base64
import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx
from pyzotero import zotero

from .connector import (
    ConnectorWriteError,
    CONNECTOR_TIMEOUT,
    MIN_LOCAL_PLUGIN_VERSION,
    error_result,
    local_write,
    plugin_endpoint_path,
    plugin_endpoint_url,
    require_local_plugin_version,
)
from .settings import fulltext_allowed_dirs


FULLTEXT_ALLOWED_DIRS = fulltext_allowed_dirs()
FULLTEXT_STAGING_DIR = FULLTEXT_ALLOWED_DIRS[0]


def _is_fulltext_allowed_path(file_path: Path) -> bool:
    resolved = file_path.resolve()
    return any(resolved == allowed_dir or allowed_dir in resolved.parents for allowed_dir in FULLTEXT_ALLOWED_DIRS)


def _stage_file_for_fulltext_attach(file_path: Path) -> tuple[Path, bool]:
    if _is_fulltext_allowed_path(file_path):
        return file_path, False
    with tempfile.NamedTemporaryFile(
        prefix="zotero-fulltext-",
        suffix=file_path.suffix,
        dir=str(FULLTEXT_STAGING_DIR),
        delete=False,
    ) as staged_handle:
        staged_path = Path(staged_handle.name)
    shutil.copy2(file_path, staged_path)
    return staged_path, True


def _plugin_supports_capability(plugin_info: dict[str, Any], capability: str) -> bool:
    capabilities = plugin_info.get("capabilities")
    return isinstance(capabilities, list) and capability in capabilities


def _attach_bytes_payload(parent_item_key: str, source_file: Path, title: str) -> dict[str, Any]:
    return {
        "item_key": parent_item_key,
        "title": title,
        "file_name": source_file.name,
        "file_bytes_base64": base64.b64encode(source_file.read_bytes()).decode("ascii"),
    }


def _is_missing_file_attach_error(response_data: dict[str, Any]) -> bool:
    error = response_data.get("error")
    return isinstance(error, str) and (
        "NS_ERROR_FILE_NOT_FOUND" in error
        or error.startswith("File not found:")
    )


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
        attach_path = plugin_endpoint_path(plugin_info, "attach")
        attach_url = plugin_endpoint_url(plugin_info, "attach")
        response = httpx.post(
            attach_url,
            json=payload,
            timeout=CONNECTOR_TIMEOUT,
        )
    except ConnectorWriteError as exc:
        return exc.to_dict()
    except httpx.HTTPError as exc:
        return error_result(
            operation,
            "fulltext_attach_request",
            f"Request to {attach_url} failed",
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "endpoint": attach_path,
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
            "The configured attach endpoint is not available.",
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "endpoint": attach_path,
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
            "The configured attach endpoint did not return valid JSON.",
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "endpoint": attach_path,
                "status_code": response.status_code,
                "body": response.text,
            },
        )

    if (
        not response_data.get("success")
        and _plugin_supports_capability(plugin_info, "attach_bytes")
        and _is_missing_file_attach_error(response_data)
    ):
        try:
            response = httpx.post(
                attach_url,
                json=_attach_bytes_payload(parent_item_key, source_file, title),
                timeout=CONNECTOR_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            return error_result(
                operation,
                "fulltext_attach_request",
                f"Request to {attach_url} failed",
                details={
                    "parent_item_key": parent_item_key,
                    "file_path": file_path,
                    "endpoint": attach_path,
                    "staged_file_path": str(staged_path),
                    "exception_type": type(exc).__name__,
                    "retry_mode": "attach_bytes",
                },
            )
        try:
            response_data = response.json()
        except ValueError:
            return error_result(
                operation,
                "parse_response",
                "The configured attach endpoint did not return valid JSON.",
                details={
                    "parent_item_key": parent_item_key,
                    "file_path": file_path,
                    "endpoint": attach_path,
                    "status_code": response.status_code,
                    "body": response.text,
                    "retry_mode": "attach_bytes",
                },
            )

    if not response_data.get("success"):
        return error_result(
            operation,
            "fulltext_attach_endpoint",
            response_data.get("error", "The configured attach endpoint reported a failure."),
            details={
                "parent_item_key": parent_item_key,
                "file_path": file_path,
                "endpoint": attach_path,
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

    Uses the installed local add-on's configured attach endpoint to attach the
    PDF to an existing item as a stored Zotero attachment. Files outside the
    configured staging directories are copied into one of them before upload.

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

    def _pdf_candidates_for_parent(parent_item: dict, children: list[dict]) -> list[dict]:
        """Build candidate rename records for one parent, with collision disambiguation."""
        parent_title = parent_item["data"].get("title", "") or parent_item["key"]
        base_slug = _slugify(parent_title) or parent_item["key"].lower()
        pdfs = [
            child for child in children
            if child.get("data", {}).get("itemType") == "attachment"
            and child.get("data", {}).get("contentType") == "application/pdf"
        ]
        records = []
        seen: dict[str, int] = {}
        for child in pdfs:
            slug = base_slug
            count = seen.get(slug, 0) + 1
            seen[slug] = count
            disambiguated = slug if count == 1 else f"{slug}_{count}"
            records.append({
                "key": child["key"],
                "old_title": child["data"].get("title", ""),
                "new_title": disambiguated + ".pdf",
            })
        return records

    # Collect PDF attachments with their parent titles
    if collection_key:
        candidates = []
        for item in zot.collection_items_top(collection_key):
            children = zot.children(item["key"])
            candidates.extend(_pdf_candidates_for_parent(item, children))
    else:
        candidates = []
        from .client import _get_library_with_children

        for item in _get_library_with_children(zot):
            if item["data"].get("itemType") in {"attachment", "note"}:
                continue
            candidates.extend(_pdf_candidates_for_parent(item, item.get("_children", [])))

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


DEFAULT_PDF_EXTRACTOR = "docling"
_PDF_EXTRACTOR_ENV = "ZOTERO_PDF_EXTRACTOR"
_MINERU_CMD_ENV = "ZOTERO_MINERU_CMD"
_EXTRACTORS = (DEFAULT_PDF_EXTRACTOR, "mineru")


def _resolve_pdf_extractor(extractor: str | None = None) -> str:
    configured = extractor or os.environ.get(_PDF_EXTRACTOR_ENV, DEFAULT_PDF_EXTRACTOR)
    return configured.strip().lower()


def _find_pdf_attachment(zot: zotero.Zotero, item_key: str, operation: str) -> dict[str, Any] | tuple[str, Path]:
    """Locate the first PDF attachment for item_key on disk.

    Returns either an error_result dict (on failure) or (att_key, pdf_path) tuple.
    """
    from pathlib import Path as _Path
    from .connector import result_from_exception

    try:
        children = zot.children(item_key)
    except Exception as exc:
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
            operation, "locate_pdf",
            f"No PDF attachment found for item {item_key}.",
            details={"item_key": item_key},
        )

    att_data = pdf_attachment["data"]
    att_key = pdf_attachment["key"]
    filename = att_data.get("filename", "")
    if not filename:
        return error_result(
            operation, "locate_pdf",
            f"PDF attachment {att_key} has no filename recorded.",
            details={"item_key": item_key, "attachment_key": att_key},
        )

    pdf_path = _Path.home() / "Zotero" / "storage" / att_key / filename
    if not pdf_path.exists():
        return error_result(
            operation, "locate_pdf",
            f"PDF file not found on disk: {pdf_path}",
            details={"item_key": item_key, "attachment_key": att_key, "pdf_path": str(pdf_path)},
        )

    return att_key, pdf_path


def _extract_docling(pdf_path: Path, tmp_dir: Path) -> tuple[Path, str]:
    """Run docling via uvx and return (output_path, title).

    No installation required — runs via uvx.
    Requires: uvx (uv) on PATH.
    """
    import subprocess

    try:
        subprocess.run(
            [
                "uvx", "--from", "docling", "docling",
                str(pdf_path),
                "--to", "md",
                "--output", str(tmp_dir),
            ],
            capture_output=True, check=True, text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("uvx not found. Install uv: https://docs.astral.sh/uv/") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"docling exited {exc.returncode}: {exc.stderr.strip()}"
        ) from exc

    out_path = tmp_dir / (pdf_path.stem + ".md")
    if not out_path.exists():
        raise RuntimeError(
            f"docling ran but expected output not found: {out_path}"
        )
    return out_path, pdf_path.stem + "_docling.md"


def _extract_mineru(pdf_path: Path, tmp_dir: Path, *, mineru_cmd: str) -> tuple[Path, str]:
    """Run MinerU and return (output_path, title).

    MinerU must be configured separately. Set ZOTERO_MINERU_CMD to the full
    command (e.g. '/path/to/conda/envs/mineru/bin/magic-pdf' or 'magic-pdf').
    Defaults to 'magic-pdf' (old CLI) if ZOTERO_MINERU_CMD is not set.

    Install MinerU: pip install magic-pdf[full] --extra-index-url https://wheels.myhloli.com
    Or follow https://github.com/opendatalab/MinerU for GPU/model setup.
    """
    import subprocess

    try:
        subprocess.run(
            [mineru_cmd, "-p", str(pdf_path), "-o", str(tmp_dir), "-m", "auto"],
            capture_output=True, check=True, text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"MinerU command not found: {mineru_cmd!r}. "
            "Set ZOTERO_MINERU_CMD to the full path, or install magic-pdf."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"MinerU exited {exc.returncode}: {exc.stderr.strip()}"
        ) from exc

    # MinerU output structure: {tmp_dir}/{stem}/auto/{stem}.md
    stem = pdf_path.stem
    out_path = tmp_dir / stem / "auto" / (stem + ".md")
    if not out_path.exists():
        raise RuntimeError(
            f"MinerU ran but expected output not found: {out_path}"
        )
    return out_path, stem + "_mineru.md"


def extract_and_attach_text(
    zot: zotero.Zotero,
    item_key: str,
    *,
    extractor: str | None = None,
    mineru_cmd: str | None = None,
) -> dict[str, Any]:
    """Extract text from a PDF attachment and upload the result as a Markdown attachment.

    Finds the first PDF attachment child of item_key, runs the configured extractor,
    and uploads the output as a new child attachment via the configured attach endpoint.

    Args:
        zot:        Zotero client.
        item_key:   Key of the parent Zotero item.
        extractor:  Internal override for the configured extractor. Defaults to
                    ZOTERO_PDF_EXTRACTOR, then "docling".
        mineru_cmd: Internal override for the MinerU command. Defaults to the
                    ZOTERO_MINERU_CMD environment variable, then "magic-pdf".

    Returns:
        Dict with "success" bool and details. Returns a structured error if the
        PDF is missing, the extractor is not installed, or extraction fails.
    """
    operation = "extract_and_attach_text"
    selected_extractor = _resolve_pdf_extractor(extractor)

    if selected_extractor not in _EXTRACTORS:
        return error_result(
            operation, "input_validation",
            f"Unknown extractor: {selected_extractor!r}. Choose from: {', '.join(_EXTRACTORS)}",
            details={"item_key": item_key, "extractor": selected_extractor},
        )

    found = _find_pdf_attachment(zot, item_key, operation)
    if isinstance(found, dict):  # error_result
        return found
    att_key, pdf_path = found

    with tempfile.TemporaryDirectory(prefix="zotero-extract-") as tmp_str:
        tmp_dir = Path(tmp_str)
        try:
            if selected_extractor == "docling":
                out_path, title = _extract_docling(pdf_path, tmp_dir)
            else:
                cmd = mineru_cmd or os.environ.get(_MINERU_CMD_ENV, "magic-pdf")
                out_path, title = _extract_mineru(pdf_path, tmp_dir, mineru_cmd=cmd)
        except RuntimeError as exc:
            return error_result(
                operation, f"{selected_extractor}_failed",
                str(exc),
                details={
                    "item_key": item_key,
                    "pdf_path": str(pdf_path),
                    "extractor": selected_extractor,
                },
            )
        try:
            characters = out_path.stat().st_size
        except OSError as exc:
            return error_result(
                operation,
                f"{selected_extractor}_output_metadata",
                f"Could not inspect extracted output: {exc}",
                details={
                    "item_key": item_key,
                    "pdf_path": str(pdf_path),
                    "extractor": selected_extractor,
                    "output_path": str(out_path),
                    "exception_type": type(exc).__name__,
                },
            )
        upload_result = attach_file_to_item(
            zot,
            item_key,
            str(out_path),
            title=title,
            operation=operation,
        )

    if not upload_result.get("success"):
        return upload_result

    return {
        **upload_result,
        "operation": operation,
        "item_key": item_key,
        "source_pdf_key": att_key,
        "extractor": selected_extractor,
        "output_title": title,
        "characters_extracted": characters,
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


# pdf_management.pdf_processor alias — extract text and attach .txt back to the item
pdf_processor = extract_and_attach_text
