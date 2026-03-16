"""LLM-based analysis for Zotero items."""

import datetime
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import httpx
from pyzotero import zotero

from .attachments import _extract_docling, _extract_mineru, _find_pdf_attachment, _resolve_pdf_extractor
from .connector import error_result, local_write

_TOC_INDEX_TAG = "_toc_index"


def _call_llm(text: str, model: str) -> str:
    """Call the LLM with the extracted text to generate a TOC index.

    Expects OPENCODE_LLM_API_BASE and OPENCODE_LLM_API_KEY env vars (or OpenAI defaults).
    """
    api_key = os.environ.get("OPENCODE_LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    api_base = os.environ.get(
        "OPENCODE_LLM_API_BASE",
        os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"),
    )

    prompt = (
        "Analyze the following text extracted from a document. "
        "Recognize markdown headings and fenced unit blocks (definition, theorem, lemma, proof, etc.). "
        "Output a nested bullet list where each unit is represented with a bold unit type, "
        "its label (if any), and a one-line summary. "
        "Do not include any preamble or extra text. Output only the Markdown nested bullet list.\n\n"
        f"Text:\n{text[:100000]}"
    )

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that creates structured TOC notes."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{api_base.rstrip('/')}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def generate_toc_note(
    zot: zotero.Zotero,
    item_key: str,
    *,
    model: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Generate a structured TOC note for a Zotero item.

    Steps:
      1. Resolve item PDF attachment.
      2. Extract text via configured extractor.
      3. Send to LLM with structured prompt.
      4. Write result as an HTML child note tagged _toc_index.

    Args:
        zot: Zotero client.
        item_key: Key of the parent Zotero item.
        model: LLM model identifier. Defaults to OPENCODE_LLM_MODEL env var or gpt-4o.
        force: If True, overwrite any existing TOC note.
        dry_run: If True, return a preview without writing to Zotero.

    Returns:
        Dict with operation result.
    """
    operation = "generate_toc_note"
    model = model or os.environ.get("OPENCODE_LLM_MODEL", "gpt-4o")

    try:
        item = zot.item(item_key)
    except Exception as exc:
        return error_result(operation, "fetch_item", f"Error fetching item: {exc}", details={"item_key": item_key})

    # Check for existing TOC notes
    existing_note_keys: list[str] = []
    try:
        children = zot.children(item_key)
        for child in children:
            if child.get("data", {}).get("itemType") == "note":
                tags = [t.get("tag") for t in child.get("data", {}).get("tags", [])]
                if _TOC_INDEX_TAG in tags:
                    existing_note_keys.append(child["key"])
    except Exception as exc:
        return error_result(operation, "check_children", str(exc), details={"item_key": item_key})

    if existing_note_keys and not force:
        return {
            "success": True,
            "operation": operation,
            "stage": "skip_existing",
            "message": f"TOC note already exists for {item_key}. Use --force to regenerate.",
        }

    # Resolve PDF attachment
    found = _find_pdf_attachment(zot, item_key, operation)
    if isinstance(found, dict):
        return found
    _att_key, pdf_path = found

    # Extract text via configured extractor
    selected_extractor = _resolve_pdf_extractor(None)
    with tempfile.TemporaryDirectory(prefix="zotero-analysis-") as tmp_str:
        tmp_dir = Path(tmp_str)
        try:
            if selected_extractor == "docling":
                out_path, _ = _extract_docling(pdf_path, tmp_dir)
            else:
                cmd = os.environ.get("ZOTERO_MINERU_CMD", "magic-pdf")
                out_path, _ = _extract_mineru(pdf_path, tmp_dir, mineru_cmd=cmd)
        except RuntimeError as exc:
            return error_result(
                operation,
                f"{selected_extractor}_failed",
                str(exc),
                details={
                    "item_key": item_key,
                    "pdf_path": str(pdf_path),
                    "extractor": selected_extractor,
                },
            )

        try:
            text = out_path.read_text(encoding="utf-8")
        except Exception as exc:
            return error_result(
                operation,
                "read_extracted_text",
                f"Could not read extracted text: {exc}",
                details={"item_key": item_key, "output_path": str(out_path)},
            )

    if len(text.strip()) < 100:
        return {
            "success": False,
            "operation": operation,
            "stage": "too_little_text",
            "error": "Extracted text is too short to generate a TOC note.",
        }

    if dry_run:
        return {
            "success": True,
            "operation": operation,
            "stage": "dry_run",
            "message": f"Would generate TOC note for {item_key} using model {model} (text length: {len(text)})",
            "text_preview": text[:500],
        }

    # Call LLM
    try:
        toc_content = _call_llm(text, model)
    except Exception as exc:
        return error_result(
            operation,
            "llm_call",
            f"Failed to generate TOC from LLM: {exc}",
            details={"item_key": item_key, "model": model},
        )

    # Convert markdown to simple HTML
    html_content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", toc_content)
    html_content = html_content.replace("\n", "<br/>")

    title = item.get("data", {}).get("title", "Unknown Title")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    note_html = f"<h1>TOC Index - {title} ({model}, {date_str})</h1>\n{html_content}"

    # Trash existing notes if force
    try:
        if existing_note_keys and force:
            for note_key in existing_note_keys:
                local_write("trash_item", {"item_key": note_key}, operation=operation)

        return local_write(
            "create_note",
            payload={
                "parent_item_key": item_key,
                "note_html": note_html,
                "tags": [_TOC_INDEX_TAG],
            },
            operation=operation,
        )
    except Exception as exc:
        return error_result(
            operation,
            "create_note_exception",
            str(exc),
            details={"item_key": item_key},
        )
