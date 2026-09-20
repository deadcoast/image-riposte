"""PAC-031: explicit ordinary/combined receipts and unchanged-file boundaries."""
import hashlib
import json
import os

import pytest
from typer.testing import CliRunner

from riposte import organizer
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.store import catalog
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.service import Request, execute

POLICY = Policy(date_mode="modified")


def snapshot(root):
    return {p.relative_to(root).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def test_ordinary_preview_binds_exact_destinations_without_writes(root, make_image):
    source = make_image(root / "private.png")
    before = snapshot(root)
    preview = organizer.plan(root, POLICY)
    assert len(preview["plan_id"]) == 64
    assert preview == organizer.plan(root, POLICY)
    assert preview["files"][0]["destination"] == "2025/March/img/SML/SML01.png"
    assert preview["files"][0]["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert snapshot(root) == before and not (root / ".riposte").exists()


def test_ordinary_apply_requires_receipt_before_state(root, make_image):
    make_image(root / "original.png")
    before = snapshot(root)
    with pytest.raises(RiposteError, match="^SORT_PREVIEW_REQUIRED$"):
        organizer.organize(root, POLICY)
    assert snapshot(root) == before and not (root / ".riposte-operation.lease").exists()


@pytest.mark.parametrize("change", ["added", "removed", "bytes", "mtime", "policy", "limits", "sidecars", "destination"])
def test_stale_ordinary_preview_rejected_without_state(root, make_image, change):
    source = make_image(root / "original.png")
    preview = organizer.plan(root, POLICY)
    policy = POLICY
    if change == "added": make_image(root / "new.png")
    if change == "removed": source.unlink()
    if change == "bytes":
        stamp = source.stat().st_mtime_ns
        make_image(source, color=(2, 80, 150))
        os.utime(source, ns=(stamp, stamp))
    if change == "mtime": os.utime(source, (1, 1))
    if change == "policy": policy = Policy(date_mode="embedded")
    if change == "limits": policy = Policy(date_mode="modified", max_pixels=20_000_000)
    if change == "sidecars": policy = Policy(date_mode="modified", discard_sidecars=True)
    if change == "destination": make_image(root / "2025/March/img/SML/SML01.png")
    before = snapshot(root)
    with pytest.raises(RiposteError, match="^SORT_PREVIEW_CHANGED$"):
        organizer.organize(root, policy, plan_id=preview.get("plan_id"))
    assert snapshot(root) == before and not (root / ".riposte").exists()
    assert not (root / ".riposte-operation.lease").exists()


def test_bound_sort_and_exact_undo(root, make_image):
    source = make_image(root / "original.png")
    before = source.read_bytes(), source.stat().st_mtime_ns
    preview = organizer.plan(root, POLICY)
    result = organizer.organize(root, POLICY, plan_id=preview.get("plan_id"))
    assert result["checkpoint"] == "COMPLETE"
    assert catalog(root)[0]["relative"] == preview["files"][0]["destination"]
    undo = organizer.undo_sort(root)
    assert organizer.undo_sort(root, apply=True, sort_id=undo["sort_id"])["checkpoint"] == "COMPLETE"
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before


def test_terminal_carries_the_displayed_ordinary_receipt(root, make_image):
    make_image(root / "original.png")
    controller = Controller(root, Presentation())
    try:
        controller.action("organize")
        controller.key(Key("char", "p"))
        controller.state.operation.join()
        controller.pump()
        preview = controller.state.page.result
        make_image(root / "new.png")
        before = snapshot(root)
        controller.key(Key("enter"))
        assert controller.state.page.confirm_request.values.get("plan_id") == preview.get("plan_id")
        controller.key(Key("paste", "REPLACE"))
        controller.key(Key("enter"))
        controller.state.operation.join()
        controller.pump()
        assert controller.state.page.code == "SORT_PREVIEW_CHANGED"
        assert snapshot(root) == before
    finally:
        controller.shutdown()


@pytest.mark.parametrize("change", ["source", "policy", "epsilon", "edges", "selection", "model"])
def test_combined_receipt_rejects_drift_before_models(root, make_image, monkeypatch, change):
    make_image(root / "original.png")
    values = {"all_images": True, "date_mode": "modified", "vae_dirs": ["MODEL"]}
    preview = execute(Request("sort-riposte-plan", root, values))
    if change == "source": make_image(root / "new.png")
    if change == "policy": values["date_mode"] = "embedded"
    if change == "epsilon": values["epsilon"] = 3
    if change == "edges": values["edges"] = [1024]
    if change == "selection": values["year"] = "2025"
    if change == "model": values["vae_dirs"] = ["OTHER_MODEL"]
    calls = []
    monkeypatch.setattr("riposte.publication._models", lambda *args: calls.append(args) or [])
    before = snapshot(root)
    with pytest.raises(RiposteError, match="^SORT_PREVIEW_CHANGED$"):
        execute(Request("sort-riposte", root, {**values, "plan_id": preview.get("plan_id")}))
    assert not calls and snapshot(root) == before


def test_change_during_model_preflight_rejects_sort_without_state(root, make_image, monkeypatch):
    source = make_image(root / "original.png")
    before = source.read_bytes()
    values = {"all_images": True, "date_mode": "modified", "vae_dirs": ["MODEL"]}
    preview = execute(Request("sort-riposte-plan", root, values))
    def models(*args):
        make_image(root / "late.png")
        return []
    monkeypatch.setattr("riposte.publication._models", models)
    with pytest.raises(RiposteError, match="^SORT_PREVIEW_CHANGED$"):
        execute(Request("sort-riposte", root, {**values, "plan_id": preview.get("plan_id")}))
    assert source.read_bytes() == before and (root / "late.png").exists()
    assert not (root / ".riposte").exists() and not (root / ".riposte-operation.lease").exists()


def test_cli_receipt_roundtrip_and_missing_consent(root, make_image):
    make_image(root / "original.png")
    runner = CliRunner()
    p = runner.invoke(app, ["--json", "sort", str(root), "--date-mode", "modified"])
    assert p.exit_code == 0
    receipt = json.loads(p.stdout)["plan_id"]
    missing = runner.invoke(app, ["--json", "sort", str(root), "--apply"])
    assert missing.exit_code == 2 and json.loads(missing.stderr)["error"] == "SORT_PREVIEW_REQUIRED"
    applied = runner.invoke(app, ["--json", "sort", str(root), "--date-mode", "modified", "--apply", "--plan-id", receipt])
    assert applied.exit_code == 0 and json.loads(applied.stdout)["checkpoint"] == "COMPLETE"


@pytest.mark.parametrize("change", ["added", "removed", "policy", "missing"])
def test_api_rejects_unreviewed_sort_and_allows_fresh_retry(root, make_image, change):
    from fastapi.testclient import TestClient
    from riposte.server import create_app
    from test_category_sort_interfaces import job
    source = make_image(root / "original.png")
    with TestClient(create_app(root, "preview-test")) as client:
        client.headers["X-Riposte-Token"] = "preview-test"
        options = {"date_mode": "modified"}
        preview = job(client, "organize", options)["result"]
        if change == "added": make_image(root / "new.png")
        if change == "removed": source.unlink()
        if change == "policy": options["date_mode"] = "embedded"
        before = snapshot(root)
        result = job(client, "organize", {**options, "apply": True, "acknowledge_source_removal": True,
                                         "plan_id": None if change == "missing" else preview["plan_id"]})
        assert result["code"] == ("SORT_PREVIEW_REQUIRED" if change == "missing" else "SORT_PREVIEW_CHANGED")
        assert snapshot(root) == before and not (root / ".riposte-operation.lease").exists()
        refreshed = job(client, "organize", options)["result"]
        result = job(client, "organize", {**options, "apply": True, "acknowledge_source_removal": True,
                                         "plan_id": refreshed["plan_id"]})
        assert result["state"] == "done", result


@pytest.mark.parametrize("change", ["catalog", "titles", "history"])
def test_ordinary_receipt_includes_existing_private_state(root, make_image, change):
    import sqlite3
    from riposte.sort_history import latest_sort
    make_image(root / "original.png")
    organizer.organize(root, POLICY, plan_id=organizer.plan(root, POLICY)["plan_id"])
    preview = organizer.plan(root, POLICY)
    if change == "history":
        journal = latest_sort(root)
        path = root / ".riposte/sort-history" / journal["id"] / "journal.json"
        data = json.loads(path.read_text())
        data["status"] = "APPLYING"
        path.write_text(json.dumps(data))
    else:
        with sqlite3.connect(root / ".riposte/catalog.sqlite3") as db:
            if change == "catalog": db.execute("UPDATE images SET date_source='embedded'")
            else:
                data = json.loads(db.execute("SELECT data FROM sort_titles").fetchone()[0])
                data["original_filename"] = "later-title.png"
                db.execute("UPDATE sort_titles SET data=?", (json.dumps(data),))
    before = snapshot(root)
    with pytest.raises(RiposteError, match="^SORT_PREVIEW_CHANGED$"):
        organizer.organize(root, POLICY, plan_id=preview["plan_id"])
    assert snapshot(root) == before


@pytest.mark.parametrize("change", ["added", "changed", "removed"])
def test_changes_after_execution_starts_never_expand_reviewed_inputs(root, make_image, change):
    first = make_image(root / "a.png")
    second = make_image(root / "b.png", color=(9, 30, 60))
    original = first.read_bytes()
    preview = organizer.plan(root, POLICY)
    def progress(event):
        if event["processed"] != 2: return
        if change == "added": make_image(root / "late.png")
        if change == "changed": second.write_bytes(b"later source edit")
        if change == "removed": second.unlink()
    result = organizer.organize(root, POLICY, progress, plan_id=preview["plan_id"])
    assert result["checkpoint"] == "INCOMPLETE"
    assert result["counts"]["migrated"] == (2 if change == "added" else 1)
    assert {row["relative"] for row in catalog(root)} <= {item["destination"] for item in preview["files"]}
    if change == "added": assert (root / "late.png").exists()
    else: assert result["blockers"]["SORT_PREVIEW_CHANGED"] == 1
    assert organizer.undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert first.read_bytes() == original
    if change == "changed": assert second.read_bytes() == b"later source edit"
    if change == "removed": assert not second.exists()


@pytest.mark.parametrize("change", ["extra", "reviewed_catalog"])
def test_combined_selection_cannot_expand_or_silently_shrink_after_sort(root, make_image, monkeypatch, change):
    import riposte.publication as publication
    from riposte.store import record_image
    make_image(root / "original.png")
    values = {"all_images": True, "date_mode": "modified"}
    preview = execute(Request("sort-riposte-plan", root, values))
    monkeypatch.setattr(publication, "_models", lambda *args: [])
    real = organizer.organize
    extra = []
    def sorted_then_changed(*args, **kwargs):
        result = real(*args, **kwargs)
        row = catalog(root)[0]
        if change == "extra":
            from riposte.sanitize import png_audit
            data = (root / row["relative"]).read_bytes()
            (root / "2025/March/img/SML/SML99.png").write_bytes(data)
            extra.append(record_image(root, "2025/March/img/SML/SML99.png", png_audit(data), len(data), row["date_source"])["id"])
        else:
            import sqlite3
            with sqlite3.connect(root / ".riposte/catalog.sqlite3") as db:
                db.execute("DELETE FROM images")
        return result
    monkeypatch.setattr(organizer, "organize", sorted_then_changed)
    selected = []
    monkeypatch.setattr(publication, "start_publication", lambda root, ids, *args, **kwargs: selected.extend(ids) or {"mode": "PUBLICATION_BATCH"})
    result = execute(Request("sort-riposte", root, {**values, "plan_id": preview["plan_id"]}))
    if change == "extra": assert len(selected) == 1 and not set(selected) & set(extra)
    else: assert result["code"] == "SORT_PREVIEW_CHANGED" and not selected


def test_combined_requires_its_top_level_receipt(root, make_image, monkeypatch):
    make_image(root / "original.png")
    values = {"all_images": True, "date_mode": "modified"}
    preview = execute(Request("sort-riposte-plan", root, values))
    monkeypatch.setattr("riposte.publication._models", lambda *args: pytest.fail("unreviewed models started"))
    for identifier, error in ((None, "SORT_PREVIEW_REQUIRED"), (preview["sorting"]["plan_id"], "SORT_PREVIEW_CHANGED")):
        with pytest.raises(RiposteError, match=error):
            execute(Request("sort-riposte", root, {**values, "plan_id": identifier}))
    assert not (root / ".riposte").exists()
