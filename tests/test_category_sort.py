"""Exact category consent, private provenance and transactional undo regressions."""
import contextlib
import json
import os
from pathlib import Path

import pytest

from riposte.category_rules import build_rules, load_rules, save_rules
from riposte.errors import RiposteError
from riposte.organizer import organize, plan, audit_workspace, undo_sort
from riposte.policy import Policy, canonical_path
from riposte.sort_history import latest_sort
from riposte.sort_titles import title_records, save_title
from riposte.store import catalog, connect

POLICY = Policy(date_mode="modified")


def rules(root, *specs):
    return save_rules(root, build_rules(specs or ("Hockey=hockey;goalie",)), expected_revision=load_rules(root).revision)


def apply(root, **kwargs):
    preview = plan(root, POLICY, categories=True, **kwargs)
    assert preview["ready"], preview
    return organize(root, POLICY, categories=True, plan_id=preview["plan_id"], **kwargs)


def test_exact_preview_readonly_and_missing_consent(root, make_image):
    image = make_image(root / "hockey-slapshot.png")
    before = image.read_bytes()
    p = plan(root, POLICY, categories=True)
    assert not (root / ".riposte").exists()
    assert p["files"][0]["destination"] == "2025/March/img/uncategorized/SML/SML01.png"
    assert p == plan(root, POLICY, categories=True)
    assert p["counts"]["unmatched_files"] == 1
    with pytest.raises(RiposteError, match="CATEGORY_PREVIEW_REQUIRED"):
        organize(root, POLICY, categories=True)
    assert not (root / ".riposte").exists() and image.read_bytes() == before


def test_sort_original_title_private_stable_repeat_and_exact_undo(root, make_image):
    rules(root)
    image = make_image(root / "winter-HOCKEY-goalie-practice.png")
    before = image.read_bytes()
    p = plan(root, POLICY, categories=True)
    assert p["files"][0]["matched_terms"] == ["goalie", "hockey"]
    assert p["files"][0]["destination"] == "2025/March/img/hockey/SML/SML01.png"
    assert apply(root)["checkpoint"] == "COMPLETE"
    rows, titles = catalog(root), title_records(root)
    assert titles[0]["original_filename"] == image.name
    assert "original_filename" not in rows[0]
    assert audit_workspace(root)["checkpoint"] == "COMPLETE"
    assert apply(root)["sort_id"] is None
    assert organize(root, POLICY)["sort_id"] is None
    assert catalog(root) == rows and title_records(root) == titles
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert image.read_bytes() == before and not catalog(root) and not title_records(root)


@pytest.mark.parametrize("change", ["rules", "source", "addition", "mtime", "catalog", "titles", "assignment", "policy"])
def test_changed_preview_refuses_before_writes(root, make_image, change):
    rules(root)
    image = make_image(root / "hockey.png")
    organize(root, POLICY)
    p = plan(root, POLICY, categories=True)
    row = catalog(root)[0]
    args = {"policy": POLICY, "categories": True, "plan_id": p["plan_id"]}
    if change == "rules": rules(root, "Sport=hockey")
    if change == "source": make_image(root / row["relative"], color=(30, 40, 50))
    if change == "addition": make_image(root / "new.png")
    if change == "mtime": os.utime(root / row["relative"], (1, 1))
    if change == "catalog":
        with contextlib.closing(connect(root)) as db:
            db.execute("UPDATE images SET date_source='changed'")
            db.commit()
    if change == "titles": save_title(root, {**title_records(root)[0], "original_filename": "later.png"})
    if change == "assignment": args["assignments"] = [row["relative"] + "=uncategorized"]
    if change == "policy": args["policy"] = Policy(date_mode="embedded")
    old_journal = latest_sort(root)
    with pytest.raises(RiposteError, match="CATEGORY_PREVIEW_CHANGED"):
        organize(root, **args)
    assert latest_sort(root) == old_journal
    assert not (root / "2025/March/img/hockey").exists()


def test_legacy_numbered_files_need_manual_assignment_and_restore_absence(root, make_image):
    rules(root)
    make_image(root / "hockey.png")
    organize(root, POLICY)
    row = catalog(root)[0]
    with contextlib.closing(connect(root)) as db:
        db.execute("DELETE FROM sort_titles")
        db.commit()
    assert plan(root, POLICY, categories=True)["blockers"] == {"CATEGORY_ORIGINAL_TITLE_REQUIRED": 1}
    result = apply(root, assignments=[row["relative"] + "=hockey"])
    assert result["checkpoint"] == "COMPLETE"
    assert title_records(root)[0]["original_filename"] is None
    assert title_records(root)[0]["manual"]
    assert catalog(root)[0]["id"] == row["id"]
    assert apply(root)["sort_id"] is None
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == [row] and not title_records(root)


def test_ambiguity_override_exclusion_unicode_and_empty_rules(root, make_image):
    rules(root, "Équipe=hockey", "Sports=hockey")
    make_image(root / "winter-HOCKEY.png")
    p = plan(root, POLICY, categories=True)
    assert p["blockers"] == {"CATEGORY_AMBIGUOUS": 1}
    assert p["counts"]["ambiguous_files"] == 1
    assert apply(root, assignments=["winter-HOCKEY.png=équipe"])["checkpoint"] == "COMPLETE"
    assert "/équipe/" in catalog(root)[0]["relative"]
    canonical_path(catalog(root)[0]["relative"])


def test_title_only_update_undo_preserves_catalog(root, make_image):
    rules(root)
    make_image(root / "hockey.png")
    apply(root)
    rows, titles = catalog(root), title_records(root)
    result = apply(root, assignments=[rows[0]["relative"] + "=hockey"])
    assert result["sort_id"] and not latest_sort(root)["entries"]
    assert title_records(root)[0]["manual"]
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == rows and title_records(root) == titles


def test_changed_assignment_blocks_undo(root, make_image):
    rules(root)
    make_image(root / "hockey.png")
    apply(root)
    save_title(root, {**title_records(root)[0], "original_filename": "changed.png"})
    assert undo_sort(root)["blockers"] == {"UNDO_ASSIGNMENTS_CHANGED": 1}
    assert undo_sort(root, apply=True)["checkpoint"] == "INCOMPLETE"


def test_rules_change_reclassifies_using_original_and_undo_restores_assignment(root, make_image):
    rules(root)
    make_image(root / "hockey.png")
    apply(root)
    rows, titles = catalog(root), title_records(root)
    rules(root, "Winter=hockey")
    assert apply(root)["checkpoint"] == "COMPLETE"
    assert catalog(root)[0]["id"] == rows[0]["id"]
    assert "/winter/" in catalog(root)[0]["relative"]
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == rows and title_records(root) == titles


def test_late_collision_never_claims_unowned_output(root, make_image, monkeypatch):
    import riposte.organizer as sorter
    rules(root)
    image = make_image(root / "hockey.png")
    p = plan(root, POLICY, categories=True)
    write = sorter.atomic_clean_write
    destination = root / p["files"][0]["destination"]
    def occupied(*args, **kwargs):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"other writer")
        return write(*args, **kwargs)
    monkeypatch.setattr(sorter, "atomic_clean_write", occupied)
    assert organize(root, POLICY, categories=True, plan_id=p["plan_id"])["checkpoint"] == "INCOMPLETE"
    assert image.exists() and not catalog(root) and not title_records(root)
    assert latest_sort(root)["entries"][0]["output"] is None
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert destination.read_bytes() == b"other writer"


@pytest.mark.parametrize("when", ["before_title", "after_title", "after_catalog_restore"])
def test_interruption_recovery_restores_private_state(root, make_image, monkeypatch, when):
    import riposte.sort_history as history
    rules(root)
    make_image(root / "hockey.png")
    organize(root, POLICY)
    rows, titles = catalog(root), title_records(root)
    if when == "after_catalog_restore":
        apply(root)
        save = history._save
        def interrupted(root, journal):
            if journal["status"] == "UNDONE": raise KeyboardInterrupt()
            return save(root, journal)
        with monkeypatch.context() as patch:
            patch.setattr(history, "_save", interrupted)
            with pytest.raises(KeyboardInterrupt): undo_sort(root, apply=True)
    else:
        save = history.save_title
        def interrupted(root, row):
            if when == "after_title": save(root, row)
            raise KeyboardInterrupt()
        with monkeypatch.context() as patch:
            patch.setattr(history, "save_title", interrupted)
            with pytest.raises(KeyboardInterrupt): apply(root)
    assert latest_sort(root)["status"] in {"APPLYING", "UNDOING"}
    assert plan(root, POLICY, categories=True)["blockers"]["SORT_RECOVERY_REQUIRED"]
    assert undo_sort(root)["ready"]
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == rows and title_records(root) == titles


def test_real_video_category_move_keeps_identity_bytes_and_undo(root, make_image):
    import shutil
    import subprocess
    from riposte.video import video_catalog
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Local ffmpeg/ffprobe required for a real video fixture")
    rules(root)
    image = make_image(root / "hockey.png")
    video = root / "winter-hockey-goalie-practice.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x48:r=2", "-t", "1",
                    "-metadata", "comment=PRIVATE_VIDEO_METADATA", str(video)], check=True, capture_output=True, timeout=30,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    os.utime(video, (image.stat().st_mtime, image.stat().st_mtime))
    video_bytes = video.read_bytes()
    assert organize(root, POLICY)["checkpoint"] == "COMPLETE"
    previous, titles = video_catalog(root), title_records(root)
    assert apply(root)["checkpoint"] == "COMPLETE"
    row = video_catalog(root)[0]
    assert row["id"] == previous[0]["id"] and row["relative"] == "2025/March/vid/hockey/SML/SML01.mp4"
    assert (root / row["relative"]).read_bytes() == video_bytes
    assert catalog(root)[0]["relative"] == "2025/March/img/hockey/SML/SML01.png"
    assert audit_workspace(root)["checkpoint"] == "COMPLETE"
    assert apply(root)["sort_id"] is None
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert video_catalog(root) == previous and title_records(root) == titles


def test_duplicate_content_and_collisions_have_separate_ids(root, make_image):
    rules(root)
    make_image(root / "hockey-one.png")
    make_image(root / "hockey-two.png")
    apply(root)
    before = catalog(root)
    make_image(root / "hockey-three.png")
    p = plan(root, POLICY, categories=True)
    assert next(r for r in p["files"] if r["source"] == "hockey-three.png")["destination"].endswith("SML03.png")
    assert apply(root)["checkpoint"] == "COMPLETE"
    assert len({r["id"] for r in catalog(root)}) == 3
    assert len({r["sha256"] for r in catalog(root)}) == 1
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == before and (root / "hockey-three.png").exists()


def test_source_changes_during_preview_apply_leave_recovery_safe(root, make_image, monkeypatch):
    import riposte.sort_history as history
    rules(root)
    source = make_image(root / "hockey.png")
    p = plan(root, POLICY, categories=True)
    save = history._save
    changed = False
    def edited(root, journal):
        nonlocal changed
        save(root, journal)
        if journal["entries"] and not changed:
            source.write_bytes(b"later user input")
            changed = True
    monkeypatch.setattr(history, "_save", edited)
    assert organize(root, POLICY, categories=True, plan_id=p["plan_id"])["checkpoint"] == "INCOMPLETE"
    assert source.read_bytes() == b"later user input" and not catalog(root) and not title_records(root)
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == b"later user input"


def test_unreadable_directory_blocks_frozen_plan(root, monkeypatch):
    import riposte.organizer as sorter
    walk = sorter.os.walk
    def unreadable(path, **kwargs):
        kwargs["onerror"](PermissionError(13, "denied", str(root / "private")))
        return walk(path, **kwargs)
    monkeypatch.setattr(sorter.os, "walk", unreadable)
    p = plan(root, POLICY, categories=True)
    assert p["blockers"] == {"DIRECTORY_UNREADABLE": 1}
    assert not (root / ".riposte").exists()


def test_normalized_numbered_title_stays_unknown_with_manual_assignment(root, make_image):
    make_image(root / "ＳＭＬ01.png")
    p = plan(root, POLICY, categories=True)
    assert p["blockers"] == {"CATEGORY_ORIGINAL_TITLE_REQUIRED": 1}
    assert apply(root, assignments=["ＳＭＬ01.png=uncategorized"])["checkpoint"] == "COMPLETE"
    assert title_records(root)[0]["original_filename"] is None


def test_version_one_recovery_and_legacy_namespace(root, make_image):
    from riposte.store import LEGACY_SIGNATURE
    source = make_image(root / "hockey.png")
    original = source.read_bytes()
    organize(root, POLICY)
    journal = latest_sort(root)
    journal["version"] = 1
    journal.pop("titles")
    journal.pop("title_updates")
    with contextlib.closing(connect(root)) as db:
        db.execute("DROP TABLE sort_titles")
        db.commit()
    path = root / ".riposte/sort-history" / journal["id"] / "journal.json"
    path.write_text(json.dumps(journal), encoding="utf-8")
    assert undo_sort(root)["ready"]
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == original and not title_records(root)
    (root / ".riposte").rename(root / ".shroud")
    (root / ".shroud/WORKSPACE").write_text(LEGACY_SIGNATURE)
    rules(root)
    assert apply(root)["checkpoint"] == "COMPLETE"
    assert not (root / ".riposte").exists()
    assert audit_workspace(root)["checkpoint"] == "COMPLETE"
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == original
