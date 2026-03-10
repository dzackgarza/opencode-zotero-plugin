"""
Shared pytest fixtures for zotero_librarian tests.

Live Zotero tests are automatically skipped when Zotero is not running.
"""
import pytest
from zotero_librarian.client import _all_items, get_zotero


def require_zotero():
    """Return a live Zotero client or skip when the local API is unavailable."""
    zot = get_zotero()
    try:
        zot.num_items()
    except Exception as exc:
        pytest.skip(
            "Zotero local API is unavailable. "
            "Start Zotero 7+ and enable: Edit → Settings → Advanced → "
            "'Allow other applications to communicate with Zotero'. "
            f"Underlying error: {exc}"
        )
    return zot


@pytest.fixture(scope="session")
def zot():
    """Live Zotero client (session-scoped)."""
    return require_zotero()


@pytest.fixture(scope="session")
def all_items_list(zot):
    """All library items, loaded only for tests that explicitly request them."""
    return list(_all_items(zot))


@pytest.fixture(scope="session")
def first_item(zot):
    """First top-level item for single-item tests."""
    return zot.top(limit=1)[0]


@pytest.fixture(scope="session")
def sample_collection(zot):
    """First non-empty collection for bounded live tests."""
    for collection in zot.collections():
        if zot.collection_items_top(collection["key"], limit=1):
            return collection
    raise AssertionError("Expected at least one non-empty Zotero collection for bounded live tests")


@pytest.fixture(scope="session")
def sample_collection_items(zot, sample_collection):
    """Top-level items from the sample collection."""
    return zot.collection_items_top(sample_collection["key"])
