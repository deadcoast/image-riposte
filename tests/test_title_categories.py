"""Filename-only milestone: suggestions and explicit drafts cannot sort or save."""
from riposte.organizer import plan as _sort_preview
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from riposte import title_categories as tc
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.terminal.actions import make_request, request_argv
from riposte.terminal.controller import Controller
from riposte.terminal.interaction import hints
from riposte.terminal.jobs import Operation
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.render import render
from riposte.terminal.service import Request, execute


def names(root, *titles):
    for title in titles:
        path = root / title
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Filename discovery does not decode this media fixture.")


def snapshot(root):
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def candidates(report):
    return {row["term"]: row["count"] for row in report["candidates"]}


def test_user_five_examples_and_arbitrary_position(root):
    names(root, *[f"hockey-{word}.png" for word in ("slapshot", "player", "forward", "defencemen", "goalie")])
    report = tc.discover_categories(root, min_count=1)
    assert candidates(report)["hockey"] == 5
    assert all(candidates(report)[term] == 1 for term in ("slapshot", "player", "forward", "defencemen", "goalie"))
    assert report["candidates"][0]["coverage"] == 1.0
    assert candidates(tc.discover_categories(root)) == {"hockey": 5}
    names(root, "winter-hockey-goalie-practice.mp4", "hockey-hockey-player.png", "fieldhockey.png")
    report = tc.discover_categories(root, categories=["Hockey=hockey"])
    assert candidates(report)["hockey"] == 7
    assert report["review"]["categories"][0]["count"] == 7
    assert report["counts"]["unmatched_files"] == 1


def test_unicode_separators_and_contiguous_phrases(root):
    names(root, "HOCKEY_Player.final.PNG", "hockey player 001.jpg", "ＨＯＣＫＥＹ_player.mp4",
          "Café_GOAL.png", "Cafe\u0301-goal.png", "Straße-goal.png", "STRASSE-goal.png")
    result = candidates(tc.discover_categories(root))
    assert result["hockey player"] == 3
    assert result["café goal"] == 2
    assert result["strasse"] == 2
    assert "001" not in result and "png" not in result
    assert tc.title_tokens("खेल अभ्यास") == ("खेल", "अभ्यास")


def test_filler_and_numeric_boundaries_never_invent_phrases(root):
    names(root, "hockey-and-goalie.png", "hockey-123-goalie.mp4", "hockey-goalie.png", "hockey-hockey-hockey.png")
    report = tc.discover_categories(root, min_count=1, ignore=["hockey"])
    result = candidates(report)
    assert "hockey" not in result
    assert result["hockey goalie"] == 1
    assert result["hockey hockey"] == 1
    assert "hockey and goalie" not in result
    assert candidates(tc.discover_categories(root, min_count=1, fillers=()))["hockey and goalie"] == 1


def test_manual_renamed_merged_drafts_are_explicit_and_count_union(root):
    names(root, "goalie-goaltender.png", "goaltender.mp4", "hockey-goalie.png", "goalies.png")
    report = tc.discover_categories(root, min_count=20, categories=["Goalkeepers=goalie;goaltender", "Hockey=hockey", "Absent=tennis"])
    assert report["candidates"] == []
    review = report["review"]
    assert [r["count"] for r in review["categories"]] == [3, 1, 0]
    assert report["counts"]["ambiguous_files"] == 1
    assert report["counts"]["unmatched_files"] == 1
    assert review["overlaps"] == [{"categories": ["Goalkeepers", "Hockey"], "count": 1}]
    assert review["ambiguous_examples"][0]["filename"] == "hockey-goalie.png"
    assert report["writes"] is False and report["rules_saved"] is False
    assert tc.discover_categories(root, categories=["goalie"])["review"]["categories"][0]["count"] == 2


def test_manual_phrases_keep_original_boundaries_and_ignore_discovery_filters(root):
    names(root, "king-of-hockey.png", "king-hockey.png", "hockey-7-player.png")
    report = tc.discover_categories(root, ignore=["hockey"], max_words=1,
                                    categories=["King=king of hockey", "Other=king hockey", "Player=hockey player"])
    assert [g["count"] for g in report["review"]["categories"]] == [1, 1, 0]


def test_no_media_reads_no_state_writes_and_private_directories_pruned(root, monkeypatch):
    names(root, "hockey.png", "hockey.mp4", "ignored.txt", "nested/.riposte/private-hockey.png",
          "nested/.shroud/secret-hockey.png")
    before = snapshot(root)
    def no_media_open(*args, **kwargs):
        pytest.fail("Discovery tried to open media bytes")
    monkeypatch.setattr(Path, "open", no_media_open)
    report = tc.discover_categories(root)
    monkeypatch.undo()
    assert candidates(report) == {"hockey": 2}
    assert report["counts"]["private_directories"] == 2
    assert snapshot(root) == before
    assert not (root / ".riposte").exists()
    assert report["media_validated"] is False


def test_known_generated_names_and_legacy_names_require_original_titles(root, make_image):
    make_image(root / "hockey-player.png")
    organize(root, Policy(date_mode="modified"), plan_id=_sort_preview(root, Policy(date_mode="modified"))["plan_id"])
    names(root, "2025/March/SML/SML99.png", "MED001.mp4", "new-hockey.png")
    before = snapshot(root)
    report = tc.discover_categories(root, min_count=1, categories=["Bad=sml01;med001"])
    assert report["counts"]["original_title_required"] == 3
    assert report["counts"]["analyzed_files"] == 1
    assert report["review"]["categories"][0]["count"] == 0
    assert "player" not in candidates(report)  # Private sort history is not a title source here.
    assert snapshot(root) == before


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_linked_files_and_directories_are_excluded_before_walk(root, monkeypatch, kind):
    names(root, "hockey.png", "linked/hockey-goalie.png", "fake-link.png")
    original = Path.lstat

    def linked(path, *args, **kwargs):
        if path.name in {"linked", "fake-link.png"}:
            return SimpleNamespace(st_mode=stat.S_IFLNK if kind == "symlink" else stat.S_IFDIR,
                                   st_file_attributes=0x400 if kind == "junction" else 0)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", linked)
    report = tc.discover_categories(root, min_count=1)
    assert candidates(report) == {"hockey": 1}
    assert report["counts"]["linked_paths"] == 2


def test_unreadable_walk_is_not_a_complete_scan(root, monkeypatch):
    def broken_walk(root, *, followlinks, onerror):
        onerror(PermissionError("private path must not enter result"))
        return iter(())
    monkeypatch.setattr(tc.os, "walk", broken_walk)
    report = tc.discover_categories(root)
    assert report["checkpoint"] == "INCOMPLETE"
    assert report["counts"]["unreadable_directories"] == 1
    assert "private path" not in json.dumps(report)


@pytest.mark.parametrize("directory", [False, True])
def test_unreadable_entry_is_not_misreported_as_a_link(root, monkeypatch, directory):
    names(root, "hockey.png", "blocked/goalie.png" if directory else "blocked.png")
    original = Path.lstat
    blocked = root / ("blocked" if directory else "blocked.png")

    def denied(path, *args, **kwargs):
        if path == blocked:
            raise PermissionError("private filename must not enter diagnostics")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", denied)
    report = tc.discover_categories(root, min_count=1)
    assert report["checkpoint"] == "INCOMPLETE"
    assert report["counts"]["unreadable_directories" if directory else "unreadable_files"] == 1
    assert report["counts"].get("linked_paths", 0) == 0
    assert candidates(report) == {"hockey": 1}
    assert "private filename" not in json.dumps(report)


@pytest.mark.parametrize("kwargs", [{"min_count": 0}, {"min_count": True}, {"max_words": 4}, {"limit": 501},
                                  {"sample_limit": -1}, {"fillers": "hockey"}, {"fillers": ["ice hockey"]},
                                  {"ignore": [""]}, {"categories": ["Hockey="]}, {"categories": ["=hockey"]},
                                  {"categories": ["A=one", "a=two"]}, {"categories": ["Bad\nlabel=hockey"]}])
def test_invalid_options_fail_without_writing(root, kwargs):
    with pytest.raises(RiposteError): tc.discover_categories(root, **kwargs)
    assert list(root.iterdir()) == []


def test_empty_collection_and_bounds(root):
    report = tc.discover_categories(root)
    assert report["candidates"] == [] and report["candidate_count"] == 0
    names(root, *[f"hockey-action{i}.png" for i in range(30)])
    report = tc.discover_categories(root, min_count=1, limit=2, sample_limit=2)
    assert report["candidate_count"] > 2 and len(report["candidates"]) == 2
    assert report["omitted_candidates"] == report["candidate_count"] - 2
    assert all(len(row["examples"]) <= 2 for row in report["candidates"])


def test_vocabulary_limit_fails_visibly_without_partial_suggestions(root, monkeypatch):
    names(root, "one-two-three.png")
    monkeypatch.setattr(tc, "MAX_TERMS", 2)
    with pytest.raises(RiposteError, match="CATEGORY_VOCABULARY_LIMIT"):
        tc.discover_categories(root)
    assert not (root / ".riposte").exists()


def test_cancellation_and_progress_do_not_expose_names(root):
    names(root, "private-hockey.png")
    events = []
    def cancel(event):
        events.append(event)
        if event.get("processed", 0) >= 1: raise RiposteError("JOB_CANCELLED")
    with pytest.raises(RiposteError, match="JOB_CANCELLED"):
        tc.discover_categories(root, progress=cancel)
    assert "private" not in json.dumps(events)
    assert not (root / ".riposte").exists()
    operation = Operation(Request("categories", root))
    assert operation.cancel()
    operation.start().join()
    assert operation.exit_code == 130 and operation.result is None


def test_cli_and_terminal_form_use_same_readonly_service(root):
    names(root, "hockey-player.png", "winter-hockey-goalie.mp4")
    before = snapshot(root)
    controller = Controller(root, Presentation(plain=True, no_animation=True))
    controller.action("organize")
    assert any(h.key == "c" and h.label == "Categories" for h in hints(controller.state))
    controller.key(Key("char", "c"))
    assert controller.state.page.action == "categories"
    controller.state.page.values.update(category_specs="Sport=hockey;goalie", fillers="", ignore="winter")
    request = controller.request_from_form()
    expected = execute(request)
    args = ["--json", *request_argv(request)[1:]]
    actual = CliRunner().invoke(app, args)
    assert actual.exit_code == 0, actual.output
    assert json.loads(actual.stdout) == expected
    assert expected["review"]["categories"][0]["count"] == 2
    assert "--fillers" in args and args[args.index("--fillers") + 1] == ""
    assert snapshot(root) == before


def test_category_results_cannot_authorize_source_replacement(root):
    names(root, "hockey.png")
    controller = Controller(root, Presentation(no_animation=True))
    controller.action("categories")
    controller.run_form()
    controller.state.operation.join()
    controller.pump()
    assert controller.state.page.name == "result"
    assert controller.state.page.result["writes"] is False
    for width, height in ((79, 24), (100, 34), (132, 46)):
        frame = render(controller.state, width, height, 0).plain()
        assert "FILENAME CATEGORIES" in frame.upper()
        assert all(len(line) <= width for line in frame.splitlines())
    controller.key(Key("enter"))
    assert controller.state.page.name == "form"
    assert list(root.iterdir()) == [root / "hockey.png"]


def test_default_form_and_ignored_candidate_can_be_reselected(root):
    names(root, "hockey.png")
    request = make_request("categories", root, {})
    report = execute(request)
    assert report["review"]["categories"] == []
    report = tc.discover_categories(root, ignore=["hockey"], categories=["Sport=hockey"])
    assert report["review"]["categories"][0]["count"] == 1


@pytest.mark.skipif(sys.platform != "win32", reason="Windows command-wrapper argument contract")
def test_windows_launcher_accepts_category_aliases(root):
    names(root, "hockey.png", "goalie.mp4", "other.jpg")
    before = snapshot(root)
    launcher = Path(__file__).resolve().parents[1] / "riposte.cmd"
    result = subprocess.run([str(launcher), "--json", "categories", str(root),
                             "--category", "Sport=hockey;goalie"],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["review"]["categories"][0]["count"] == 2
    assert report["counts"]["unmatched_files"] == 1
    assert snapshot(root) == before
