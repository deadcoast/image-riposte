"""Reproduce bounded development-audit findings without modifying application source.

Run with the repository's existing application environment. These are fault probes,
not a replacement product test suite. A reproduced defect is not a passing product
claim. Publication fixtures are synthetic committed records, not model output.
"""
from __future__ import annotations

import hashlib
import io
import json
import locale
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from riposte.errors import RiposteError
from riposte.organizer import audit_workspace
from riposte.policy import folder_for
from riposte.publication import (
    PublishRecipe, publication_pixels, publication_status, publication_zip,
    review_publication,
)
from riposte.sanitize import encode_clean, png_audit
from riposte.server import create_app
from riposte.store import atomic_clean_write, atomic_json_write, record_image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence/development-audit"
RESULTS: list[dict] = []


def run_probe(name, function):
    try:
        result = function()
        RESULTS.append({"probe": name, "execution": "COMPLETED", **result})
    except Exception as exc:
        RESULTS.append({"probe": name, "execution": "HARNESS_ERROR",
                        "exception": type(exc).__name__, "detail": str(exc)})


def wait_job(app, identifier):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        item = next(j for j in app.state.jobs.snapshot() if j["id"] == identifier)
        if item["state"] not in {"queued", "running"}:
            return item
        time.sleep(.01)
    raise TimeoutError("Job did not finish within five seconds")


def server_probes(root):
    root.mkdir()
    (root / "unmanaged.txt").write_text("audit fixture", encoding="utf-8")
    app = create_app(root, token="audit-fixture-token")
    headers = {"x-riposte-token": "audit-fixture-token"}
    with TestClient(app, raise_server_exceptions=False) as client:
        homepage = client.get("/")
        response = client.post("/api/organize", headers=headers,
                               json={"apply": True, "acknowledge_source_removal": True})
        job = wait_job(app, response.json()["job_id"])
        oversized = b" " * 40000 + b'{"apply":false}'
        fixed = client.post("/api/organize", headers={**headers, "content-type": "application/json"},
                            content=oversized)
        chunked = client.post("/api/organize", headers={**headers, "content-type": "application/json"},
                              content=iter([oversized]))
        chunked_job = (wait_job(app, chunked.json()["job_id"])
                       if chunked.status_code == 200 else None)
        state = client.get("/api/state", headers=headers).json()
        return {
            "boundary": "Real FastAPI ASGI requests; no real TCP socket or browser",
            "homepage": {"status": homepage.status_code,
                         "error": homepage.json() if homepage.status_code == 500 else None},
            "incomplete_organization_job": job,
            "body_limit": {"bytes": len(oversized), "fixed_status": fixed.status_code,
                           "chunked_status": chunked.status_code,
                           "chunked_request_headers": dict(chunked.request.headers),
                           "chunked_finished": chunked_job is not None},
            "api_version": state["version"],
        }


def publication_fixture(root):
    """Commit valid synthetic records without invoking a model or organizer."""
    root.mkdir()
    day = "2026-09-10"
    clean = Image.new("RGB", (64, 64), (110, 130, 150))
    candidate = clean.copy()
    candidate.putpixel((12, 12), (111, 130, 150))
    clean_data, candidate_data = encode_clean(clean, day), encode_clean(candidate, day)
    folder = folder_for(day, *clean.size)
    relative = (folder / (folder.name + "01.png")).as_posix()
    atomic_clean_write(root, relative, clean_data)
    row = record_image(root, relative, png_audit(clean_data), len(clean_data), "modified")
    batch, item = uuid.uuid4().hex, uuid.uuid4().hex
    task = {"id": item, "image_id": row["id"], "date": day, "max_edge": 64,
            "index": 0, "source_clean_sha256": row["sha256"]}
    recipe = PublishRecipe(edges=(64,))
    from riposte.quality import quality_report
    from riposte.metrics import transport_report
    prefix = f".riposte/publishing/{batch}"
    request = {"id": batch, "schema": 1, "sequence": 1, "recipe": recipe.public(),
               "tasks": [task], "duplicate_renders_avoided": 0}
    report = {**task, "batch_id": batch, "relative": relative, "width": 64, "height": 64,
              "artifact_sha256": {"clean": hashlib.sha256(clean_data).hexdigest(),
                                   "candidate": hashlib.sha256(candidate_data).hexdigest()},
              "quality": quality_report(clean, candidate, recipe.quality),
              "transport": transport_report(clean, candidate),
              "guard": {"fixture": True}, "ai_protection": "UNVERIFIED"}
    atomic_json_write(root, prefix + "/request.json", request)
    atomic_json_write(root, prefix + "/outcome.json", {"status": "FINISHED"})
    for name, data in (("clean", clean_data), ("candidate", candidate_data)):
        atomic_clean_write(root, prefix + f"/items/{item}/{name}.png", data)
    atomic_json_write(root, prefix + f"/items/{item}/report.json", report)
    return batch, item, root / prefix / "items" / item / "candidate.png", clean, row


def error_code(fn):
    try:
        fn()
        return "NO_ERROR"
    except RiposteError as exc:
        return exc.code


def review_probes(root):
    batch, item, candidate_path, clean, _ = publication_fixture(root)
    checkpoint = audit_workspace(root)["checkpoint"]
    approved = review_publication(root, batch, [item], "ACCEPTED", True, True)
    original_pack = publication_zip(root, batch)
    with zipfile.ZipFile(io.BytesIO(original_pack)) as archive:
        pack_entries = archive.namelist()
    clean.putpixel((12, 12), (112, 130, 150))
    candidate_path.write_bytes(encode_clean(clean, "2026-09-10"))
    after = publication_status(root, batch)
    rejected = error_code(lambda: review_publication(root, batch, [item], "REJECTED"))
    return {
        "boundary": "Synthetic committed publication; real storage, review, status, PNG verification and ZIP paths; no model generation",
        "control_checkpoint": checkpoint,
        "control_accepted": approved["counts"]["ACCEPTED"], "control_zip_entries": pack_entries,
        "after_candidate_changed": after,
        "reject_changed_candidate": rejected,
        "serve_changed_candidate": error_code(lambda: publication_pixels(root, batch, item)),
        "pack_changed_candidate": error_code(lambda: publication_zip(root, batch)),
    }


def terminal_probe(root):
    from riposte.terminal.app import _line_command
    from riposte.terminal.controller import Controller
    from riposte.terminal.output import Presentation
    from riposte.terminal.interaction import fields_for
    root.mkdir()
    controller = Controller(root, Presentation(plain=True))
    controller.action("doctor")
    fields = fields_for(controller.state.page)
    _line_command(controller, "focus 3")
    after_focus = controller.state.page.cursor
    _line_command(controller, "down")
    return {"boundary": "Real controller and line-command parser; no native terminal host",
            "page": controller.state.page.name, "field_names": [f.key for f in fields],
            "requested_zero_based_index": 2, "cursor_after_focus_3": after_focus,
            "cursor_after_down_control": controller.state.page.cursor}


def optional_preflight_probe(root):
    import riposte.models as models
    import riposte.runtime_probe as runtime
    import riposte.temporal as temporal
    import riposte.publication as publication
    calls = {"encoder_probe": 0, "inpaint_calls": 0, "temporal_calls": 0}
    class Encoder:
        device = "cpu"
        identity = {"fixture": "encoder"}
        def __init__(self, *args): pass
    class Inpaint:
        identity = {"fixture": "inpaint"}
        def __init__(self, *args): pass
        def __call__(self, *args, **kwargs):
            calls["inpaint_calls"] += 1
            raise RuntimeError("Deliberately non-executable optional fixture")
    class Temporal:
        identity = {"fixture": "temporal"}
        def __init__(self, *args): pass
        def __call__(self, *args, **kwargs):
            calls["temporal_calls"] += 1
            raise RuntimeError("Deliberately non-executable optional fixture")
    def encoder_probe(model):
        calls["encoder_probe"] += 1
        return {"fixture": "successful encoder probe"}
    _, _, _, _, row = publication_fixture(root)
    def at_run(workspace, request, selected_models, progress):
        return {"request_committed_before_optional_execution":
                (workspace / ".riposte/publishing" / request["id"] / "request.json").is_file(),
                "calls_at_request_commit": dict(calls)}
    with patch.object(models, "LocalEncoder", Encoder), patch.object(models, "LocalInpaintProbe", Inpaint), \
            patch.object(temporal, "LocalTemporalProbe", Temporal), patch.object(runtime, "probe_encoder", encoder_probe), \
            patch.object(publication, "_run", at_run):
        result = publication.start_publication(root, [row["id"]], [Path("fixture-encoder")],
                                               pipeline_dir=Path("fixture-inpaint"),
                                               temporal_dir=Path("fixture-temporal"))
    return {"boundary": "Controlled loader and execution instrumentation; proves call order only, not numerical model behavior", **result}


def organizer_probe(root):
    from riposte.organizer import organize
    from riposte.policy import Policy, same_file_state
    from riposte.store import catalog
    root.mkdir()
    immediate = root / "immediate"
    immediate.mkdir()
    Image.new("RGB", (64, 48), (30, 90, 150)).save(immediate / "input.png")
    immediate_result = organize(immediate, Policy(date_mode="modified"))
    changed = root / "dated"
    changed.mkdir()
    source = changed / "input.png"
    Image.new("RGB", (64, 48), (30, 90, 150)).save(source)
    time.sleep(.02)
    os.utime(source, (1725984000, 1725984000))
    with source.open("rb") as stream:
        descriptor, pathname = os.fstat(stream.fileno()), source.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    results = []
    for _ in range(3):
        result = organize(changed, Policy(date_mode="modified"))
        results.append({"checkpoint": result["checkpoint"], "blockers": result["blockers"],
                        "catalog_images": len(catalog(changed)), "raw_source_present": source.exists()})
    return {"boundary": "Real Windows filesystem and organizer, synthetic PNG; no mocked stat results",
            "immediate_control_checkpoint": immediate_result["checkpoint"],
            "dated_fixture_setup": "Save PNG, wait 20ms, set atime/mtime to a historical timestamp, then organize",
            "fstat": {f: getattr(descriptor, f) for f in fields},
            "stat": {f: getattr(pathname, f) for f in fields},
            "same_file_state": same_file_state(descriptor, pathname), "successive_runs": results}


def browser_checkpoint_probe():
    # Execute the exact function body with boundary collaborators substituted.
    # This tests the assignment, not browser rendering or the full JS application.
    source = ROOT / "src/riposte/static/publish.js"
    node = r"""
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const match = source.match(/function completed\(result\)\{[^\n]*\}/);
if (!match) throw new Error('Expected function not found; review changed source');
let renders=0;
const context={current:'',batch:null,state:{audit:{checkpoint:'INCOMPLETE',unmanaged:1}},
 renderAuditBadge:()=>renders++,renderBatch:()=>{},setView:()=>{}};
vm.createContext(context);vm.runInContext(match[0],context);
context.completed({id:'synthetic-blocked-batch',mode:'PUBLICATION_BATCH',counts:{BLOCKED:1}});
process.stdout.write(JSON.stringify({after:context.state.audit,badge_renders:renders}));
"""
    command = ["node", "-e", node, str(source)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return {"boundary": "Exact completed() source function in Node VM; DOM collaborators substituted; not browser acceptance",
            "before": {"checkpoint": "INCOMPLETE", "unmanaged": 1},
            "command": command, **json.loads(result.stdout)}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary_parent = ROOT / "typing/.cache/development-audit"
    temporary_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="probes-", dir=temporary_parent) as temporary:
        base = Path(temporary)
        run_probe("server", lambda: server_probes(base / "server"))
        run_probe("publication_review", lambda: review_probes(base / "publication"))
        run_probe("terminal_focus", lambda: terminal_probe(base / "terminal"))
        run_probe("optional_model_preflight", lambda: optional_preflight_probe(base / "preflight"))
        run_probe("organizer_retry", lambda: organizer_probe(base / "organizer"))
        run_probe("browser_checkpoint", browser_checkpoint_probe)
    document = {"python": sys.version, "platform": platform.platform(),
                "preferred_encoding": locale.getpreferredencoding(False),
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "command": [sys.executable, "scripts/audit_development.py"], "probes": RESULTS}
    (OUTPUT / "probes.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(document, indent=2))
    return int(any(r["execution"] == "HARNESS_ERROR" for r in RESULTS))


if __name__ == "__main__":
    raise SystemExit(main())
