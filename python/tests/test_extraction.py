"""Tests for PDF extraction (extract_and_attach_text and extractor helpers).

Some tests require Zotero running; others test error paths only.
Tests requiring docling are skipped if that tool is absent.
"""

import os
import shutil
from pathlib import Path

import pytest

from zotero_librarian.attachments import (
    _EXTRACTORS,
    _extract_docling,
    extract_and_attach_text,
)


# ---------------------------------------------------------------------------
# Fixture PDF — one page, heading + paragraph, built with reportlab
# ---------------------------------------------------------------------------

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, "
    "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo "
    "consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse "
    "cillum dolore eu fugiat nulla pariatur."
)

# Words that must appear in any correct extraction of the fixture PDF.
EXPECTED_WORDS = {"Lorem", "ipsum", "consectetur", "adipiscing", "tempor"}


def _make_fixture_pdf(path: Path) -> None:
    """One-page PDF with a heading and a lorem ipsum paragraph via reportlab."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
    except ImportError:
        pytest.skip("reportlab not installed — cannot create fixture PDF")

    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Lorem Ipsum")
    c.setFont("Helvetica", 11)
    y = 690
    # Wrap at ~90 chars
    words = LOREM.split()
    line: list[str] = []
    for word in words:
        line.append(word)
        if len(" ".join(line)) > 85:
            c.drawString(72, y, " ".join(line[:-1]))
            y -= 16
            line = [word]
    if line:
        c.drawString(72, y, " ".join(line))
    c.save()


@pytest.fixture(scope="module")
def fixture_pdf(tmp_path_factory) -> Path:
    pdf = tmp_path_factory.mktemp("pdf") / "lorem_ipsum.pdf"
    _make_fixture_pdf(pdf)
    return pdf


# ---------------------------------------------------------------------------
# Extractor registry
# ---------------------------------------------------------------------------

class TestExtractorRegistry:
    def test_extractors_registered(self):
        assert set(_EXTRACTORS) == {"docling", "mineru"}


# ---------------------------------------------------------------------------
# Invalid extractor — no Zotero needed
# ---------------------------------------------------------------------------

class TestInvalidExtractor:
    def test_unknown_configured_extractor_returns_structured_error(self, zot):
        old_value = os.environ.get("ZOTERO_PDF_EXTRACTOR")
        os.environ["ZOTERO_PDF_EXTRACTOR"] = "magic_unicorn"
        try:
            result = extract_and_attach_text(zot, "AAAAAAAA")
        finally:
            if old_value is None:
                os.environ.pop("ZOTERO_PDF_EXTRACTOR", None)
            else:
                os.environ["ZOTERO_PDF_EXTRACTOR"] = old_value
        assert result["success"] is False
        assert result["stage"] == "input_validation"
        assert "magic_unicorn" in result["error"]

    def test_error_includes_valid_choices(self, zot):
        result = extract_and_attach_text(zot, "AAAAAAAA", extractor="bad")
        assert all(e in result["error"] for e in _EXTRACTORS)


# ---------------------------------------------------------------------------
# Item without a PDF — live Zotero, no PDF on disk needed
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def item_without_pdf(zot):
    """First journal article in the library that has no PDF child."""
    from zotero_librarian.client import _all_items
    for item in _all_items(zot, itemType="journalArticle"):
        children = zot.children(item["key"])
        has_pdf = any(
            c["data"].get("contentType") == "application/pdf" for c in children
        )
        if not has_pdf:
            return item
    pytest.skip("No journal article without a PDF found in library")


class TestNoPdfItem:
    def test_returns_locate_pdf_error(self, zot, item_without_pdf):
        result = extract_and_attach_text(zot, item_without_pdf["key"])
        assert result["success"] is False
        assert result["stage"] == "locate_pdf"

    def test_error_mentions_item_key(self, zot, item_without_pdf):
        result = extract_and_attach_text(zot, item_without_pdf["key"])
        assert item_without_pdf["key"] in result["error"] or \
               item_without_pdf["key"] in str(result.get("details", {}))


# ---------------------------------------------------------------------------
# _extract_docling — requires uvx on PATH
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def uvx_available():
    if not shutil.which("uvx"):
        pytest.skip("uvx not installed")


@pytest.mark.slow
class TestExtractDocling:
    def test_produces_md_file(self, uvx_available, fixture_pdf, tmp_path):
        out_path, _ = _extract_docling(fixture_pdf, tmp_path)
        assert out_path.exists()
        assert out_path.suffix == ".md"

    def test_title_has_docling_suffix(self, uvx_available, fixture_pdf, tmp_path):
        _, title = _extract_docling(fixture_pdf, tmp_path)
        assert title == "lorem_ipsum_docling.md"

    def test_heading_preserved_as_markdown(self, uvx_available, fixture_pdf, tmp_path):
        """Docling should extract the heading as a Markdown heading."""
        out_path, _ = _extract_docling(fixture_pdf, tmp_path)
        text = out_path.read_text()
        assert "# Lorem Ipsum" in text or "## Lorem Ipsum" in text, (
            f"Heading not found in docling output:\n{text[:500]}"
        )

    def test_output_contains_lorem_ipsum_words(self, uvx_available, fixture_pdf, tmp_path):
        out_path, _ = _extract_docling(fixture_pdf, tmp_path)
        text = out_path.read_text()
        for word in EXPECTED_WORDS:
            assert word in text, f"Expected word {word!r} not found in docling output"

    def test_missing_uvx_raises_runtime_error(self, fixture_pdf, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", "")
        with pytest.raises(RuntimeError, match="uvx not found"):
            _extract_docling(fixture_pdf, tmp_path)
