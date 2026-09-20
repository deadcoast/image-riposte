"""Measure real SQLite returned rows/bytes, elapsed time and Python peak memory."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from test_catalog_scaling import POLICY, collection, read_meter
from riposte import organizer, store


def main():
    samples = []
    with tempfile.TemporaryDirectory(prefix="riposte-catalog-scaling-") as temporary:
        for count in (16, 32, 64):
            root = Path(temporary) / str(count)
            root.mkdir()
            rows = collection(root, count)
            for operation in ("audit", "lookup", "apply_keep", "apply_new"):
                if operation == "apply_new":
                    data = (root / rows[0]["relative"]).read_bytes()
                    for index in range(count): (root / f"hockey-new-{index}.png").write_bytes(data)
                preview = organizer.plan(root, POLICY, categories=True)
                tracemalloc.start()
                started = time.perf_counter()
                with read_meter() as reads:
                    if operation == "audit": assert organizer.audit_workspace(root)["checkpoint"] == "COMPLETE"
                    elif operation == "lookup":
                        for row in rows: assert store.find_image(root, row["id"]) == row
                    else: assert organizer.organize(root, POLICY, categories=True, plan_id=preview["plan_id"])["checkpoint"] == "COMPLETE"
                elapsed = time.perf_counter() - started
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                samples.append({"images_before": count, "added_images": count if operation == "apply_new" else 0,
                                "operation": operation, **reads, "seconds": elapsed, "python_peak_bytes": peak})
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    return {"measurements": samples, "sources": sources,
            "scope": "Synthetic 32x24 PNG collections on this Windows runtime. Bytes are returned SQL rows serialized to JSON, not filesystem IO. Time and tracemalloc peak include instrumentation. No whole-sort linear-time or user-latency guarantee; recovery journal persistence and image work remain separate costs."}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
