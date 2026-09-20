"""Saved-rule contracts; no category movement or original-title recovery claimed."""
from riposte.organizer import plan as _sort_preview
import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from riposte import category_rules as cr
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.locking import LEASE_NAME
from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.sort_history import undo_sort
from riposte.store import LEGACY_SIGNATURE, state_dir, state_relative, workspace_lock
from riposte.terminal.service import EFFECTS, Request, execute


def snapshot(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def save(root, specs=("Hockey=hockey;goalie;goaltender",), **kwargs):
    return cr.save_rules(root, cr.build_rules(specs, **kwargs), expected_revision=cr.load_rules(root).revision)


def test_preview_save_reload_and_revision_consent(root):
    preview = cr.category_rules(root, categories=["Hockey=hockey;goalie"])
    assert preview["revision"] == "missing" and preview["status"] == "DRAFT"
    assert preview["rules"]["categories"][0]["slug"] == "hockey"
    assert not list(root.iterdir())
    with pytest.raises(RiposteError, match="CATEGORY_REVISION_REQUIRED"):
        cr.category_rules(root, categories=["Hockey=hockey"], save=True)
    assert not list(root.iterdir())
    result = cr.category_rules(root, categories=["Hockey=hockey;goalie"], save=True, expected_revision="missing")
    before = snapshot(root)
    assert cr.category_rules(root)["rules"] == result["rules"]
    assert result["status"] == "SAVED" and result["sorting_enabled"] is False
    assert cr.load_rules(root).revision == result["revision"] != "missing"
    with pytest.raises(RiposteError, match="CATEGORY_RULES_CHANGED"):
        cr.category_rules(root, categories=["New=tennis"], save=True, expected_revision="missing")
    assert snapshot(root) == before
    assert set(before) == {".riposte/WORKSPACE", ".riposte/category-rules.json", LEASE_NAME}
    assert before[LEASE_NAME][0] == b""  # Persistent OS lease, never artwork or a held-lock marker.


def test_priorities_aliases_exclusions_phrases_and_ties():
    rules = cr.build_rules(["Hockey=hockey;goalie;goaltender", "Practice=practice"],
                          exclusions=["hockey=table hockey;toy"], priorities=["Hockey=5"])
    match = cr.match_title("winter-hockey-goalie-practice", rules)
    assert match["status"] == "MATCHED" and match["category"]["slug"] == "hockey"
    assert match["matches"][0]["matched_terms"] == ["goalie", "hockey"]
    assert cr.match_title("table-hockey-practice", rules)["category"]["slug"] == "practice"
    assert cr.match_title("fieldhockey-player", rules)["status"] == "UNMATCHED"
    assert cr.match_title("hockey-table-practice", rules)["category"]["slug"] == "hockey"
    assert cr.match_title("toy-goaltender", rules)["category"] is None
    tied = cr.build_rules(["Hockey=hockey", "Practice=practice"])
    assert cr.match_title("hockey-practice", tied)["status"] == "AMBIGUOUS"
    assert cr.match_title("hockey-practice", tied)["category"] is None
    assert cr.match_title("SML001", rules)["status"] == "ORIGINAL_TITLE_UNAVAILABLE"


def test_unicode_normalization_slug_stability_and_explicit_rename(root):
    stored = save(root, ["Café=CAFÉ;Straße", "खेल=खेल अभ्यास"])
    assert cr.match_title("Cafe\u0301-player", stored.rules)["category"]["slug"] == "café"
    assert cr.match_title("STRASSE", stored.rules)["status"] == "MATCHED"
    assert cr.match_title("खेल-अभ्यास", stored.rules)["category"]["slug"] == "खेल"
    renamed = save(root, ["Coffee=café"], slugs=["Coffee=café"])
    assert renamed.rules[0].slug == "café" and renamed.rules[0].label == "Coffee"
    assert renamed.revision != stored.revision


@pytest.mark.parametrize("slug", ["../hockey", "con", "nul", "com1", "LPT1", "aux.txt", "hockey.",
                                  "hockey ", "", "a/b", "a\\b", "a:b", ".riposte", "uncategorized",
                                  "a--b", "a" * 81, "Hockey", "cafe\u0301"])
def test_unsafe_or_noncanonical_slug_rejected(root, slug):
    # Test the storage boundary as well as CLI compilation; no silent path cleanup.
    with pytest.raises(RiposteError, match="CATEGORY_SLUG"):
        cr.save_rules(root, [cr.CategoryRule("Hockey", slug, ("hockey",))], expected_revision="missing")
    assert not list(root.iterdir())


@pytest.mark.parametrize("specs,options", [
    (["Ice Hockey=hockey", "Ice-Hockey=goalie"], {}),
    (["Uncategorized=hockey"], {}), (["Hockey=hockey"], {"exclusions": ["Hockey=hockey"]}),
    (["Hockey=hockey"], {"exclusions": ["Other=toy"]}),
    (["Hockey=hockey"], {"priorities": ["Hockey=5", "hockey=6"]}),
    (["Hockey=hockey"], {"priorities": ["Hockey=NaN"]}),
    (["Hockey=hockey"], {"priorities": ["Hockey=1000001"]}),
    (["Hockey=hockey"], {"exclusions": ["Hockey="]}),
    (["Hockey=hockey"], {"exclusions": ["Hockey=" + "word" * 100]}),
])
def test_invalid_rules_fail_before_creating_state(root, specs, options):
    with pytest.raises(RiposteError):
        cr.category_rules(root, categories=specs, save=True, expected_revision="missing", **options)
    assert not list(root.iterdir())


def test_colliding_slugs_require_explicit_unique_override():
    rules = cr.build_rules(["Ice Hockey=hockey", "Ice-Hockey=goalie"], slugs=["Ice-Hockey=goalkeepers"])
    assert {r.slug for r in rules} == {"ice-hockey", "goalkeepers"}


@pytest.mark.parametrize("mutate", [
    lambda d: {**d, "version": 2}, lambda d: {**d, "version": True},
    lambda d: {**d, "unknown": "field"}, lambda d: {**d, "categories": {}},
    lambda d: {**d, "categories": [{**d["categories"][0], "priority": True}]},
    lambda d: {**d, "categories": [{**d["categories"][0], "terms": "hockey"}]},
    lambda d: {**d, "categories": [{**d["categories"][0], "label": "bad\nlabel"}]},
])
def test_malformed_saved_state_is_not_silently_reset(root, mutate):
    stored = save(root)
    path = root / state_relative(root, "category-rules.json")
    path.write_text(json.dumps(mutate(cr.rules_document(stored.rules))), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(RiposteError): cr.load_rules(root)
    with pytest.raises(RiposteError): save(root)
    assert path.read_bytes() == before


@pytest.mark.parametrize("content", [b"{", b"\xff", b'{"version":1,"version":1,"categories":[]}',
                                   b" " * (cr.MAX_RULE_BYTES + 1), b"[" * 2000],
                         ids=["truncated", "non-utf8", "duplicate-key", "oversized", "deeply-nested"])
def test_invalid_json_and_oversize_reads_are_bounded(root, content):
    path = state_dir(root) / "category-rules.json"
    path.write_bytes(content)
    with pytest.raises(RiposteError, match="CATEGORY_RULES_INVALID"): cr.load_rules(root)


def test_interrupted_save_keeps_previous_bytes_and_cleans_temp(root, monkeypatch):
    previous = save(root)
    before = snapshot(root)
    def interrupted(*args): raise OSError("simulated interruption")
    monkeypatch.setattr(cr.os, "replace", interrupted)
    with pytest.raises(OSError):
        cr.save_rules(root, cr.build_rules(["New=tennis"]), expected_revision=previous.revision)
    assert snapshot(root) == before


def test_concurrent_edit_during_flush_is_detected(root, monkeypatch):
    previous = save(root)
    path = root / state_relative(root, "category-rules.json")
    competing = json.dumps(cr.rules_document(cr.build_rules(["Other=other"]))).encode()
    original = cr.os.fsync
    def changed(fd):
        original(fd)
        path.write_bytes(competing)
    monkeypatch.setattr(cr.os, "fsync", changed)
    with pytest.raises(RiposteError, match="CATEGORY_RULES_CHANGED"):
        cr.save_rules(root, cr.build_rules(["New=tennis"]), expected_revision=previous.revision)
    assert path.read_bytes() == competing
    assert not list(path.parent.glob("*.tmp")) and not (path.parent / "operation.lock").exists()


def test_existing_workspace_lock_prevents_save(root):
    previous = save(root)
    with workspace_lock(root):
        with pytest.raises(RiposteError, match="WORKSPACE_LOCKED"):
            cr.save_rules(root, cr.build_rules(["New=tennis"]), expected_revision=previous.revision)
    assert cr.load_rules(root) == previous


def test_linked_and_nonfile_state_is_rejected(root, tmp_path):
    state = state_dir(root)
    target = tmp_path / "external.json"
    target.write_text(json.dumps(cr.rules_document(cr.build_rules(["Other=other"]))), encoding="utf-8")
    path = state / "category-rules.json"
    os.link(target, path)
    with pytest.raises(RiposteError): cr.load_rules(root)
    with pytest.raises(RiposteError): save(root)
    assert "Other" in target.read_text()
    path.unlink()
    path.mkdir()
    with pytest.raises(RiposteError): cr.load_rules(root)


def test_rule_symlink_rejected_without_touching_target(root, tmp_path):
    path = state_dir(root) / "category-rules.json"
    target = tmp_path / "external.json"
    target.write_text("untouched")
    try: path.symlink_to(target)
    except OSError: pytest.skip("symlinks unavailable")
    with pytest.raises(RiposteError, match="PATH_LINKED"): cr.load_rules(root)
    with pytest.raises(RiposteError): save(root)
    assert target.read_text() == "untouched"


def test_legacy_state_save_and_readonly_match_counts(root):
    state = root / ".shroud"
    state.mkdir()
    (state / "WORKSPACE").write_text(LEGACY_SIGNATURE)
    stored = save(root, ["Hockey=hockey", "Practice=practice"])
    for title in ("hockey-hockey.png", "hockey-practice.mp4", "other.jpg", "SML01.png"):
        (root / title).write_bytes(b"names only")
    (state / "private-hockey.png").write_bytes(b"ignored")
    before = snapshot(root)
    report = cr.category_rules(root, review=True)
    assert report["review"]["counts"]["analyzed_files"] == 3
    assert report["review"]["counts"]["original_title_required"] == 1
    assert report["review"]["counts"]["ambiguous_files"] == 1
    assert report["review"]["assignments"] == {"hockey": 1}
    assert cr.load_rules(root) == stored and snapshot(root) == before
    assert not (root / ".riposte").exists()


def test_review_incomplete_scan_and_cancellation(root, monkeypatch):
    def unreadable(root, *, followlinks, onerror):
        onerror(PermissionError("private path"))
        return iter(())
    monkeypatch.setattr(cr._media_titles.__globals__["os"], "walk", unreadable)
    report = cr.category_rules(root, categories=["Hockey=hockey"], review=True)
    assert report["review"]["checkpoint"] == "INCOMPLETE"
    assert "private path" not in json.dumps(report)
    monkeypatch.undo()
    (root / "hockey.png").write_bytes(b"names only")
    def cancel(_event): raise RiposteError("JOB_CANCELLED")
    with pytest.raises(RiposteError, match="JOB_CANCELLED"):
        cr.category_rules(root, categories=["Hockey=hockey"], review=True, save=True,
                          expected_revision="missing", progress=cancel)
    assert not (root / ".riposte").exists()


def test_explicit_clear_and_no_accidental_empty_replacement(root):
    previous = save(root)
    for options in ({"save": True}, {"clear": True, "categories": ["Hockey=hockey"]},
                    {"expected_revision": previous.revision}, {"priorities": ["Hockey=3"]}):
        with pytest.raises(RiposteError): cr.category_rules(root, **options)
    preview = cr.category_rules(root, clear=True)
    assert preview["rules"]["categories"] == [] and cr.load_rules(root) == previous
    cr.category_rules(root, clear=True, save=True, expected_revision=preview["revision"])
    assert cr.load_rules(root).rules == () and cr.load_rules(root).revision != "missing"


def test_cli_and_shared_service_preview_save_reload(root):
    runner = CliRunner()
    args = ["--json", "category-rules", str(root), "--category", "Hockey=hockey;goalie",
            "--exclude", "Hockey=toy", "--priority", "Hockey=10", "--slug", "Hockey=sports", "--review"]
    preview = runner.invoke(app, args)
    assert preview.exit_code == 0, preview.output
    request = Request("category-rules", root, {"category_specs": ["Hockey=hockey;goalie"],
                      "exclusions": ["Hockey=toy"], "priorities": ["Hockey=10"], "slugs": ["Hockey=sports"], "review": True})
    assert json.loads(preview.stdout) == execute(request)
    assert not list(root.iterdir())
    saved = runner.invoke(app, [*args, "--save", "--expected-revision", "missing"])
    assert saved.exit_code == 0, saved.output
    reloaded = runner.invoke(app, ["--json", "category-rules", str(root), "--review"])
    assert reloaded.exit_code == 0, reloaded.output
    assert json.loads(reloaded.stdout)["rules"] == json.loads(saved.stdout)["rules"]
    assert EFFECTS["category-rules"] == "INSPECT"
    assert EFFECTS["category-rules-save"] == "SAVE_CATEGORY_RULES"


def test_saved_rules_do_not_enable_sorting_or_change_undo(root, make_image):
    original = make_image(root / "hockey-player.png")
    artwork = original.read_bytes()
    stored = save(root)
    rule_bytes = (root / state_relative(root, "category-rules.json")).read_bytes()
    before = snapshot(root)
    assert plan(root, Policy(date_mode="modified"))["ready"]
    assert snapshot(root) == before
    result = organize(root, Policy(date_mode="modified"), plan_id=_sort_preview(root, Policy(date_mode="modified"))["plan_id"])
    assert result["checkpoint"] == "COMPLETE"
    assert (root / "2025/March/img/SML/SML01.png").is_file()
    assert cr.load_rules(root) == stored
    assert cr.category_rules(root, review=True)["review"]["counts"]["original_title_required"] == 1
    undo_sort(root, apply=True)
    assert original.read_bytes() == artwork
    assert (root / state_relative(root, "category-rules.json")).read_bytes() == rule_bytes
