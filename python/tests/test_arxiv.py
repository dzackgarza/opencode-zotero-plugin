"""Tests for arxiv module. Requires arxiv dependencies; skipped otherwise."""
import pytest
from pathlib import Path
import tempfile
import shutil

arxiv_mod = pytest.importorskip("zotero_librarian.arxiv")

from zotero_librarian.arxiv import (
    search_arxiv_papers,
    download_arxiv_paper,
    list_downloaded_papers,
    read_arxiv_paper,
    get_arxiv_paper_metadata,
    _validate_categories,
    export_papers_to_json,
    import_papers_from_json,
)


class TestValidateCategories:
    def test_valid(self):
        assert _validate_categories(["cs.AI", "cs.LG"]) is True

    def test_invalid(self):
        assert _validate_categories(["invalid.category"]) is False

    def test_empty(self):
        assert _validate_categories([]) is True


class TestSearchArxivPapers:
    def test_basic_search(self):
        results = search_arxiv_papers("quantum computing", max_results=5)
        assert len(results) > 0
        assert "id" in results[0] and "title" in results[0]

    def test_required_fields(self):
        results = search_arxiv_papers("deep learning", max_results=1)
        for field in ["id", "title", "authors", "abstract", "categories", "published", "url"]:
            assert field in results[0]


class TestGetPaperMetadata:
    def test_valid(self):
        meta = get_arxiv_paper_metadata("1706.03762")
        assert meta is not None and "title" in meta

    def test_invalid(self):
        assert get_arxiv_paper_metadata("invalid-id-99999") is None


class TestReadPaper:
    @pytest.fixture
    def tmp(self):
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d)

    def test_missing(self, tmp):
        result = read_arxiv_paper("1706.03762", output_dir=tmp)
        assert result["success"] is False

    def test_existing(self, tmp):
        content = "# Test\n\nContent."
        Path(tmp, "1706.03762.md").write_text(content)
        result = read_arxiv_paper("1706.03762", output_dir=tmp)
        assert result["success"] is True
        assert result["content"] == content


class TestExportImport:
    @pytest.fixture
    def tmp_file(self):
        import tempfile
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        path = f.name
        f.close()
        yield path
        Path(path).unlink(missing_ok=True)

    def test_roundtrip(self, tmp_file):
        papers = [{"id": "1706.03762", "title": "A"}, {"id": "1810.04805", "title": "B"}]
        export_papers_to_json(papers, tmp_file)
        imported = import_papers_from_json(tmp_file)
        assert len(imported) == 2
        assert imported[0]["id"] == "1706.03762"
