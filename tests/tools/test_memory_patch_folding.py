"""``patch`` edits the span its tolerant old_text selected, not only a byte-exact copy of it.

Regression for #138317. Entry selection folds typography (#107270): straight quotes match curly
ones, ``-`` matches a dash, and re-wrapped lines or a literal ``\\n`` still select the entry.
``patch`` selected the entry that way and then replaced only the raw ``old_text``, which is not
in the entry, so every such patch failed as "Patch is a no-op" — in a single call, in an atomic
batch, and on approval of a staged write. The patch now splices the span the folded form matched
and still refuses a span that occurs more than once.
"""

import pytest

from tools.memory_tool import MemoryStore


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.memory_tool.get_memory_dir", lambda: tmp_path)
    s = MemoryStore(memory_char_limit=500, user_char_limit=300)
    s.load_from_disk()
    return s


def test_patch_with_retyped_quotes_and_dash_edits_the_matched_span(store):
    store.add("memory", "User runs a fleet (“Omarchy” — Trinity) at home")
    result = store.patch("memory", 'fleet ("Omarchy" - Trinity)', "fleet (Zeus hub)")
    assert result["success"] is True, result
    assert store.memory_entries == ["User runs a fleet (Zeus hub) at home"]


def test_patch_with_unwrapped_text_edits_a_wrapped_entry(store):
    store.add("memory", "Tests: run make test (needs\n  docker up) before pushing")
    result = store.patch("memory", "(needs docker up)", "(needs nothing)")
    assert result["success"] is True, result
    assert store.memory_entries == ["Tests: run make test (needs nothing) before pushing"]


def test_batch_patch_with_retyped_typography_succeeds(store):
    store.add("memory", "Deploy: ‘fly deploy’ – canary first")
    result = store.apply_batch("memory", [{"action": "patch", "old_text": "'fly deploy' - canary",
                                           "content": "'fly deploy --strategy bluegreen'"}])
    assert result["success"] is True, result
    assert store.memory_entries == ["Deploy: 'fly deploy --strategy bluegreen' first"]


def test_folded_span_that_occurs_twice_is_still_refused(store):
    store.add("memory", "Ports: “a” and “a” are reserved")
    result = store.patch("memory", '"a"', "b")
    assert result["success"] is False
    assert "appears 2 times" in result["error"]
    assert store.memory_entries == ["Ports: “a” and “a” are reserved"]


def test_exact_patch_is_unchanged(store):
    store.add("memory", "Editor: vim (tabs = 4)")
    assert store.patch("memory", "tabs = 4", "tabs = 2")["success"] is True
    assert store.memory_entries == ["Editor: vim (tabs = 2)"]
