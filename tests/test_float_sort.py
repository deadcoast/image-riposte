"""Reserved user storage is outside sorting, but remains protection input."""
from pathlib import Path

import pytest

from riposte.errors import RiposteError
from riposte.intake import input_files
from riposte.organizer import audit_workspace, organize, plan, undo_sort
from riposte.policy import Policy
from riposte.terminal.service import Request, execute
from riposte.title_categories import discover_categories

POLICY = Policy(date_mode="modified", discard_sidecars=True)


def snapshot(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("categories", [False, True])
@pytest.mark.parametrize("name", ["_float_", "__float__", "_FLOAT_", "__FLOAT__"])
def test_sort_ignores_entire_float_tree_and_undo_leaves_it_alone(root, make_image, categories, name):
    held = root / "user folders" / name
    inside = make_image(held / "nested" / "private hockey painting.png")
    (held / "private.xmp").write_bytes(b"retained metadata")
    (held / "unreadable-video.mp4").write_bytes(b"not a decodable video")
    (held / "notes.txt").write_text("user-owned storage")
    (held / "empty").mkdir()
    before = snapshot(held)
    outside = make_image(root / "sort me.png")
    original = outside.read_bytes()
    preview = plan(root, POLICY, categories=categories)
    assert preview["ready"] and [f["source"] for f in preview["files"]] == [outside.name]
    assert not (root / ".riposte").exists()
    # User storage can change after preview; it is not part of sort consent.
    (held / "new note.txt").write_text("added after preview")
    before = snapshot(held)
    assert plan(root, POLICY, categories=categories)["plan_id"] == preview["plan_id"]
    result = organize(root, POLICY, categories=categories, plan_id=preview["plan_id"])
    assert result["checkpoint"] == "COMPLETE" and not outside.exists()
    assert snapshot(held) == before and (held / "empty").is_dir()
    assert audit_workspace(root)["checkpoint"] == "COMPLETE"
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert outside.read_bytes() == original and snapshot(held) == before
    files, _ = input_files([inside.parent])
    assert files == [inside]


@pytest.mark.parametrize("name", ["_float_", "__float__"])
@pytest.mark.parametrize("nested", [False, True])
@pytest.mark.parametrize("categories", [False, True])
def test_direct_float_or_descendant_cannot_be_sorted(root, make_image, name, nested, categories):
    selected = root / name / "nested" if nested else root / name
    source = make_image(selected / "painting.png")
    before = snapshot(root)
    with pytest.raises(RiposteError, match="SORT_FLOAT_ROOT"):
        plan(selected, POLICY, categories=categories)
    with pytest.raises(RiposteError, match="SORT_FLOAT_ROOT"):
        organize(selected, POLICY, categories=categories, plan_id="a" * 64)
    assert snapshot(root) == before and not (selected / ".riposte").exists()
    result = execute(Request("riposte-plan", root, {"input_paths": [selected], "edges": [64]}))
    assert result["images"] == 1 and source.exists()


@pytest.mark.parametrize("categories", [False, True])
def test_float_names_are_exact_directories_not_filename_patterns(root, make_image, categories):
    for name in ("float", "_float_backup", "___float___"):
        make_image(root / name / "painting.png")
    # An extensionless image with the reserved name is still a file, not a directory.
    source = make_image(root / "temporary.png")
    source.rename(root / "_float_")
    preview = plan(root, POLICY, categories=categories)
    assert preview["ready"] and len(preview["files"]) == 4


@pytest.mark.parametrize("categories", [False, True])
def test_renaming_to_float_after_preview_invalidates_source_consent(root, make_image, categories):
    source = make_image(root / "incoming" / "painting.png")
    preview = plan(root, POLICY, categories=categories)
    destination = root / "__float__"
    source.parent.rename(destination)
    before = snapshot(root)
    with pytest.raises(RiposteError, match="PREVIEW_CHANGED"):
        organize(root, POLICY, categories=categories, plan_id=preview["plan_id"])
    assert snapshot(root) == before and not (root / ".riposte").exists()


def test_sort_discovery_does_not_enter_float_directories(root, make_image, monkeypatch):
    make_image(root / "visible painting.png")
    for name in ("_float_", "__float__"):
        make_image(root / name / "private hockey painting.png")
    import os
    real = os.scandir

    def guarded(path):
        assert not any(p.casefold() in {"_float_", "__float__"} for p in Path(path).parts)
        return real(path)

    with monkeypatch.context() as patch:
        patch.setattr(os, "scandir", guarded)
        preview = plan(root, POLICY, categories=True)
        discovery = discover_categories(root, min_count=1)
    assert len(preview["files"]) == 1
    assert discovery["counts"]["analyzed_files"] == 1
    assert all("private" not in c["term"] and "hockey" not in c["term"] for c in discovery["candidates"])


@pytest.mark.parametrize("categories", [False, True])
def test_combined_sort_preview_uses_the_same_exclusion(root, make_image, categories):
    make_image(root / "visible.png")
    held = make_image(root / "__float__" / "held.png")
    preview = execute(Request("sort-riposte-plan", root, {"all_images": True, "categories": categories}))
    assert preview["ready"]
    assert [f["source"] for f in preview["sorting"]["files"]] == ["visible.png"]
    assert held.exists() and not (root / ".riposte").exists()


@pytest.mark.parametrize("categories", [False, True])
def test_normalized_path_outside_float_is_still_sortable(root, make_image, categories):
    (root / "_float_").mkdir()
    source = make_image(root / "ordinary" / "painting.png")
    selected = root / "_float_" / ".." / "ordinary"
    preview = plan(selected, POLICY, categories=categories)
    assert preview["ready"] and preview["files"][0]["source"] == source.name
