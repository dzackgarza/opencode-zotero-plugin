from __future__ import annotations

import os
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml


_CONFIG_ENV_VAR = "ZOTERO_LIBRARIAN_CONFIG"
_CONFIG_RESOURCE = "config.yaml"


def _config_source() -> tuple[str, str]:
    override_path = os.environ.get(_CONFIG_ENV_VAR)
    if override_path:
        return "path", str(Path(override_path).expanduser())
    return "resource", _CONFIG_RESOURCE


def _read_config_text() -> tuple[str, str]:
    source_kind, source_value = _config_source()
    if source_kind == "path":
        config_path = Path(source_value)
        return str(config_path), config_path.read_text(encoding="utf-8")
    resource = files("zotero_librarian").joinpath(source_value)
    return f"package:{source_value}", resource.read_text(encoding="utf-8")


def _require_mapping(value: Any, *, path: str, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected mapping at {path!r} in {source}")
    return value


def _require_string(value: Any, *, path: str, source: str) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Expected non-empty string at {path!r} in {source}")
    return value


def _require_float(value: Any, *, path: str, source: str) -> float:
    if not isinstance(value, (int, float)):
        raise RuntimeError(f"Expected number at {path!r} in {source}")
    return float(value)


def _require_int(value: Any, *, path: str, source: str) -> int:
    if not isinstance(value, int):
        raise RuntimeError(f"Expected integer at {path!r} in {source}")
    return value


@lru_cache(maxsize=1)
def _settings() -> tuple[str, dict[str, Any]]:
    source, raw_text = _read_config_text()
    parsed = yaml.safe_load(raw_text)
    settings = _require_mapping(parsed, path="$", source=source)
    return source, settings


def _section(name: str) -> tuple[str, dict[str, Any]]:
    source, settings = _settings()
    return source, _require_mapping(settings.get(name), path=name, source=source)


def connector_base_url() -> str:
    source, section = _section("connector")
    return _require_string(section.get("base_url"), path="connector.base_url", source=source)


def connector_timeout_seconds() -> float:
    source, section = _section("connector")
    return _require_float(section.get("timeout_seconds"), path="connector.timeout_seconds", source=source)


def connector_poll_attempts() -> int:
    source, section = _section("connector")
    return _require_int(section.get("poll_attempts"), path="connector.poll_attempts", source=source)


def connector_poll_delay_seconds() -> float:
    source, section = _section("connector")
    return _require_float(section.get("poll_delay_seconds"), path="connector.poll_delay_seconds", source=source)


def plugin_minimum_version() -> str:
    source, section = _section("plugin")
    return _require_string(section.get("minimum_version"), path="plugin.minimum_version", source=source)


def plugin_version_probe_path() -> str:
    source, section = _section("plugin")
    return _require_string(section.get("version_probe_path"), path="plugin.version_probe_path", source=source)


def plugin_fallback_endpoint_path(endpoint_name: str) -> str:
    source, section = _section("plugin")
    fallback_endpoints = _require_mapping(
        section.get("fallback_endpoints"),
        path="plugin.fallback_endpoints",
        source=source,
    )
    return _require_string(
        fallback_endpoints.get(endpoint_name),
        path=f"plugin.fallback_endpoints.{endpoint_name}",
        source=source,
    )


def fulltext_allowed_dirs() -> tuple[Path, ...]:
    source, section = _section("fulltext_attach")
    raw_dirs = section.get("allowed_dirs")
    if not isinstance(raw_dirs, list) or not raw_dirs:
        raise RuntimeError(f"Expected non-empty list at 'fulltext_attach.allowed_dirs' in {source}")
    paths: list[Path] = []
    for index, raw_dir in enumerate(raw_dirs):
        raw_path = _require_string(
            raw_dir,
            path=f"fulltext_attach.allowed_dirs[{index}]",
            source=source,
        )
        paths.append(Path(raw_path))
    return tuple(paths)
