from __future__ import annotations

from pathlib import Path
import time
from uuid import uuid4

import pytest

from zotero_librarian.attachments import upload_pdf
from zotero_librarian.batch import batch_trash_items, batch_update_items
from zotero_librarian.collections import (
    create_collection as create_collection_entry,
    move_collection,
    rename_collection,
    trash_collection as trash_collection_entry,
)
from zotero_librarian.connector import resolve_target_id, save_item
from zotero_librarian.enrichment import batch_add_identifiers
from zotero_librarian.import_ import import_by_doi
from zotero_librarian.items import (
    add_item_to_collection,
    add_tags_to_item,
    attach_note,
    attach_url,
    move_item_to_collection,
    remove_item_from_collection,
    remove_tags_from_item,
    trash_item,
    update_item_fields,
)
from zotero_librarian.notes import trash_note, update_note
from zotero_librarian.query import get_attachments, get_item, get_notes
from zotero_librarian.tags import delete_tag, merge_tags, rename_tag


def _probe_value(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def _first_item_with_doi(zot):
    for item in zot.top(limit=100):
        doi = item.get("data", {}).get("DOI", "").strip()
        if doi:
            return item
    raise AssertionError("Expected at least one top-level item with a DOI in the local Zotero library")


def _base_item(title: str) -> dict:
    return {
        "itemType": "book",
        "title": title,
        "creators": [{"creatorType": "author", "firstName": "OpenCode", "lastName": "Probe"}],
        "date": "2026",
        "publisher": "OpenCode Test Harness",
    }


def _tag_names(item: dict) -> list[str]:
    return [
        tag.get("tag", "").strip()
        for tag in item.get("data", {}).get("tags", [])
        if tag.get("tag", "").strip()
    ]


def _is_trashed(zot, item_key: str) -> bool:
    deadline = time.monotonic() + 5.0
    while True:
        if bool(zot.item(item_key).get("data", {}).get("deleted", False)):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.25)


def _collection_key(result: dict) -> str:
    key = result.get("details", {}).get("collection_key")
    assert key, result
    return key


class WriteSandbox:
    def __init__(self, zot):
        self.zot = zot
        self.item_keys: list[str] = []
        self.collection_keys: list[str] = []

    def create_item(
        self,
        *,
        title_prefix: str = "write-contract-item",
        tags: list[str] | None = None,
        collection_key: str | None = None,
    ) -> str:
        title = _probe_value(title_prefix)
        result = save_item(
            self.zot,
            _base_item(title),
            uri=f"https://example.invalid/{uuid4().hex}",
            collection_key=collection_key,
            tags=tags,
            operation="test_write_contract_setup_item",
        )
        assert result["success"] is True, result
        item_key = result["item_key"]
        self.item_keys.append(item_key)
        return item_key

    def create_collection(self, *, name_prefix: str = "write-contract-collection", parent_key: str | None = None) -> str:
        result = create_collection_entry(self.zot, _probe_value(name_prefix), parent_key=parent_key)
        assert result["success"] is True, result
        collection_key = _collection_key(result)
        self.collection_keys.append(collection_key)
        return collection_key

    def cleanup(self) -> None:
        for item_key in reversed(self.item_keys):
            try:
                trash_item(self.zot, item_key)
            except Exception:
                pass
        for collection_key in reversed(self.collection_keys):
            try:
                trash_collection_entry(self.zot, collection_key)
            except Exception:
                pass


@pytest.fixture
def sandbox(zot):
    box = WriteSandbox(zot)
    yield box
    box.cleanup()


def test_resolve_target_id_maps_collection_key_to_connector_target(zot, sample_collection):
    target_id = resolve_target_id(zot, sample_collection["key"])

    assert target_id.startswith("C")


def test_import_by_doi_reports_explicit_lookup_failure(zot):
    missing_doi = "10.99999/opencode-zotero-plugin-definitely-missing"

    result = import_by_doi(zot, missing_doi)

    assert result["success"] is False
    assert result["operation"] == "import_by_doi"
    assert result["stage"] == "crossref_lookup"
    assert result["details"]["doi"] == missing_doi


def test_batch_add_identifiers_reports_duplicate_without_mutating(zot):
    existing_item = _first_item_with_doi(zot)
    doi = existing_item["data"]["DOI"].strip()

    result = batch_add_identifiers(zot, identifiers=[doi], id_type="doi")

    assert result["duplicate"] == 1
    assert result["failed"] == 0
    assert result["added"] == 0
    assert result["results"][0]["status"] == "duplicate"
    assert result["results"][0]["existing"]["DOI"] == doi
    assert result["results"][0]["existing"]["title"] == existing_item["data"]["title"]


def test_update_item_fields_persists_new_values(zot, sandbox):
    item_key = sandbox.create_item()
    new_title = _probe_value("updated-title")
    new_extra = _probe_value("updated-extra")

    result = update_item_fields(zot, item_key, {"title": new_title, "extra": new_extra})

    assert result["success"] is True
    assert result["stage"] == "completed"
    assert result["details"]["item_key"] == item_key
    assert result["details"]["field_names"] == ["extra", "title"]
    item = get_item(zot, item_key)
    assert item["data"]["title"] == new_title
    assert item["data"]["extra"] == new_extra


def test_add_and_remove_tags_round_trip(zot, sandbox):
    initial_tag = _probe_value("initial-tag")
    item_key = sandbox.create_item(tags=[initial_tag])
    added_tag = _probe_value("added-tag")

    add_result = add_tags_to_item(zot, item_key, [added_tag, added_tag, ""])

    assert add_result["success"] is True
    item_after_add = get_item(zot, item_key)
    assert set(_tag_names(item_after_add)) == {initial_tag, added_tag}

    remove_result = remove_tags_from_item(zot, item_key, [initial_tag])

    assert remove_result["success"] is True
    item_after_remove = get_item(zot, item_key)
    assert _tag_names(item_after_remove) == [added_tag]


def test_item_collection_assignment_round_trip(zot, sandbox):
    item_key = sandbox.create_item()
    first_collection = sandbox.create_collection(name_prefix="item-collection-a")
    second_collection = sandbox.create_collection(name_prefix="item-collection-b")

    move_result = move_item_to_collection(zot, item_key, first_collection)

    assert move_result["success"] is True
    assert get_item(zot, item_key)["data"]["collections"] == [first_collection]

    add_result = add_item_to_collection(zot, item_key, second_collection)

    assert add_result["success"] is True
    assert set(get_item(zot, item_key)["data"]["collections"]) == {first_collection, second_collection}

    remove_result = remove_item_from_collection(zot, item_key, first_collection)

    assert remove_result["success"] is True
    assert get_item(zot, item_key)["data"]["collections"] == [second_collection]


def test_attach_url_creates_link_attachment(zot, sandbox):
    item_key = sandbox.create_item()
    url = f"https://example.com/{uuid4().hex}"
    title = _probe_value("linked-url")

    result = attach_url(zot, item_key, url, title)

    assert result["success"] is True
    attachments = get_attachments(zot, item_key)
    assert any(
        attachment["key"] == result["attachment_key"]
        and attachment["data"].get("title") == title
        and attachment["data"].get("url") == url
        for attachment in attachments
    )


def test_upload_pdf_creates_pdf_attachment(zot, sandbox, tmp_path):
    item_key = sandbox.create_item()
    pdf_path = Path(tmp_path) / "write-contract-probe.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%write-contract-probe\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n")

    result = upload_pdf(zot, item_key, str(pdf_path), title="Stored PDF Probe")

    assert result["success"] is True
    attachments = get_attachments(zot, item_key)
    assert any(
        attachment["key"] == result["attachment_key"]
        and attachment["data"].get("contentType") == "application/pdf"
        and attachment["data"].get("title") == "Stored PDF Probe"
        for attachment in attachments
    )


def test_attach_and_update_note_round_trip(zot, sandbox):
    item_key = sandbox.create_item()
    initial_content = "<p>initial write-contract note</p>"
    updated_content = "<p>updated write-contract note</p>"

    attach_result = attach_note(zot, item_key, initial_content, title="Write Contract Note")

    assert attach_result["success"] is True
    note_key = attach_result["note_key"]
    notes = get_notes(zot, item_key)
    assert any(note["key"] == note_key and initial_content in note["data"].get("note", "") for note in notes)

    update_result = update_note(zot, note_key, updated_content)

    assert update_result["success"] is True
    updated_notes = get_notes(zot, item_key)
    assert any(note["key"] == note_key and updated_content in note["data"].get("note", "") for note in updated_notes)


def test_trash_note_marks_note_as_deleted(zot, sandbox):
    item_key = sandbox.create_item()
    note_key = attach_note(zot, item_key, "<p>trash me</p>")["note_key"]

    result = trash_note(zot, note_key)

    assert result["success"] is True
    assert _is_trashed(zot, note_key)


def test_trash_item_marks_item_as_deleted(zot, sandbox):
    item_key = sandbox.create_item()

    result = trash_item(zot, item_key)

    assert result["success"] is True
    assert _is_trashed(zot, item_key)


def test_batch_update_items_persists_changes_to_all_targets(zot, sandbox):
    item_keys = [sandbox.create_item(title_prefix="batch-update-a"), sandbox.create_item(title_prefix="batch-update-b")]
    short_title = _probe_value("batch-short-title")

    result = batch_update_items(zot, item_keys, {"shortTitle": short_title})

    assert sorted(result["success"]) == sorted(item_keys)
    assert result["failed"] == []
    for item_key in item_keys:
        assert get_item(zot, item_key)["data"]["shortTitle"] == short_title


def test_batch_trash_items_marks_all_targets_as_deleted(zot, sandbox):
    item_keys = [sandbox.create_item(title_prefix="batch-trash-a"), sandbox.create_item(title_prefix="batch-trash-b")]

    result = batch_trash_items(zot, item_keys)

    assert sorted(result["success"]) == sorted(item_keys)
    assert result["failed"] == []
    assert all(_is_trashed(zot, item_key) for item_key in item_keys)


def test_rename_tag_updates_existing_items(zot, sandbox):
    old_tag = _probe_value("rename-old")
    new_tag = _probe_value("rename-new")
    item_key = sandbox.create_item(tags=[old_tag])

    result = rename_tag(zot, old_tag, new_tag)

    assert result["success"] is True
    tags = set(_tag_names(get_item(zot, item_key)))
    assert new_tag in tags
    assert old_tag not in tags


def test_merge_tags_rewrites_source_tags(zot, sandbox):
    source_one = _probe_value("merge-source-a")
    source_two = _probe_value("merge-source-b")
    target_tag = _probe_value("merge-target")
    item_key = sandbox.create_item(tags=[source_one, source_two])

    result = merge_tags(zot, [source_one, source_two], target_tag)

    assert result["success"] is True
    tags = set(_tag_names(get_item(zot, item_key)))
    assert tags == {target_tag}


def test_delete_tag_removes_existing_tag_from_items(zot, sandbox):
    doomed_tag = _probe_value("delete-tag")
    keep_tag = _probe_value("keep-tag")
    item_key = sandbox.create_item(tags=[doomed_tag, keep_tag])

    result = delete_tag(zot, doomed_tag)

    assert result["success"] is True
    tags = set(_tag_names(get_item(zot, item_key)))
    assert doomed_tag not in tags
    assert keep_tag in tags


def test_create_collection_returns_collection_details(zot, sandbox):
    parent_key = sandbox.create_collection(name_prefix="parent-collection")

    result = create_collection_entry(zot, _probe_value("child-collection"), parent_key=parent_key)

    assert result["success"] is True
    child_key = _collection_key(result)
    sandbox.collection_keys.append(child_key)
    collection = zot.collection(child_key)
    assert collection["data"]["parentCollection"] == parent_key
    assert result["details"]["parent_key"] == parent_key


def test_rename_collection_updates_name(zot, sandbox):
    collection_key = sandbox.create_collection(name_prefix="rename-collection")
    new_name = _probe_value("renamed-collection")

    result = rename_collection(zot, collection_key, new_name)

    assert result["success"] is True
    collection = zot.collection(collection_key)
    assert collection["data"]["name"] == new_name
    assert result["details"]["collection_name"] == new_name


def test_move_collection_updates_parent(zot, sandbox):
    parent_key = sandbox.create_collection(name_prefix="move-parent")
    child_key = sandbox.create_collection(name_prefix="move-child")

    result = move_collection(zot, child_key, parent_key)

    assert result["success"] is True
    collection = zot.collection(child_key)
    assert collection["data"]["parentCollection"] == parent_key
    assert result["details"]["parent_key"] == parent_key
