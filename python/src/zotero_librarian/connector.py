from __future__ import annotations

import secrets
import time
from collections import defaultdict
from typing import Any

import httpx
from pyzotero import zotero


CONNECTOR_BASE_URL = "http://127.0.0.1:23119"
CONNECTOR_TIMEOUT = 30.0
CONNECTOR_POLL_ATTEMPTS = 20
CONNECTOR_POLL_DELAY = 0.25
FULLTEXT_ATTACH_PATH = "/fulltext-attach"
LOCAL_WRITE_PATH = "/opencode-zotero-write"
PLUGIN_VERSION_PATH = "/opencode-zotero-plugin-version"
MIN_LOCAL_PLUGIN_VERSION = "3.1"


class ConnectorWriteError(RuntimeError):
    def __init__(
        self,
        operation: str,
        stage: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.stage = stage
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": False,
            "operation": self.operation,
            "stage": self.stage,
            "error": str(self),
            "details": self.details,
        }


def error_result(
    operation: str,
    stage: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ConnectorWriteError(
        operation=operation,
        stage=stage,
        message=message,
        details=details,
    ).to_dict()


def result_from_exception(operation: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, ConnectorWriteError):
        return exc.to_dict()
    return error_result(
        operation=operation,
        stage="unexpected_exception",
        message=str(exc),
        details={"exception_type": type(exc).__name__},
    )


def endpoint_url(path: str) -> str:
    return f"{CONNECTOR_BASE_URL}{path}"


def _parse_release_version(version: str) -> tuple[int, ...]:
    parts = version.strip().split(".")
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"Invalid release version: {version}")
    return tuple(int(part) for part in parts)


def get_local_plugin_info(*, operation: str = "local_plugin_info") -> dict[str, Any]:
    try:
        response = httpx.get(
            endpoint_url(PLUGIN_VERSION_PATH),
            timeout=CONNECTOR_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_probe",
            message=f"Could not reach {PLUGIN_VERSION_PATH} on the local Zotero server",
            details={"endpoint": PLUGIN_VERSION_PATH, "exception_type": type(exc).__name__},
        ) from exc

    if response.status_code == 404 and "No endpoint found" in response.text:
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_probe",
            message="The local Zotero add-on is too old or missing the version probe endpoint.",
            details={
                "endpoint": PLUGIN_VERSION_PATH,
                "status_code": response.status_code,
                "body": response.text,
                "minimum_required_version": MIN_LOCAL_PLUGIN_VERSION,
            },
        )
    if response.status_code != 200:
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_probe",
            message="The local Zotero add-on version probe returned an unexpected status.",
            details={
                "endpoint": PLUGIN_VERSION_PATH,
                "status_code": response.status_code,
                "body": response.text,
            },
        )

    try:
        response_data = response.json()
    except ValueError as exc:
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_probe",
            message="The local Zotero add-on version probe did not return valid JSON.",
            details={"endpoint": PLUGIN_VERSION_PATH, "body": response.text},
        ) from exc
    if not isinstance(response_data, dict):
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_probe",
            message="The local Zotero add-on version probe did not return an object response.",
            details={"endpoint": PLUGIN_VERSION_PATH, "body": response.text},
        )

    installed_version = response_data.get("version")
    if not isinstance(installed_version, str) or not installed_version.strip():
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_probe",
            message="The local Zotero add-on version probe did not include a usable version string.",
            details={"endpoint": PLUGIN_VERSION_PATH, "response": response_data},
        )
    return response_data


def require_local_plugin_version(
    minimum_version: str = MIN_LOCAL_PLUGIN_VERSION,
    *,
    operation: str,
) -> dict[str, Any]:
    plugin_info = get_local_plugin_info(operation=operation)
    installed_version = plugin_info["version"]
    try:
        installed_parts = _parse_release_version(installed_version)
        minimum_parts = _parse_release_version(minimum_version)
    except ValueError as exc:
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_requirement",
            message=str(exc),
            details={
                "installed_version": installed_version,
                "minimum_required_version": minimum_version,
            },
        ) from exc

    if installed_parts < minimum_parts:
        raise ConnectorWriteError(
            operation=operation,
            stage="plugin_version_requirement",
            message=(
                f"The local Zotero add-on is too old ({installed_version}); "
                f"{minimum_version}+ is required."
            ),
            details={
                "installed_version": installed_version,
                "minimum_required_version": minimum_version,
                "update_url": plugin_info.get("update_url"),
            },
        )
    return plugin_info


def matching_items(zot: zotero.Zotero, item: dict[str, Any]) -> list[dict[str, Any]]:
    if item.get("DOI"):
        return [
            entry
            for entry in zot.items(q=item["DOI"], qmode="everything", limit=50)
            if entry.get("data", {}).get("DOI", "") == item["DOI"]
        ]
    if item.get("ISBN"):
        return [
            entry
            for entry in zot.items(q=item["ISBN"], qmode="everything", limit=50)
            if entry.get("data", {}).get("ISBN", "") == item["ISBN"]
        ]
    title = item.get("title", "")
    if not title:
        return []
    return [
        entry
        for entry in zot.items(q=title, qmode="titleCreatorYear", limit=50)
        if entry.get("data", {}).get("title", "") == title
    ]


def matching_item_keys(zot: zotero.Zotero, item: dict[str, Any]) -> set[str]:
    return {entry["key"] for entry in matching_items(zot, item)}


def _post_json(
    path: str,
    payload: dict[str, Any],
    *,
    operation: str,
    stage: str,
) -> httpx.Response:
    try:
        response = httpx.post(
            endpoint_url(path),
            json=payload,
            timeout=CONNECTOR_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise ConnectorWriteError(
            operation=operation,
            stage=stage,
            message=f"Connector request failed for {path}",
            details={"path": path, "payload": payload, "exception_type": type(exc).__name__},
        ) from exc
    return response


def _connector_metadata() -> dict[str, Any]:
    operation = "connector_metadata"
    response = _post_json(
        "/connector/getSelectedCollection",
        {},
        operation=operation,
        stage="request",
    )
    if response.status_code != 200:
        raise ConnectorWriteError(
            operation=operation,
            stage="request",
            message="Connector did not return selected-collection metadata",
            details={"status_code": response.status_code, "body": response.text},
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ConnectorWriteError(
            operation=operation,
            stage="parse_response",
            message="Connector selected-collection response was not valid JSON",
            details={"body": response.text},
        ) from exc


def _local_collection_paths(zot: zotero.Zotero) -> dict[str, tuple[str, ...]]:
    collections = list(zot.collections())
    data_by_key = {collection["key"]: collection["data"] for collection in collections}

    def build_path(collection_key: str) -> tuple[str, ...]:
        names: list[str] = []
        current_key: str | bool = collection_key
        while current_key:
            collection_data = data_by_key[current_key]
            names.append(collection_data["name"])
            current_key = collection_data.get("parentCollection", False)
        return tuple(reversed(names))

    return {collection_key: build_path(collection_key) for collection_key in data_by_key}


def _connector_collection_targets() -> dict[tuple[str, ...], list[str]]:
    metadata = _connector_metadata()
    targets = metadata.get("targets", [])
    stack: list[str] = []
    targets_by_path: dict[tuple[str, ...], list[str]] = defaultdict(list)

    for target in targets:
        level = int(target.get("level", 0))
        stack = stack[:level]
        stack.append(target["name"])
        target_id = target["id"]
        if target_id.startswith("C"):
            targets_by_path[tuple(stack[1:])].append(target_id)
    return dict(targets_by_path)


def current_library_target_id() -> str:
    metadata = _connector_metadata()
    library_target_id = f"L{metadata['libraryID']}"
    return library_target_id


def resolve_target_id(zot: zotero.Zotero, collection_key: str) -> str:
    local_paths = _local_collection_paths(zot)
    if collection_key not in local_paths:
        raise ConnectorWriteError(
            operation="resolve_target_id",
            stage="lookup_collection_key",
            message=f"Collection key not found: {collection_key}",
            details={"collection_key": collection_key},
        )

    collection_path = local_paths[collection_key]
    connector_targets = _connector_collection_targets()
    matches = connector_targets.get(collection_path, [])
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ConnectorWriteError(
            operation="resolve_target_id",
            stage="match_connector_target",
            message=f"Could not match collection key {collection_key} to a connector target",
            details={"collection_key": collection_key, "collection_path": list(collection_path)},
        )
    raise ConnectorWriteError(
        operation="resolve_target_id",
        stage="match_connector_target",
        message=f"Collection key {collection_key} matched multiple connector targets",
        details={
            "collection_key": collection_key,
            "collection_path": list(collection_path),
            "matches": matches,
        },
    )


def _poll_created_item_key(
    zot: zotero.Zotero,
    item: dict[str, Any],
    before_keys: set[str],
    *,
    operation: str,
) -> str:
    for _ in range(CONNECTOR_POLL_ATTEMPTS):
        for entry in matching_items(zot, item):
            if entry["key"] not in before_keys:
                return entry["key"]
        time.sleep(CONNECTOR_POLL_DELAY)
    raise ConnectorWriteError(
        operation=operation,
        stage="locate_saved_item",
        message="Connector save succeeded but the new local Zotero item could not be located",
        details={"title": item.get("title", ""), "doi": item.get("DOI", ""), "isbn": item.get("ISBN", "")},
    )


def _update_session(
    *,
    session_id: str,
    target: str,
    operation: str,
    tags: list[str] | None = None,
    note: str | None = None,
) -> None:
    payload: dict[str, Any] = {"sessionID": session_id, "target": target}
    if tags:
        payload["tags"] = tags
    if note is not None:
        payload["note"] = note

    response = _post_json(
        "/connector/updateSession",
        payload,
        operation=operation,
        stage="update_session",
    )
    if response.status_code != 200:
        raise ConnectorWriteError(
            operation=operation,
            stage="update_session",
            message="Connector session update failed",
            details={"status_code": response.status_code, "body": response.text, "target": target},
        )


def save_item(
    zot: zotero.Zotero,
    item: dict[str, Any],
    *,
    uri: str,
    collection_key: str | None = None,
    tags: list[str] | None = None,
    note: str | None = None,
    operation: str = "save_item",
) -> dict[str, Any]:
    before_keys = matching_item_keys(zot, item)
    session_id = secrets.token_hex(8)
    connector_item = item.copy()
    connector_item["id"] = connector_item.get("id") or secrets.token_hex(8)

    response = _post_json(
        "/connector/saveItems",
        {"sessionID": session_id, "items": [connector_item], "uri": uri},
        operation=operation,
        stage="save_items",
    )
    if response.status_code != 201:
        raise ConnectorWriteError(
            operation=operation,
            stage="save_items",
            message="Connector saveItems request failed",
            details={"status_code": response.status_code, "body": response.text},
        )

    item_key = _poll_created_item_key(zot, item, before_keys, operation=operation)

    if collection_key or tags or note is not None:
        target = resolve_target_id(zot, collection_key) if collection_key else current_library_target_id()
        _update_session(
            session_id=session_id,
            target=target,
            operation=operation,
            tags=tags,
            note=note,
        )

    return {
        "success": True,
        "operation": operation,
        "stage": "completed",
        "item_key": item_key,
        "session_id": session_id,
    }


def import_text(
    payload: str,
    *,
    operation: str = "import_text",
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    response = httpx.post(
        f"{CONNECTOR_BASE_URL}/connector/import",
        params={"session": session_id or secrets.token_hex(8)},
        content=payload.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=CONNECTOR_TIMEOUT,
    )
    if response.status_code != 201:
        raise ConnectorWriteError(
            operation=operation,
            stage="connector_import",
            message="Connector import request failed",
            details={"status_code": response.status_code, "body": response.text},
        )
    try:
        imported = response.json()
    except ValueError as exc:
        raise ConnectorWriteError(
            operation=operation,
            stage="parse_response",
            message="Connector import response was not valid JSON",
            details={"body": response.text},
        ) from exc
    if not isinstance(imported, list):
        raise ConnectorWriteError(
            operation=operation,
            stage="parse_response",
            message="Connector import response did not return an item list",
            details={"body": response.text},
        )
    return imported


def local_write(
    endpoint_operation: str,
    *,
    payload: dict[str, Any] | None = None,
    operation: str | None = None,
) -> dict[str, Any]:
    result_operation = operation or endpoint_operation
    request_payload = {"operation": endpoint_operation}
    if payload:
        request_payload.update(payload)

    try:
        plugin_info = require_local_plugin_version(operation=result_operation)
    except ConnectorWriteError as exc:
        return exc.to_dict()

    response = _post_json(
        LOCAL_WRITE_PATH,
        request_payload,
        operation=result_operation,
        stage="local_write_request",
    )
    if response.status_code == 404 and "No endpoint found" in response.text:
        return error_result(
            result_operation,
            "local_write_endpoint",
            "The /opencode-zotero-write Zotero plugin endpoint is not available.",
            details={
                "endpoint_operation": endpoint_operation,
                "status_code": response.status_code,
                "body": response.text,
            },
        )
    try:
        response_data = response.json()
    except ValueError:
        return error_result(
            result_operation,
            "parse_response",
            "The local write endpoint did not return valid JSON.",
            details={
                "endpoint_operation": endpoint_operation,
                "status_code": response.status_code,
                "body": response.text,
            },
        )
    if not isinstance(response_data, dict):
        return error_result(
            result_operation,
            "parse_response",
            "The local write endpoint did not return an object response.",
            details={
                "endpoint_operation": endpoint_operation,
                "status_code": response.status_code,
                "body": response.text,
            },
        )

    normalized = dict(response_data)
    normalized["operation"] = result_operation
    normalized.setdefault("details", {})
    normalized.setdefault("version", plugin_info["version"])
    if normalized.get("success"):
        normalized.setdefault("stage", "completed")
        return normalized

    normalized.setdefault("stage", "local_write_endpoint")
    normalized.setdefault(
        "error",
        f"The local write endpoint reported a failure for {result_operation}.",
    )
    return normalized
