"""Category matches enrich sorting; missing matches never require setup."""
import contextlib

import pytest

from riposte.category_rules import build_rules, load_rules, save_rules
from riposte.organizer import audit_workspace, organize, plan, undo_sort
from riposte.policy import Policy
from riposte.sort_titles import title_records
from riposte.store import catalog, connect
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.render import render

POLICY = Policy(date_mode="modified")


def save(root, specs=()):
    save_rules(root, build_rules(specs), expected_revision=load_rules(root).revision)


def apply(root, **kwargs):
    preview = plan(root, POLICY, categories=True, **kwargs)
    assert preview["ready"], preview["blockers"]
    result = organize(root, POLICY, categories=True, plan_id=preview["plan_id"], **kwargs)
    assert result["checkpoint"] == "COMPLETE", result
    return preview, result


def finish(c):
    assert c.state.operation.done.wait(15)
    c.pump()
    assert c.state.page.code is None, c.state.page.code


@pytest.mark.parametrize("rules", [None, (), ("Hockey=hockey",)])
def test_default_sort_without_category_setup_sorts_numbered_and_unmatched_then_undo(root, make_image, rules):
    sources = [make_image(root / name) for name in ("SML01.png", "MED002.png", "holiday.png")]
    originals = {p.name: p.read_bytes() for p in sources}
    held = make_image(root / "__float__" / "LRG01.png"); held_bytes = held.read_bytes()
    if rules is not None: save(root, rules)
    c = Controller(root, Presentation(no_animation=True))
    try:
        c.key(Key("enter")); c.key(Key("char", "1")); finish(c)
        preview = c.state.page.result
        assert preview["ready"], preview["blockers"]
        assert len(preview["files"]) == 3
        assert all("/img/SML/" in item["destination"] and item["category"] is None for item in preview["files"])
        screen = render(c.state, 72, 24).plain()
        assert "[Enter] Confirm sort" in screen
        c.key(Key("enter")); assert c.state.page.confirm_word == "REPLACE"
        c.key(Key("char", "REPLACE")); c.key(Key("enter")); finish(c)
        assert c.state.page.result["checkpoint"] == "COMPLETE"
        assert len(catalog(root)) == 3 and all(not p.exists() for p in sources)
        assert held.read_bytes() == held_bytes
        c.key(Key("enter")); c.key(Key("char", "1")); finish(c)
        assert c.state.page.result["ready"] and c.state.page.result["counts"]["already_sorted"] == 3
        assert "NO CHANGES" in render(c.state, 72, 24).plain()
        c.key(Key("enter")); c.key(Key("char", "u")); finish(c)
        c.key(Key("enter")); c.key(Key("char", "UNDO")); c.key(Key("enter")); finish(c)
        assert {p.name: p.read_bytes() for p in sources} == originals
        assert held.read_bytes() == held_bytes
    finally:
        c.shutdown()


def test_mixed_matches_ties_and_unknown_titles_all_sort_without_arbitrary_categories(root, make_image):
    save(root, ("Hockey=hockey", "Painting=painting", "Artwork=painting"))
    for name in ("hockey-goalie.png", "painting.png", "other.png", "SML01.png"):
        make_image(root / name)
    preview, _ = apply(root)
    files = {item["source"]: item for item in preview["files"]}
    assert files["hockey-goalie.png"]["category"]["slug"] == "hockey"
    assert "/img/hockey/SML/" in files["hockey-goalie.png"]["destination"]
    for name in ("painting.png", "other.png", "SML01.png"):
        assert files[name]["category"] is None
        assert "/img/SML/" in files[name]["destination"]
    assert files["SML01.png"]["original_filename"] is None
    assert files["painting.png"]["match_status"] == "AMBIGUOUS"
    assert audit_workspace(root)["checkpoint"] == "COMPLETE"


@pytest.mark.parametrize("categorized", [False, True])
def test_legacy_catalog_without_titles_can_sort_new_additions(root, make_image, categorized):
    save(root, ("Hockey=hockey",))
    make_image(root / "first hockey.png")
    organize(root, POLICY, categories=categorized, plan_id=plan(root, POLICY, categories=categorized)["plan_id"])
    previous = catalog(root)[0]
    with contextlib.closing(connect(root)) as db:
        db.execute("DELETE FROM sort_titles"); db.commit()
    make_image(root / "new painting.png")
    preview, _ = apply(root)
    kept = next(f for f in preview["files"] if f["source"] == previous["relative"])
    assert kept["action"] == "KEEP"
    assert kept["category_source"] == ("PRESERVED" if categorized else "NONE")
    assert len(catalog(root)) == 2
    assert next(t for t in title_records(root) if t["id"] == previous["id"])["original_filename"] is None
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == [previous] and not title_records(root)


@pytest.mark.parametrize("manual", [False, True])
def test_removing_category_rules_keeps_existing_assignment_and_new_files_still_sort(root, make_image, manual):
    save(root, ("Hockey=hockey",))
    make_image(root / "hockey.png")
    apply(root, assignments=["hockey.png=hockey"] if manual else [])
    old = catalog(root)[0]
    save(root)
    make_image(root / "SML02.png")
    preview, _ = apply(root)
    kept = next(f for f in preview["files"] if f["source"] == old["relative"])
    assert kept["action"] == "KEEP" and kept["category"]["slug"] == "hockey"
    assert next(t for t in title_records(root) if t["id"] == old["id"])["manual"] is manual
    assert len(catalog(root)) == 2 and audit_workspace(root)["checkpoint"] == "COMPLETE"


def test_explicit_auto_can_clear_a_saved_manual_category(root, make_image):
    save(root, ("Hockey=hockey",))
    make_image(root / "other.png")
    apply(root, assignments=["other.png=hockey"])
    old = catalog(root)[0]
    preview, _ = apply(root, assignments=[old["relative"] + "=auto"])
    assert preview["files"][0]["category"] is None
    assert "/img/SML/" in catalog(root)[0]["relative"]
    assert not title_records(root)[0]["manual"]
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert catalog(root) == [old] and title_records(root)[0]["manual"]
