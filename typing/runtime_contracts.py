"""Offline contract fixtures using real core operations in a temporary workspace.

Publication records are synthetic fixtures, not executed model outputs. This
checks record shapes and signatures, not protection efficacy or UI acceptance.
"""
from __future__ import annotations

import ast
from collections.abc import Sequence
import json
from pathlib import Path
import sys
import tempfile
import types
import typing
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image
from riposte import metrics, models, organizer, publication, quality, sanitize, store
from riposte.terminal import actions, service
from riposte.terminal.jobs import Operation
from riposte.terminal.keyboard import KeyDecoder


def load_records():
    """Load type-only declarations privately for fixture checks; no stub import path."""
    path = ROOT / "typing/stubs/_riposte_types.pyi"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    # The recursive JSON alias is static-only and unused by concrete records.
    tree.body = [n for n in tree.body if not (
        isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        and n.target.id == "JSONValue")]
    module = types.ModuleType("_riposte_contract_fixture_types")
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec", dont_inherit=True), module.__dict__)
    return module


RECORDS = load_records()


def matches(value, expected, label="result"):
    if expected is typing.Any:
        return
    if typing.is_typeddict(expected):
        assert isinstance(value, dict), f"{label}: expected dictionary"
        hints = typing.get_type_hints(expected, include_extras=True)
        missing = expected.__required_keys__ - value.keys()
        extra = value.keys() - hints.keys()
        assert not missing and not extra, f"{label}: missing={missing}, extra={extra}"
        for key, item in value.items():
            matches(item, hints[key], f"{label}.{key}")
        return
    origin, args = typing.get_origin(expected), typing.get_args(expected)
    if origin in (typing.Required, typing.NotRequired):
        return matches(value, args[0], label)
    if origin in (typing.Union, types.UnionType):
        for candidate in args:
            try:
                matches(value, candidate, label)
                return
            except AssertionError:
                pass
        raise AssertionError(f"{label}: {value!r} does not match {expected}")
    if origin is typing.Literal:
        assert any(type(value) is type(item) and value == item for item in args), label
    elif origin in (list, Sequence):
        assert isinstance(value, list if origin is list else Sequence), label
        for item in value:
            matches(item, args[0], label)
    elif origin is tuple:
        assert isinstance(value, tuple), label
        if len(args) == 2 and args[1] is Ellipsis:
            for item in value:
                matches(item, args[0], label)
        else:
            assert len(value) == len(args), label
            for item, kind in zip(value, args):
                matches(item, kind, label)
    elif origin is dict:
        assert isinstance(value, dict), label
        for key, item in value.items():
            matches(key, args[0], label)
            matches(item, args[1], label)
    elif expected in (int, bool, str, bytes, type(None)):
        assert type(value) is expected, f"{label}: expected {expected}, got {type(value)}"
    elif expected is float:
        assert type(value) in (int, float), label
    else:
        assert isinstance(value, expected), label


class ContractFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="riposte-types-", dir=ROOT / "typing/.cache")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = Image.new("RGB", (64, 64), (80, 90, 100))

    def organized(self):
        self.image.save(self.root / "fixture.png")
        matches(organizer.plan(self.root), RECORDS.OrganizationPlan)
        report = organizer.organize(self.root)
        matches(report, RECORDS.OrganizationReport)
        # The source may retain the input when Windows fstat/stat disagree.
        # Both outcomes are part of the actual OrganizationReport contract.
        if report["checkpoint"] == "INCOMPLETE":
            self.assertIn("SOURCE_CHANGED_OUTPUT_RETAINED", report["blockers"])
            self.assertTrue((self.root / "fixture.png").exists())
        else:
            self.assertFalse((self.root / "fixture.png").exists())
        rows = store.catalog(self.root)
        self.assertEqual(len(rows), 1)
        matches(rows[0], RECORDS.CatalogRow)
        return rows[0]

    def test_png_fidelity_quality_and_budget(self):
        raw = sanitize.encode_clean(self.image, "2026-09-16")
        matches(sanitize.png_audit(raw), RECORDS.PngAudit)
        same = metrics.fidelity(self.image, self.image)
        matches(same, RECORDS.FidelityReport)
        self.assertIsNone(same["psnr_db"])
        other = Image.new("RGB", self.image.size, (81, 91, 101))
        changed = metrics.fidelity(self.image, other)
        matches(changed, RECORDS.FidelityReport)
        self.assertIsInstance(changed["psnr_db"], float)
        matches(metrics.transport_report(self.image, other), RECORDS.TransportReport)
        result = quality.quality_report(self.image, other)
        matches(result, RECORDS.QualityReport)
        self.assertEqual(result["status"], "PASS")
        blocked = quality.quality_report(self.image, Image.new("RGB", self.image.size, "white"))
        matches(blocked, RECORDS.QualityReport)
        self.assertEqual(blocked["status"], "BLOCKED")
        budget = quality.spatial_budget(self.image, quality.QualityLimits())
        self.assertEqual(str(budget.dtype), "uint8")
        self.assertEqual(budget.shape, (64, 64))

    def test_organization_catalog_and_image_selection(self):
        row = self.organized()
        matches(organizer.audit_workspace(self.root), RECORDS.WorkspaceAudit)
        matches(store.find_image(self.root, row["id"]), RECORDS.CatalogRow)
        selected = service.select_rows(self.root, month=row["day"][5:7])
        self.assertEqual(selected, [row])
        image = service.view_image(self.root, {"image_id": row["id"]})
        matches(image, RECORDS.ImageInfo)
        self.assertEqual(image["viewer"], "NOT_OPENED")
        self.assertNotIn("relative", image)
        self.assertIsInstance(service.image_bytes(self.root, {"image_id": row["id"]}), bytes)
        with store.workspace_lock(self.root) as held:
            self.assertIsNone(held)

    def test_incomplete_organization_records(self):
        (self.root / "unknown.txt").write_text("fixture", encoding="utf-8")
        preview = organizer.plan(self.root)
        matches(preview, RECORDS.OrganizationPlan)
        self.assertFalse(preview["ready"])
        report = organizer.organize(self.root)
        matches(report, RECORDS.OrganizationReport)
        self.assertEqual(report["checkpoint"], "INCOMPLETE")
        matches(organizer.audit_workspace(self.root), RECORDS.WorkspaceAudit)

    def test_upgrade_optional_fields(self):
        current = store.upgrade_workspace(self.root)
        matches(current, RECORDS.UpgradeReport)
        self.assertNotIn("state_directory", current)
        legacy = self.root / ".shroud"
        legacy.mkdir()
        (legacy / "WORKSPACE").write_text(store.LEGACY_SIGNATURE)
        upgraded = store.upgrade_workspace(self.root)
        matches(upgraded, RECORDS.UpgradeReport)
        self.assertEqual(upgraded["state_directory"], ".riposte")

    def fixture_batch(self):
        # Prepare canonical catalog state directly. This does not claim that
        # source migration succeeded on this Windows/Python runtime.
        raw = sanitize.encode_clean(self.image, "2026-09-16")
        relative = "2026/September/SML/SML01.png"
        store.atomic_clean_write(self.root, relative, raw)
        row = store.record_image(self.root, relative, sanitize.png_audit(raw), len(raw), "embedded")
        recipe = publication.PublishRecipe(edges=(64,))
        matches(recipe.public(), RECORDS.RecipeRecord)
        self.assertEqual(publication.PublishRecipe.from_dict(json.loads(json.dumps(recipe.public()))), recipe)
        planned = publication.publication_plan(self.root, [row["id"]], recipe)
        matches(planned, RECORDS.PublicationPlan)
        batch_id, item_id = "a" * 32, "b" * 32
        request = {
            "id": batch_id, "schema": 1, "sequence": 1,
            "recipe": recipe.public(),
            "tasks": [{**planned["tasks"][0], "id": item_id}],
            "duplicate_renders_avoided": 0,
        }
        prefix = f".riposte/publishing/{batch_id}"
        store.atomic_json_write(self.root, prefix + "/request.json", request)
        return batch_id, item_id, prefix

    def test_synthetic_publication_pending_and_blocked_shapes(self):
        batch_id, item_id, prefix = self.fixture_batch()
        batch = publication.publication_status(self.root, batch_id)
        matches(batch, RECORDS.PublicationBatch)
        self.assertEqual(batch["items"][0]["status"], "PENDING")
        self.assertNotIn("width", batch["items"][0])
        store.atomic_json_write(self.root, prefix + f"/failures/{item_id}.json", {"code": "FIXTURE_ONLY"})
        failed = publication.publication_status(self.root, batch_id)
        matches(failed, RECORDS.PublicationBatch)
        self.assertEqual(failed["items"][0]["status"], "BLOCKED")
        matches(publication.publications(self.root)[0], RECORDS.PublicationSummary)

    def test_synthetic_publication_ready_and_export_shape(self):
        batch_id, item_id, prefix = self.fixture_batch()
        report = {
            "relative": "2026/September/SML/SML01.png", "width": 64, "height": 64,
            "quality": quality.quality_report(self.image, self.image),
            "artifact_sha256": {"clean": "0" * 64, "candidate": "1" * 64},
            "transport": metrics.transport_report(self.image, self.image),
        }
        store.atomic_json_write(self.root, prefix + f"/items/{item_id}/report.json", report)
        ready = publication.publication_status(self.root, batch_id)
        matches(ready, RECORDS.PublicationBatch)
        self.assertEqual(ready["items"][0]["status"], "READY_FOR_REVIEW")
        # Only the export record's shape is under test. No model execution,
        # review approval, or real publishing ZIP is asserted by this fixture.
        with patch.object(publication, "_publication_zip_locked", return_value=b"synthetic fixture"):
            exported = publication.export_publication(self.root, batch_id)
        matches(exported, RECORDS.PublicationExport)

    def test_runtime_and_preflight_shapes_without_model_loading(self):
        matches(models.runtime_capabilities(), RECORDS.RuntimeCapabilities)
        folder = self.root / "model"
        folder.mkdir()
        (folder / "config.json").write_text('{"_class_name":"AutoencoderTiny"}')
        (folder / "fixture.safetensors").write_bytes(b"not real weights; preflight fixture only")
        report = models.inspect_vae(folder)
        matches(report, RECORDS.VaeInspection)
        self.assertNotIn("weights_sha256", report)
        report = models.inspect_vae(folder, fingerprint=True)
        matches(report, RECORDS.VaeInspection)
        self.assertIsInstance(report["weights_sha256"], str)

    def test_operation_callback_and_form_contracts(self):
        def function(request, progress):
            self.assertEqual(request.name, "audit")
            event = {"phase": "Checking fixture", "processed": 1, "total": 1}
            matches(event, RECORDS.ProgressEvent)
            progress(event)
            return {"checkpoint": "COMPLETE"}
        op = Operation(service.Request("audit", self.root), function).start()
        self.assertEqual(op.join(), {"checkpoint": "COMPLETE"})
        self.assertEqual(op.snapshot().state, "DONE")
        decoder = KeyDecoder()
        self.assertIsNone(decoder.feed("x"))
        self.assertEqual(decoder.next().text, "x")
        self.assertIsNone(decoder.next())
        request = actions.make_request("publish", self.root, {}, selected=["c" * 32])
        matches(request.values, RECORDS.RequestValues)
        self.assertIsInstance(actions.command_line(request), str)
        for field, raw in ((actions.Field("words", "Words", "words"), (1.5, "word")),
                           (actions.Field("on", "On", "bool"), "yes")):
            matches(actions.parse_value(field, raw), RECORDS.FormValue)

    def test_validator_rejects_drift(self):
        invalid = {"date": "2026-09-16", "width": "64", "height": 64,
                   "chunks": ["IHDR"], "metadata": "DATE_ONLY", "sha256": "0" * 64}
        with self.assertRaises(AssertionError):
            matches(invalid, RECORDS.PngAudit)
        invalid["width"] = 64
        invalid["original_filename"] = "unexpected"
        with self.assertRaises(AssertionError):
            matches(invalid, RECORDS.PngAudit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
