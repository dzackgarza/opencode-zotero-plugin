"""Tests for Better BibTeX citation key ↔ Zotero key lookup.

Requires Zotero running with Better BibTeX installed.
Auto-skipped when the BBT endpoint is unreachable.
"""

import pytest
import httpx

from zotero_librarian._cli import build_parser
from zotero_librarian.lookup import lookup, lookup_citekey, lookup_zotero_key


BBT_RPC_URL = "http://127.0.0.1:23119/better-bibtex/json-rpc"


def require_bbt():
    """Return (zotero_key, citekey) for one real item, or skip if BBT is down."""
    try:
        resp = httpx.post(
            BBT_RPC_URL,
            json={"jsonrpc": "2.0", "method": "item.search", "params": ["a"], "id": 1},
            timeout=5.0,
        )
        resp.raise_for_status()
        results = resp.json().get("result") or []
    except Exception as exc:
        pytest.skip(f"Better BibTeX endpoint not reachable: {exc}")

    if not results:
        pytest.skip("Better BibTeX returned no items to test against")

    item = results[0]
    uri = item.get("id", "")
    zotero_key = uri.rstrip("/").split("/")[-1]
    citekey = item.get("citekey") or item.get("citation-key") or ""
    if not zotero_key or not citekey:
        pytest.skip("First BBT result missing zotero_key or citekey")

    return zotero_key, citekey


@pytest.fixture(scope="module")
def bbt_item():
    """Real (zotero_key, citekey) pair from the live library."""
    return require_bbt()


class TestLookupZoteroKey:
    def test_known_key_returns_citekey(self, bbt_item):
        zotero_key, expected_citekey = bbt_item
        result = lookup_zotero_key(zotero_key)
        assert result["success"] is True
        assert result["zotero_key"] == zotero_key
        assert result["citekey"] == expected_citekey

    def test_nonexistent_key_returns_error(self):
        result = lookup_zotero_key("ZZZZZZZZ")
        assert result["success"] is False
        assert result["stage"] == "not_found"
        assert "ZZZZZZZZ" in result["error"]

    def test_result_structure(self, bbt_item):
        zotero_key, _ = bbt_item
        result = lookup_zotero_key(zotero_key)
        assert "operation" in result
        assert result["operation"] == "lookup_zotero_key"


class TestLookupCitekey:
    def test_primary_lookup_returns_zotero_key(self, bbt_item):
        expected_zotero_key, citekey = bbt_item
        result = lookup(citekey)
        assert result["success"] is True
        assert result["operation"] == "lookup"
        assert result["zotero_key"] == expected_zotero_key
        assert result["citekey"] == citekey

    def test_known_citekey_returns_zotero_key(self, bbt_item):
        expected_zotero_key, citekey = bbt_item
        result = lookup_citekey(citekey)
        assert result["success"] is True
        assert result["zotero_key"] == expected_zotero_key
        assert result["citekey"] == citekey

    def test_nonexistent_citekey_returns_error(self):
        result = lookup_citekey("xyzzy_totally_nonexistent_key_999")
        assert result["success"] is False
        assert result["stage"] == "not_found"

    def test_result_includes_title_and_type(self, bbt_item):
        _, citekey = bbt_item
        result = lookup_citekey(citekey)
        assert result["success"] is True
        assert "title" in result
        assert "type" in result

    def test_result_structure(self, bbt_item):
        _, citekey = bbt_item
        result = lookup_citekey(citekey)
        assert result["operation"] == "lookup_citekey"


class TestRoundTrip:
    def test_zotero_key_round_trip(self, bbt_item):
        """lookup_zotero_key then lookup_citekey returns original zotero_key."""
        zotero_key, _ = bbt_item
        citekey_result = lookup_zotero_key(zotero_key)
        assert citekey_result["success"] is True

        back = lookup_citekey(citekey_result["citekey"])
        assert back["success"] is True
        assert back["zotero_key"] == zotero_key

    def test_citekey_round_trip(self, bbt_item):
        """lookup_citekey then lookup_zotero_key returns original citekey."""
        _, citekey = bbt_item
        key_result = lookup_citekey(citekey)
        assert key_result["success"] is True

        back = lookup_zotero_key(key_result["zotero_key"])
        assert back["success"] is True
        assert back["citekey"] == citekey


class TestLookupCli:
    def test_lookup_defaults_to_citekey_mode(self):
        args = build_parser().parse_args(["lookup", "smith2020foo"])
        assert args.command == "lookup"
        assert args.identifier == "smith2020foo"
        assert args.zotero_key is False

    def test_lookup_supports_reverse_flag(self):
        args = build_parser().parse_args(["lookup", "VNPN6FHT", "--zotero-key"])
        assert args.command == "lookup"
        assert args.identifier == "VNPN6FHT"
        assert args.zotero_key is True
