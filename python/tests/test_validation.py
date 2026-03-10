"""Tests for validation — offline (no Zotero needed)."""
from zotero_librarian.validation import validate_doi, validate_isbn, validate_issn


class TestValidateDoi:
    def test_valid(self):
        assert validate_doi("10.1000/test") is True
        assert validate_doi("10.1371/journal.pone.0123456") is True

    def test_invalid(self):
        assert validate_doi("invalid") is False
        assert validate_doi("doi:10.1000/test") is False
        assert validate_doi("") is False


class TestValidateIsbn:
    def test_valid_isbn13(self):
        assert validate_isbn("9780123456789") is True
        assert validate_isbn("978-0-12-345678-9") is True

    def test_valid_isbn10(self):
        assert validate_isbn("0123456789") is True

    def test_invalid(self):
        assert validate_isbn("invalid") is False
        assert validate_isbn("12345") is False


class TestValidateIssn:
    def test_valid(self):
        assert validate_issn("1234-5678") is True

    def test_invalid(self):
        assert validate_issn("invalid") is False
        assert validate_issn("12345678") is False
