"""Read-only-source development audit; every mutating probe uses synthetic .tmp files.

A successful script proves these observations reproduced, not that the product
passes their proposed repair criteria. No user artwork, model downloads or
application-source edits are involved.
"""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient
from typer.testing import CliRunner
from riposte import organizer, store
from riposte.category_rules import build_rules, load_rules, save_rules
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.server import create_app
from riposte.sort_history import undo_sort
from riposte.terminal.paths import validate_workspace

ROOT = Path(__file__).resolve().parents[2]
POLICY = Policy(date_mode="modified")


def hashes():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src/riposte").rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def picture(path, index=0):
    Image.new("RGB", (32, 24), (index % 256, 80, 150)).save(path)
    stamp = dt.datetime(2025, 3, 12, 12).timestamp()
    os.utime(path, (stamp, stamp))


def code(call):
    try:
        call()
    except RiposteError as exc:
        return exc.code
    return "ACCEPTED"


def run():
    before = hashes()
    scratch = ROOT / ".tmp/development-review"
    scratch.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="probes-", dir=scratch))
    findings = {}

    crash = work / "crash"
    crash.mkdir()
    source = crash / "original.png"
    picture(source)
    original = source.read_bytes()
    child = subprocess.run([sys.executable, "-c", "\n".join([
        "import os,sys", "from pathlib import Path",
        "from riposte.store import workspace_lock",
        "from riposte.sort_history import SortHistory",
        "root=Path(sys.argv[1])",
        "with workspace_lock(root):",
        " history=SortHistory(root)",
        " history.prepare(root/'original.png',None,None,'img')",
        " os._exit(23)",
    ]), str(crash)], capture_output=True, text=True, timeout=20)
    assert child.returncode == 23, child.stderr
    preview = undo_sort(crash)
    apply_code = code(lambda: undo_sort(crash, apply=True, sort_id=preview["sort_id"]))
    assert preview["ready"] and apply_code == "WORKSPACE_LOCKED"
    assert source.read_bytes() == original
    findings["crash_lock"] = {"child_exit": 23, "undo_preview_ready": True,
        "undo_apply_code": apply_code, "lock_bytes": (crash / ".riposte/operation.lock").stat().st_size,
        "source_intact": True, "scope": "Actual child process exits without lock cleanup; recovery preview succeeds but apply is blocked."}

    overlap = work / "application-subfolder"
    overlap.mkdir()
    picture(overlap / "fixture.png")
    terminal_code = code(lambda: validate_workspace(overlap))
    cli = CliRunner().invoke(app, ["--json", "sort", str(overlap), "--date-mode", "modified", "--apply"])
    assert terminal_code == "IMAGE_FOLDER_OVERLAPS_APPLICATION"
    assert cli.exit_code == 0, cli.output
    applied = json.loads(cli.stdout)
    assert applied["counts"]["migrated"] == 1
    findings["application_overlap"] = {"terminal": terminal_code, "direct_cli_exit": cli.exit_code,
        "direct_cli_migrated": 1, "scope": "Real CLI accepts a synthetic folder inside this application checkout that the terminal picker rejects."}

    changed = work / "ordinary-preview"
    changed.mkdir()
    picture(changed / "first.png")
    preview = organizer.plan(changed, POLICY)
    picture(changed / "added-after-preview.png", 1)
    applied = organizer.organize(changed, POLICY)
    assert preview["counts"]["images_to_migrate"] == 1
    assert applied["counts"]["migrated"] == 2
    findings["ordinary_preview"] = {"preview_images": 1, "applied_images": 2,
        "has_preview_id": "plan_id" in preview,
        "scope": "Ordinary sorting has directory-wide apply semantics; unlike category sorting, it does not bind apply to the displayed snapshot."}

    measurements = []
    for count in (16, 32):
        collection = work / f"collection-{count}"
        collection.mkdir()
        for i in range(count):
            picture(collection / f"hockey-{i}.png", i)
        save_rules(collection, build_rules(["Hockey=hockey"]), expected_revision=load_rules(collection).revision)
        preview = organizer.plan(collection, POLICY, categories=True)
        assert organizer.organize(collection, POLICY, categories=True, plan_id=preview["plan_id"])["checkpoint"] == "COMPLETE"
        calls, returned = [], []
        original_titles = organizer.title_records

        def titles(root):
            rows = original_titles(root)
            calls.append(1)
            returned.append(len(rows))
            return rows

        with patch.object(organizer, "title_records", titles):
            assert organizer.audit_workspace(collection)["checkpoint"] == "COMPLETE"
        reads, row_counts = [], []
        original_catalog = store.catalog

        def catalog(root):
            rows = original_catalog(root)
            reads.append(1)
            row_counts.append(len(rows))
            return rows

        ids = [row["id"] for row in original_catalog(collection)]
        with patch.object(store, "catalog", catalog):
            for identifier in ids:
                store.find_image(collection, identifier)
        assert len(calls) == count and sum(returned) == count * count
        assert len(reads) == count and sum(row_counts) == count * count
        measurements.append({"images": count, "audit_title_reads": len(calls),
            "audit_title_rows": sum(returned), "selection_catalog_reads": len(reads),
            "selection_catalog_rows": sum(row_counts)})
    findings["catalog_scaling"] = {"measurements": measurements,
        "scope": "Real SQLite/catalog work with call instrumentation; row counts establish quadratic repeated reads, not a wall-clock benchmark."}

    webroot = work / "browser-preview"
    webroot.mkdir()
    release = threading.Event()
    started = threading.Event()

    def slow_preview(root, policy, progress, **kwargs):
        started.set()
        release.wait(10)
        return {"mode": "READ_ONLY", "counts": {}, "blockers": {}}

    with patch("riposte.server.plan", slow_preview), TestClient(create_app(webroot, "audit-token")) as client:
        client.headers["X-Riposte-Token"] = "audit-token"
        try:
            response = client.post("/api/organize", json={"apply": False}).json()
            assert started.wait(5)
            cancel = client.post(f"/api/jobs/{response['job_id']}/cancel")
            assert cancel.status_code == 400 and cancel.json()["code"] == "JOB_CANCELLATION_UNSUPPORTED"
        finally:
            release.set()
        for _ in range(100):
            if client.get("/api/state").json()["jobs"][0]["state"] == "done":
                break
            time.sleep(.01)
        findings["browser_scan_cancel"] = {"preview_job_cancel_code": cancel.json()["code"],
            "scope": "Real API job/cancel path with a controlled read-only work function; no model or browser rendering involved."}

    after = hashes()
    assert before == after
    review = json.loads((Path(__file__).parent / "review.json").read_text(encoding="utf-8"))
    assert review["sources"] == after
    assert {item["group"] for item in review["findings"]} == {1, 2, 3, 4}
    assert len(review["findings"]) == len({item["id"] for item in review["findings"]}) == 16
    csv.field_size_limit(10_000_000)
    with (ROOT / "todo.PACER.csv").open(encoding="utf-8", newline="") as stream:
        tasks = {row["ID"]: row for row in csv.DictReader(stream)}
    for item in review["findings"]:
        row = tasks[item["id"]]
        assert row["Status"] == "TODO" and row["ApprovalState"] == "PENDING"
        assert row["Priority"] == item["priority"]
        assert item["sources"] and item["acceptance"] and item["impact"]
        for location in item["sources"]:
            path, line = location.rsplit(":", 1)
            assert (ROOT / path).is_file()
            assert 1 <= int(line) <= len((ROOT / path).read_text(encoding="utf-8").splitlines())
        if item["id"] != "PAC-015":
            assert row["Title"] == item["title"]
            assert row["ValidationCriteria"] == item["acceptance"]
    with (ROOT / "organism.PACER.csv").open(encoding="utf-8", newline="") as stream:
        requirements = {row["ID"]: row for row in csv.DictReader(stream)}
    assert all(requirements[key]["Status"] == "PACED_REQUIREMENT" for key in ("OGM-012", "OGM-018"))
    return {"probe_status": "OBSERVATIONS_REPRODUCED", "application_acceptance": "NOT_A_PASS_CLAIM",
        "command": ".venv/Scripts/python.exe evidence/development-review-2026-09-18/probes.py",
        "source_unchanged": True, "sources": before, "findings": findings,
        "review_checks": {"groups": 4, "items": 16, "todo_entries_pending": True,
                          "source_links_exist": True, "recovery_acceptance_incomplete": True},
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
