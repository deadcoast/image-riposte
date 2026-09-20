"""PAC-030: workspace rejection before any scan, state creation or source edit."""
from riposte.organizer import plan as _sort_preview
import json
import os
from pathlib import Path
import subprocess

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from riposte import store
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.server import create_app
from riposte.terminal.paths import validate_workspace
from riposte.terminal.service import Request, execute


@pytest.fixture
def layout(tmp_path, monkeypatch):
    checkout = tmp_path / "application"
    package = checkout / "src/riposte"
    package.mkdir(parents=True)
    (checkout / "pyproject.toml").write_text('[project]\nname = "riposte-studio"\n')
    # Model the loaded module locations, not an optional bypass of the guard.
    monkeypatch.setattr(store, "__file__", str(package / "store.py"))
    monkeypatch.setattr("riposte.terminal.paths.__file__", str(package / "terminal/paths.py"))
    inside = checkout / "images"
    inside.mkdir()
    sibling = tmp_path / "images"
    sibling.mkdir()
    return checkout, inside, sibling


@pytest.mark.parametrize("entry", ["backend", "plan", "service", "combined", "rules", "terminal", "api", "cli"])
@pytest.mark.parametrize("relationship", ["exact", "ancestor", "descendant"])
def test_all_boundaries_reject_overlap_without_writes(layout, make_image, entry, relationship):
    checkout, inside, _ = layout
    root = {"exact": checkout, "ancestor": checkout.parent, "descendant": inside}[relationship]
    source = make_image(root / "original.png")
    original, modified = source.read_bytes(), source.stat().st_mtime_ns
    before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
    if entry == "cli":
        result = CliRunner().invoke(app, ["--json", "sort", str(root), "--apply", "--date-mode", "modified"])
        assert result.exit_code == 2, result.stdout
        assert json.loads(result.stderr)["error"] == "IMAGE_FOLDER_OVERLAPS_APPLICATION"
        assert not result.stdout and str(root) not in result.stderr
    else:
        calls = {
            "backend": lambda: organize(root, Policy(date_mode="modified")),
            "plan": lambda: plan(root),
            "service": lambda: execute(Request("apply", root)),
            "combined": lambda: execute(Request("sort-riposte", root, {"all_images": True})),
            "rules": lambda: execute(Request("category-rules-save", root)),
            "terminal": lambda: validate_workspace(root),
            "api": lambda: create_app(root),
        }
        with pytest.raises(RiposteError, match="^IMAGE_FOLDER_OVERLAPS_APPLICATION$"):
            calls[entry]()
    assert source.read_bytes() == original and source.stat().st_mtime_ns == modified
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*")) == before


def test_independent_sibling_preview_sort_and_exact_undo(layout, make_image):
    _, _, root = layout
    source = make_image(root / "original.png")
    original, modified = source.read_bytes(), source.stat().st_mtime_ns
    assert validate_workspace(root) == root
    assert execute(Request("organize", root))["ready"]
    assert sorted(p.name for p in root.iterdir()) == ["original.png"]
    application = create_app(root, token="test")
    with TestClient(application) as client:
        response = client.post("/api/organize", headers={"x-riposte-token": "test"},
                               json={"apply": True, "acknowledge_source_removal": True, "date_mode": "modified",
                                     "plan_id": _sort_preview(root, Policy(date_mode="modified"))["plan_id"]})
        assert response.status_code == 200
        application.state.jobs.pool.submit(lambda: None).result(timeout=10)
        job = next(j for j in application.state.jobs.snapshot() if j["id"] == response.json()["job_id"])
        assert job["state"] == "done", job
        assert job["result"]["checkpoint"] == "COMPLETE"
    assert not source.exists()
    preview = execute(Request("undo-sort", root))
    result = execute(Request("undo-sort-apply", root, {"sort_id": preview["sort_id"]}))
    assert result["checkpoint"] == "COMPLETE"
    assert source.read_bytes() == original and source.stat().st_mtime_ns == modified


@pytest.mark.parametrize("relative", ["Lib/site-packages/riposte", "lib/python3.13/site-packages/riposte", "target/riposte", "src/riposte"])
def test_installed_package_has_no_fixed_parent_assumption(tmp_path, monkeypatch, relative):
    package = tmp_path / relative
    package.mkdir(parents=True)
    monkeypatch.setattr(store, "__file__", str(package / "store.py"))
    monkeypatch.setattr("riposte.terminal.paths.__file__", str(package / "terminal/paths.py"))
    child = package / "images"
    child.mkdir()
    sibling = package.with_name("images")
    sibling.mkdir()
    for root in (package, package.parent, child):
        with pytest.raises(RiposteError, match="^IMAGE_FOLDER_OVERLAPS_APPLICATION$"):
            store.check_root(root)
        with pytest.raises(RiposteError, match="^IMAGE_FOLDER_OVERLAPS_APPLICATION$"):
            validate_workspace(root)
    assert store.check_root(sibling) == validate_workspace(sibling) == sibling
    assert not list(sibling.iterdir())


def test_dotdot_paths_compare_canonical_locations(layout):
    checkout, inside, sibling = layout
    with pytest.raises(RiposteError, match="^IMAGE_FOLDER_OVERLAPS_APPLICATION$"):
        store.check_root(sibling / ".." / checkout.name / inside.name)
    independent = checkout / ".." / sibling.name
    assert store.check_root(independent).resolve() == sibling


@pytest.mark.skipif(os.name != "nt", reason="Windows case-insensitive paths")
def test_windows_case_alias_cannot_bypass_guard(layout):
    _, inside, _ = layout
    with pytest.raises(RiposteError, match="^IMAGE_FOLDER_OVERLAPS_APPLICATION$"):
        store.check_root(Path(str(inside).upper()))


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_links_and_linked_parents_remain_rejected(layout, kind):
    checkout, inside, sibling = layout
    link = sibling / "linked"
    if kind == "junction":
        if os.name != "nt":
            pytest.skip("Windows junction")
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(checkout)], capture_output=True, text=True)
        assert made.returncode == 0, made.stderr
    else:
        try:
            link.symlink_to(checkout, target_is_directory=True)
        except OSError as exc:
            if os.name == "nt" and exc.winerror == 1314:
                pytest.skip("Windows symlink privilege unavailable; junction exercised separately")
            raise
    for path, code in ((link, "ROOT_INVALID"), (link / inside.name, "ROOT_LINKED")):
        for check in (store.check_root, validate_workspace):
            with pytest.raises(RiposteError, match=f"^{code}$"):
                check(path)
    assert not list(inside.iterdir())


def test_unrelated_src_project_is_not_a_riposte_checkout(tmp_path, monkeypatch):
    package = tmp_path / "src/riposte"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "unrelated"\n')
    monkeypatch.setattr(store, "__file__", str(package / "store.py"))
    assert store.application_directory() == package
    sibling = package.with_name("images")
    sibling.mkdir()
    assert store.check_root(sibling) == sibling


def test_unreadable_layout_fails_without_workspace_writes(tmp_path, monkeypatch):
    package = tmp_path / "src/riposte"
    package.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[broken")
    monkeypatch.setattr(store, "__file__", str(package / "store.py"))
    with pytest.raises(RiposteError, match="^APPLICATION_LAYOUT_INVALID$"):
        organize(package)
    assert not list(package.iterdir())


def test_api_rechecks_root_at_execution(layout, monkeypatch, make_image):
    _, _, root = layout
    source = make_image(root / "original.png")
    original = source.read_bytes()
    application = create_app(root, token="test")
    with TestClient(application) as client:
        monkeypatch.setattr(store, "application_directory", lambda: root)
        response = client.post("/api/organize", headers={"x-riposte-token": "test"},
                               json={"apply": True, "acknowledge_source_removal": True})
        assert response.status_code == 200
        application.state.jobs.pool.submit(lambda: None).result(timeout=10)
        job = next(j for j in application.state.jobs.snapshot() if j["id"] == response.json()["job_id"])
        assert job["state"] == "error" and job["code"] == "IMAGE_FOLDER_OVERLAPS_APPLICATION"
    assert source.read_bytes() == original
    assert sorted(p.name for p in root.iterdir()) == ["original.png"]


def test_existing_nested_library_can_move_with_history_and_undo(layout, monkeypatch, make_image):
    checkout, inside, sibling = layout
    source = make_image(inside / "original.png")
    before = source.read_bytes(), source.stat().st_mtime_ns
    # Seed an old CLI-created library. Restore the guard before testing recovery.
    with monkeypatch.context() as previous_version:
        previous_version.setattr(store, "application_directory", lambda: checkout.with_name("old-install"))
        assert organize(inside, Policy(date_mode="modified"), plan_id=_sort_preview(inside, Policy(date_mode="modified"))["plan_id"])["checkpoint"] == "COMPLETE"
    with pytest.raises(RiposteError, match="^IMAGE_FOLDER_OVERLAPS_APPLICATION$"):
        execute(Request("undo-sort", inside))
    moved = inside.rename(sibling / "library")
    assert (moved / ".riposte/sort-history").is_dir()
    assert (moved / ".riposte-operation.lease").is_file()
    preview = execute(Request("undo-sort", moved))
    assert preview["ready"]
    assert execute(Request("undo-sort-apply", moved, {"sort_id": preview["sort_id"]}))["checkpoint"] == "COMPLETE"
    restored = moved / "original.png"
    assert (restored.read_bytes(), restored.stat().st_mtime_ns) == before
