"""Better BibTeX citation key ↔ Zotero item key lookup.

Requires the Better BibTeX plugin installed in Zotero.
Calls the JSON-RPC endpoint at http://127.0.0.1:23119/better-bibtex/json-rpc.
"""

from __future__ import annotations

from typing import Any

import httpx

from .connector import CONNECTOR_BASE_URL, CONNECTOR_TIMEOUT, error_result

_BBT_RPC_URL = f"{CONNECTOR_BASE_URL}/better-bibtex/json-rpc"
_BBT_UNAVAILABLE_MSG = (
    "The Better BibTeX JSON-RPC endpoint is not reachable. "
    "Ensure Better BibTeX is installed and Zotero is running."
)


def _bbt_rpc(method: str, params: list[Any], *, operation: str) -> dict[str, Any]:
    """Call a Better BibTeX JSON-RPC method. Returns the raw response dict."""
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    try:
        response = httpx.post(_BBT_RPC_URL, json=payload, timeout=CONNECTOR_TIMEOUT)
    except httpx.HTTPError as exc:
        return error_result(
            operation,
            "bbt_rpc_request",
            _BBT_UNAVAILABLE_MSG,
            details={"method": method, "exception_type": type(exc).__name__},
        )
    if response.status_code >= 400:
        return error_result(
            operation,
            "bbt_rpc_status",
            "Better BibTeX JSON-RPC returned an unexpected HTTP status.",
            details={"method": method, "status_code": response.status_code, "body": response.text},
        )
    try:
        data = response.json()
    except ValueError:
        return error_result(
            operation,
            "bbt_rpc_parse",
            "Better BibTeX JSON-RPC returned non-JSON response.",
            details={"method": method, "status_code": response.status_code, "body": response.text},
        )
    if "error" in data:
        return error_result(
            operation,
            "bbt_rpc_error",
            f"Better BibTeX JSON-RPC error: {data['error'].get('message', data['error'])}",
            details={"method": method, "rpc_error": data["error"]},
        )
    return {"success": True, "result": data.get("result")}


def _extract_item_key_from_uri(uri: str) -> str | None:
    """Extract Zotero item key from a URI like http://zotero.org/users/NNN/items/XXXXXXXX."""
    parts = uri.rstrip("/").split("/")
    if parts and parts[-1]:
        return parts[-1]
    return None


def _lookup_citekey(citekey: str, *, operation: str) -> dict[str, Any]:
    """Look up a Zotero item key given a Better BibTeX citation key.

    Args:
        citekey: BibTeX citation key (e.g. "smith2020foo")

    Returns:
        dict with success, zotero_key, and citekey on success;
        or error dict if Better BibTeX is unavailable or key not found.
    """
    rpc = _bbt_rpc("item.search", [citekey], operation=operation)
    if not rpc.get("success"):
        return rpc

    results = rpc["result"] or []
    for item in results:
        item_citekey = item.get("citekey") or item.get("citation-key") or ""
        if item_citekey == citekey:
            uri = item.get("id", "")
            zotero_key = _extract_item_key_from_uri(uri)
            if not zotero_key:
                return error_result(
                    operation,
                    "parse_uri",
                    f"Could not extract Zotero key from URI: {uri!r}",
                    details={"citekey": citekey, "uri": uri},
                )
            return {
                "success": True,
                "operation": operation,
                "zotero_key": zotero_key,
                "citekey": citekey,
                "title": item.get("title"),
                "type": item.get("type"),
            }

    return error_result(
        operation,
        "not_found",
        f"No item found with citation key: {citekey!r}",
        details={"citekey": citekey, "search_results": len(results)},
    )


def lookup(citekey: str) -> dict[str, Any]:
    """Look up a Zotero item key given a Better BibTeX citation key."""
    return _lookup_citekey(citekey, operation="lookup")


def lookup_citekey(citekey: str) -> dict[str, Any]:
    """Backward-compatible alias for Better BibTeX citekey lookup."""
    return _lookup_citekey(citekey, operation="lookup_citekey")


def lookup_zotero_key(zotero_key: str) -> dict[str, Any]:
    """Look up the Better BibTeX citation key for a given Zotero item key.

    Args:
        zotero_key: Zotero item key (e.g. "VNPN6FHT")

    Returns:
        dict with success, zotero_key, and citekey on success;
        or error dict if Better BibTeX is unavailable or key not found.
    """
    operation = "lookup_zotero_key"

    rpc = _bbt_rpc("item.citationkey", [[zotero_key]], operation=operation)
    if not rpc.get("success"):
        return rpc

    mapping = rpc["result"] or {}
    citekey = mapping.get(zotero_key)
    if not citekey:
        return error_result(
            operation,
            "not_found",
            f"No citation key found for Zotero key: {zotero_key!r}",
            details={"zotero_key": zotero_key},
        )

    return {
        "success": True,
        "operation": operation,
        "zotero_key": zotero_key,
        "citekey": citekey,
    }
