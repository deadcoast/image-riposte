"""Bounded parent acceptance: large discovery and saved publishing references.

Run with the existing repository Python. Fixtures stay in ignored .tmp/.
No model is loaded or protection efficacy asserted.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import tracemalloc
from unittest.mock import patch

from PIL import Image
from riposte import publication
from riposte.category_rules import build_rules, load_rules, save_rules
from riposte.errors import RiposteError
from riposte.organizer import organize, plan, undo_sort
from riposte.policy import Policy
from riposte.store import catalog
from riposte.title_categories import discover_categories


def verify():
    repo = Path(__file__).resolve().parents[2]
    scratch = repo / ".tmp" / "category-sort"
    scratch.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="parent-", dir=scratch))
    large = workspace / "large"
    large.mkdir()
    for index in range(10_000):
        (large / f"winter-hockey-goalie-{index:05}.png").touch()
    tracemalloc.start()
    started = time.perf_counter()
    report = discover_categories(large)
    seconds = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert report["checkpoint"] == "COMPLETE"
    assert report["counts"]["analyzed_files"] == 10_000
    assert next(x for x in report["candidates"] if x["term"] == "hockey")["count"] == 10_000
    assert not (large / ".riposte").exists()
    events = []

    def cancel(event):
        events.append(event)
        if event.get("processed", 0) >= 500:
            raise RiposteError("JOB_CANCELLED")

    try:
        discover_categories(large, progress=cancel)
    except RiposteError as exc:
        assert str(exc) == "JOB_CANCELLED"
    else:
        raise AssertionError("Cancellation was ignored")
    assert not (large / ".riposte").exists()
    assert "hockey" not in json.dumps(events)
    assert all(p.stat().st_size == 0 for p in large.iterdir())

    root = workspace / "publishing"
    root.mkdir()
    source = root / "hockey-goalie.png"
    Image.new("RGB", (64, 48), (30, 90, 150)).save(source)
    stamp = dt.datetime(2025, 3, 12, 12).timestamp()
    os.utime(source, (stamp, stamp))
    policy = Policy(date_mode="modified")
    organize(root, policy)
    original = catalog(root)[0]
    original_bytes = (root / original["relative"]).read_bytes()
    # Exercise the real request writer, replacing only model execution.
    with patch.object(publication, "_run", lambda root, request, models, progress: request):
        request = publication.start_publication(
            root, [original["id"]], [], _loaded_models=([], None, None, {}, [])
        )
    request_path = root / ".riposte" / "publishing" / request["id"] / "request.json"
    request_bytes = request_path.read_bytes()
    for label in ("Hockey", "Winter"):
        save_rules(root, build_rules([f"{label}=hockey"]), expected_revision=load_rules(root).revision)
        preview = plan(root, policy, categories=True)
        assert preview["ready"]
        assert organize(root, policy, categories=True, plan_id=preview["plan_id"])["checkpoint"] == "COMPLETE"
        saved = publication._request(root, request["id"])
        resolved = publication._source_row(root, saved, saved["tasks"][0])
        assert resolved["id"] == original["id"]
        assert resolved["sha256"] == original["sha256"]
        assert f"/{label.lower()}/" in resolved["relative"]
        assert (root / resolved["relative"]).read_bytes() == original_bytes
        assert request_path.read_bytes() == request_bytes
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    restored = publication._source_row(root, request, request["tasks"][0])
    assert "/hockey/" in restored["relative"]
    assert (root / restored["relative"]).read_bytes() == original_bytes
    assert request_path.read_bytes() == request_bytes
    return {
        "result": "PASS",
        "command": ".venv/Scripts/python.exe evidence/category-sort/verify_parent.py",
        "large_discovery": {"files": 10_000, "seconds": seconds, "peak_traced_bytes": peak,
                            "hockey_document_frequency": 10_000, "cancelled_after": 500,
                            "writes": False, "media_decoded": False},
        "publishing_references": "Real saved request retains image identity, clean bytes and request bytes across two category moves and undo; model execution replaced with a fixture.",
        "sources": {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((repo / "src" / "riposte").rglob("*.py"))},
        "verifier_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
