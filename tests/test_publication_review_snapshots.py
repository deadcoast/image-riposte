"""Actual publication storage and image verification; no model dependency."""
import gc
import hashlib
import io
import json
from pathlib import Path
import uuid
import weakref
from zipfile import ZipFile

from PIL import Image
import pytest

from riposte import publication as p
from riposte.errors import RiposteError
from riposte.metrics import transport_report
from riposte.policy import folder_for
from riposte.quality import quality_report
from riposte.sanitize import encode_clean, png_audit
from riposte.store import atomic_clean_write, atomic_json_write, record_image


@pytest.fixture
def ready_batch(root):
    day = "2026-09-10"
    batch_id = uuid.uuid4().hex
    prefix = f".riposte/publishing/{batch_id}"
    tasks = []
    for index in range(6):
        clean = Image.new("RGB", (64, 64), (90 + index, 120, 150))
        candidate = clean.copy()
        candidate.putpixel((12, 12), (91 + index, 120, 150))
        clean_bytes, candidate_bytes = encode_clean(clean, day), encode_clean(candidate, day)
        relative = (folder_for(day, 64, 64) / f"SML{index + 1:02d}.png").as_posix()
        atomic_clean_write(root, relative, clean_bytes)
        row = record_image(root, relative, png_audit(clean_bytes), len(clean_bytes), "modified")
        task = {"id": uuid.uuid4().hex, "image_id": row["id"], "date": day, "max_edge": 64,
                "index": index, "source_clean_sha256": row["sha256"]}
        tasks.append(task)
        item_prefix = f"{prefix}/items/{task['id']}"
        for kind, data in (("clean", clean_bytes), ("candidate", candidate_bytes)):
            atomic_clean_write(root, f"{item_prefix}/{kind}.png", data)
        atomic_json_write(root, f"{item_prefix}/report.json", {**task, "batch_id": batch_id,
            "relative": relative, "width": 64, "height": 64,
            "artifact_sha256": {"clean": hashlib.sha256(clean_bytes).hexdigest(),
                                "candidate": hashlib.sha256(candidate_bytes).hexdigest()},
            "quality": quality_report(clean, candidate), "transport": transport_report(clean, candidate),
            "guard": {"fixture": "REVIEW_STORAGE_REGRESSION"}, "ai_protection": "UNVERIFIED"})
    request = {"id": batch_id, "schema": 1, "sequence": 1, "recipe": p.PublishRecipe((64,)).public(),
               "tasks": tasks, "duplicate_renders_avoided": 0}
    atomic_json_write(root, f"{prefix}/request.json", request)
    atomic_json_write(root, f"{prefix}/outcome.json", {"status": "FINISHED"})
    return request


def accept(root, request):
    return p.review_publication(root, request["id"], [task["id"] for task in request["tasks"]],
                                "ACCEPTED", True, True)


def item_folder(root, request, index=0):
    return root / ".riposte/publishing" / request["id"] / "items" / request["tasks"][index]["id"]


def test_review_releases_decoded_images_before_writing_receipts(root, ready_batch, monkeypatch):
    references, live_at_write, live_during_validation = [], [], []
    verify, write = p._verified_item, p._replace_json

    def measured_verify(*args):
        result = verify(*args)
        references.extend(weakref.ref(image) for image in result[1].values())
        gc.collect()
        live_during_validation.append(sum(reference() is not None for reference in references))
        return result

    def measured_write(*args):
        gc.collect()
        live_at_write.append(sum(reference() is not None for reference in references))
        return write(*args)

    monkeypatch.setattr(p, "_verified_item", measured_verify)
    monkeypatch.setattr(p, "_replace_json", measured_write)
    result = accept(root, ready_batch)
    assert result["counts"]["ACCEPTED"] == 6
    assert live_at_write == [0] * 6
    assert max(live_during_validation) == 2


def test_last_invalid_item_leaves_entire_selection_unapproved(root, ready_batch):
    (item_folder(root, ready_batch, -1) / "candidate.png").write_bytes(b"invalid")
    with pytest.raises(RiposteError):
        accept(root, ready_batch)
    assert not (root / ".riposte/publishing" / ready_batch["id"] / "reviews").exists()


@pytest.mark.parametrize("operation", ["verify", "review", "export"])
def test_report_replaced_during_verification_cannot_supply_approval_hash(root, ready_batch, monkeypatch, operation):
    request = ready_batch
    if operation == "export":
        accept(root, request)
    path = item_folder(root, request) / "report.json"
    initial_bytes = path.read_bytes()
    replacement = json.loads(initial_bytes)
    replacement["guard"]["note"] = "Changed after report parsing"
    replacement_bytes = json.dumps(replacement).encode("utf-8")
    measure = p.quality_report
    writes = []

    def replace_report(*args, **kwargs):
        if not writes:
            path.write_bytes(replacement_bytes)
            writes.append(1)
        return measure(*args, **kwargs)

    monkeypatch.setattr(p, "quality_report", replace_report)
    if operation == "verify":
        report, _, _, digest = p._verified_item(root, request, request["tasks"][0])
        assert report == json.loads(initial_bytes)
        assert digest == hashlib.sha256(initial_bytes).hexdigest()
    elif operation == "review":
        result = accept(root, request)
        assert result["items"][0]["review"] == "STALE"
        with pytest.raises(RiposteError, match="PUBLICATION_REVIEW_STALE"):
            p.publication_zip(root, request["id"])
    else:
        # This operation already read the approved snapshot. It may finish that
        # exact snapshot; the next operation must observe the changed report.
        raw = p.publication_zip(root, request["id"])
        with ZipFile(io.BytesIO(raw)) as archive:
            assert len(archive.namelist()) == 6
        with pytest.raises(RiposteError, match="PUBLICATION_REVIEW_STALE"):
            p.publication_zip(root, request["id"])
    assert writes == [1]


def test_multi_item_review_export_and_revocation_preserve_exact_bytes(root, ready_batch):
    before = {path: path.read_bytes() for path in root.rglob("*.png")}
    accept(root, ready_batch)
    with ZipFile(io.BytesIO(p.publication_zip(root, ready_batch["id"]))) as archive:
        assert len(archive.namelist()) == 6
        for index, task in enumerate(ready_batch["tasks"]):
            report = json.loads((item_folder(root, ready_batch, index) / "report.json").read_text())
            assert archive.read(report["relative"]) == (item_folder(root, ready_batch, index) / "candidate.png").read_bytes()
    rejected = p.review_publication(root, ready_batch["id"], [ready_batch["tasks"][0]["id"]], "REJECTED")
    assert rejected["counts"]["ACCEPTED"] == 5
    with ZipFile(io.BytesIO(p.publication_zip(root, ready_batch["id"]))) as archive:
        assert len(archive.namelist()) == 5
    assert before == {path: path.read_bytes() for path in root.rglob("*.png")}


@pytest.mark.parametrize("length", [8_388_608, 8_388_609])
def test_record_byte_limit(root, length):
    path = root / "record.json"
    path.write_bytes(b"{}" + b" " * (length - 2))
    if length <= 8_388_608:
        assert p._read(root, "record.json") == {}
    else:
        with pytest.raises(RiposteError, match="PUBLICATION_RECORD_INVALID"):
            p._read(root, "record.json")


def test_record_growth_after_stat_does_not_bypass_limit(root, monkeypatch):
    path = root / "record.json"
    path.write_bytes(b"{}")
    calls = []
    original_open = Path.open

    class GrowingFile(io.BytesIO):
        def read(self, size=-1):
            calls.append(size)
            return super().read(size)

    def opened(file, *args, **kwargs):
        if file == path:
            return GrowingFile(b"{}" + b" " * 8_388_608)
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(RiposteError, match="PUBLICATION_RECORD_INVALID"):
        p._read(root, "record.json")
    assert calls == [8_388_609]


@pytest.mark.parametrize("data", [b"[]", b"broken json", b"\xff", b"null"])
def test_invalid_records_remain_sanitized(root, data):
    (root / "record.json").write_bytes(data)
    with pytest.raises(RiposteError, match="PUBLICATION_RECORD_(INVALID|UNREADABLE)"):
        p._read(root, "record.json")
