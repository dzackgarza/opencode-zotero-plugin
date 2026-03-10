"""Tests for the _dispatch CLI — offline (no Zotero needed)."""
import json
import subprocess
import sys
from pathlib import Path

from zotero_librarian.client import count_items

PYTHON_SRC = Path(__file__).parent.parent / "src"


def run_dispatch(tool_name: str, args: dict) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "zotero_librarian._dispatch", tool_name, json.dumps(args)],
        cwd=str(PYTHON_SRC),
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(PYTHON_SRC)},
    )
    output = result.stdout.strip()
    if not output:
        output = result.stderr.strip()
    return json.loads(output)


class TestDispatchOffline:
    def test_unknown_tool_returns_error(self):
        data = run_dispatch("nonexistent_tool", {})
        assert "error" in data

    def test_count_items_matches_live_local_api(self, zot):
        assert run_dispatch("count_items", {}) == count_items(zot)

    def test_get_item_matches_live_local_api(self, first_item):
        data = run_dispatch("get_item", {"item_key": first_item["key"]})
        assert data["key"] == first_item["key"]
        assert data["data"]["title"] == first_item["data"]["title"]
