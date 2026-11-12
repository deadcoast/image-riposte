"""The main product path: protect a selection -> review -> date-only image pack.

Clean masters never change. Models are loaded once per batch; every requested
size is optimized from its own clean raster. Completed items survive cooperative
cancellation and are verified before resume, review, image serving or download.
Only approved PNGs enter a publishing ZIP; no reports, paths or model identities.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, replace
import hashlib
import io
import json
import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, Mapping
from PIL import Image
from .errors import RiposteError
from .policy import folder_for, valid_day
from .quality import QualityLimits, quality_report
from .spatial import ArtistMask, checked_masks, mask_for, preview as spatial_preview
from .release_guard import ReleaseConfig, protect_release
from .sanitize import encode_clean, png_audit, social_render
from .metrics import transport_report
from .store import (check_root, safe_child, state_relative, workspace_lock, find_image,
                    atomic_clean_write, atomic_json_write)

@dataclass(frozen=True)
class PublishRecipe:
    edges: tuple[int, ...] = (1536,)
    guard: ReleaseConfig = ReleaseConfig()
    quality: QualityLimits = QualityLimits()
    masks: tuple[ArtistMask, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.edges, tuple) or not 1 <= len(self.edges) <= 3
            or len(set(self.edges)) != len(self.edges)
            or any(type(n) is not int or not 64 <= n <= 4096 for n in self.edges)
            or not isinstance(self.guard, ReleaseConfig) or not isinstance(self.quality, QualityLimits)):
            raise RiposteError("PUBLICATION_RECIPE_INVALID")
        checked_masks(self.masks)

    def public(self) -> dict[str, object]:
        value: dict[str, object] = {"edges": self.edges, "guard": asdict(self.guard), "quality": asdict(self.quality)}
        if self.masks:
            value["masks"] = [mask.public() for mask in self.masks]
        return value

    def budget_revision(self) -> str | None:
        if not self.masks:
            return None
        value = {"masks": [mask.public() for mask in self.masks], "edges": self.edges, "quality": asdict(self.quality)}
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @classmethod
    def from_dict(cls, data):
        try:
            if set(data) not in ({"edges", "guard", "quality"}, {"edges", "guard", "quality", "masks"}): raise ValueError
            if "masks" in data and not isinstance(data["masks"], list): raise ValueError
            return cls(tuple(data["edges"]), ReleaseConfig(**data["guard"]), QualityLimits(**data["quality"]),
                       tuple(ArtistMask.from_dict(item) for item in data.get("masks", [])))
        except (TypeError, KeyError, ValueError): raise RiposteError("PUBLICATION_RECIPE_INVALID") from None


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise RiposteError("PUBLICATION_NOT_FOUND")
    return value


def _prefix(root, batch_id): return state_relative(root, f"publishing/{_id(batch_id)}")


def _read(root, relative):
    return _read_record(root, relative)[0]


def _read_record(root, relative):
    """Parse one bounded snapshot and retain its exact bytes for receipt hashes."""
    path = safe_child(root, relative)
    try:
        with path.open("rb") as stream:
            raw = stream.read(8_388_609)
        if len(raw) > 8_388_608: raise RiposteError("PUBLICATION_RECORD_INVALID")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict): raise RiposteError("PUBLICATION_RECORD_INVALID")
        return data, raw
    except (ValueError, OSError): raise RiposteError("PUBLICATION_RECORD_UNREADABLE") from None


def _replace_json(root, relative, report):
    data = json.dumps(report, sort_keys=True, indent=2, allow_nan=False).encode()
    dest = safe_child(root, relative)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.parent / (".report-" + uuid.uuid4().hex + ".tmp")
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, dest)
    finally: temp.unlink(missing_ok=True)


def _checkpoint(root):
    from .organizer import audit_workspace
    if audit_workspace(root)["checkpoint"] != "COMPLETE":
        raise RiposteError("ORGANIZATION_CHECKPOINT_REQUIRED")


def publication_plan(root, image_ids, recipe: PublishRecipe = PublishRecipe(), *, input_paths=None, date_mode="download", budget_offset: int = 0, _include_budget_previews: bool = True) -> dict:
    check_root(root)
    if input_paths:
        if image_ids:
            raise RiposteError("INPUT_SELECTION_CONFLICT")
        from .intake import inspect_inputs
        from .policy import Policy
        sources, ignored = inspect_inputs(input_paths, Policy(date_mode=date_mode))
        result = {**_plan_rows([source.row for source in sources], recipe),
                  "source_mode": "snapshot", "ignored_files": ignored, "originals_preserved": True}
        if recipe.masks and _include_budget_previews:
            page = _preview_tasks(result, budget_offset)
            previews = []
            for source in sources:
                edges = tuple(task["max_edge"] for task in page if task["image_id"] == source.row["id"])
                if edges:
                    with Image.open(io.BytesIO(source.snapshot(Policy(date_mode=date_mode)))) as image:
                        previews.extend(_budget_previews(image, source.row, replace(recipe, edges=edges)))
            result["budget_previews"] = previews
        return result
    if (not isinstance(image_ids, (list, tuple)) or not 1 <= len(image_ids) <= 200
        or len(set(image_ids)) != len(image_ids)):
        raise RiposteError("PUBLICATION_SELECTION_INVALID")
    rows = [find_image(root, _id(identifier)) for identifier in image_ids]
    result = _plan_rows(rows, recipe)
    if recipe.masks and _include_budget_previews:
        page = _preview_tasks(result, budget_offset)
        previews = []
        for row in rows:
            edges = tuple(task["max_edge"] for task in page if task["image_id"] == row["id"])
            if edges:
                with Image.open(safe_child(root, row["relative"])) as image:
                    previews.extend(_budget_previews(image, row, replace(recipe, edges=edges)))
        result["budget_previews"] = previews
    return result


def _preview_tasks(result: dict[str, Any], offset: int) -> list[dict[str, Any]]:
    tasks = [task for task in result["tasks"] if task.get("artist_mask_sha256")]
    if type(offset) is not int or not 0 <= offset < max(1, len(tasks)):
        raise RiposteError("ARTIST_MASK_PREVIEW_REQUIRED")
    result.update(budget_preview_total=len(tasks), budget_preview_offset=offset)
    return tasks[offset:offset + 3]


def _budget_previews(image: Image.Image, row: Mapping[str, Any], recipe: PublishRecipe) -> list[dict[str, Any]]:
    from .quality import spatial_budget
    artist_mask = mask_for(recipe.masks, row)
    if artist_mask is None:
        return []
    previews, sizes = [], set()
    for edge in sorted(recipe.edges):
        clean = social_render(image, edge)
        if clean.size in sizes:
            continue
        sizes.add(clean.size)
        caps = spatial_budget(clean, recipe.quality, artist_mask)
        previews.append({"image_id": row["id"], "max_edge": edge, "date": row["day"],
                         **spatial_preview(clean, caps, artist_mask)})
    return previews


def _plan_rows(rows, recipe):
    if {mask.source_sha256 for mask in recipe.masks} - {row["sha256"] for row in rows}:
        raise RiposteError("ARTIST_MASK_SELECTION_MISMATCH")
    tasks, avoided = [], 0
    for row in rows:
        artist_mask = mask_for(recipe.masks, row)
        seen_edges = set()
        for edge in sorted(recipe.edges):
            effective = min(edge, max(row["width"], row["height"]))
            if effective in seen_edges:
                avoided += 1; continue
            seen_edges.add(effective)
            tasks.append({"image_id": row["id"], "date": row["day"], "max_edge": edge,
                          "source_clean_sha256": row["sha256"], "index": len(tasks),
                          **({"artist_mask_sha256": artist_mask.identity} if artist_mask else {})})
    return {"mode": "PUBLICATION_PLAN", "images": len(rows), "outputs": len(tasks),
            "duplicate_renders_avoided": avoided, "tasks": tasks, "recipe": recipe.public(),
            "master_changes": 0, "ai_protection": "UNVERIFIED", "writes": False,
            **({"budget_revision": recipe.budget_revision()} if recipe.masks else {})}


def _request(root, batch_id):
    data = _read(root, _prefix(root, batch_id) + "/request.json")
    if data.get("id") != batch_id or data.get("schema") != 1:
        raise RiposteError("PUBLICATION_RECORD_INVALID")
    if data.get("source_mode", "catalog") not in {"catalog", "snapshot"}:
        raise RiposteError("PUBLICATION_RECORD_INVALID")
    recipe = PublishRecipe.from_dict(data.get("recipe", {}))
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 600: raise RiposteError("PUBLICATION_RECORD_INVALID")
    ids = []
    for n, task in enumerate(tasks):
        _id(task.get("id")); _id(task.get("image_id")); valid_day(task.get("date"))
        if (task.get("index") != n or type(task.get("max_edge")) is not int
            or not 64 <= task["max_edge"] <= 4096
            or not re.fullmatch(r"[0-9a-f]{64}", task.get("source_clean_sha256", ""))):
            raise RiposteError("PUBLICATION_RECORD_INVALID")
        ids.append(task["id"])
        artist_mask = next((mask for mask in recipe.masks if mask.source_sha256 == task["source_clean_sha256"]), None)
        if task.get("artist_mask_sha256") != (artist_mask.identity if artist_mask else None):
            raise RiposteError("ARTIST_MASK_BINDING_CHANGED")
    if len(set(ids)) != len(ids): raise RiposteError("PUBLICATION_RECORD_INVALID")
    return data


def _models(vae_dirs, device, pipeline_dir, temporal_dir, progress=None):
    from .models import LocalEncoder, LocalInpaintProbe
    from .runtime_probe import probe_encoder, probe_inpaint, probe_temporal
    from .temporal import LocalTemporalProbe
    if not 1 <= len(vae_dirs) <= 4: raise RiposteError("NO_MODEL_NO_PROTECTION")
    encoders, probes = [], []
    for index, path in enumerate(vae_dirs):
        if progress: progress({"phase": "Loading and executing selected local encoders", "processed": index, "total": len(vae_dirs)})
        model = LocalEncoder(path, device)
        probes.append(probe_encoder(model)); encoders.append(model)
    probe = LocalInpaintProbe(pipeline_dir, encoders[0].device) if pipeline_dir else None
    if probe is not None:
        if progress: progress({"phase": "Executing selected inpainting input gradients"})
        probes.append(probe_inpaint(probe))
    temporal = LocalTemporalProbe(temporal_dir, encoders[0].device) if temporal_dir else None
    if temporal is not None:
        if progress: progress({"phase": "Executing selected temporal input gradient"})
        probes.append(probe_temporal(temporal))
    identities = {"encoders": [e.identity for e in encoders], "inpaint": getattr(probe, "identity", None),
                  "temporal": getattr(temporal, "identity", None)}
    return encoders, probe, temporal, identities, probes


def start_publication(root, image_ids, vae_dirs, recipe: PublishRecipe = PublishRecipe(),
                      device="auto", pipeline_dir=None, temporal_dir=None, progress=None, *, input_paths=None, date_mode="download", _loaded_models=None):
    with workspace_lock(root):
        sources = []
        ignored = 0
        if input_paths:
            if image_ids:
                raise RiposteError("INPUT_SELECTION_CONFLICT")
            from .intake import inspect_inputs
            from .policy import Policy
            policy = Policy(date_mode=date_mode)
            sources, ignored = inspect_inputs(input_paths, policy, progress)
            plan = _plan_rows([source.row for source in sources], recipe)
        else:
            plan = publication_plan(root, image_ids, recipe, _include_budget_previews=False)
        models = _loaded_models if _loaded_models is not None else _models(vae_dirs, device, pipeline_dir, temporal_dir, progress)
        identifier = uuid.uuid4().hex
        try:
            for source in sources:
                if progress:
                    progress({"phase": "Saving clean input snapshot"})
                data = source.snapshot(policy)
                atomic_clean_write(root, _prefix(root, identifier) + f'/inputs/{source.row["id"]}.png', data)
        except BaseException:
            # This fresh UUID has no committed request or generated outputs yet.
            # Discard only its incomplete snapshots; originals are never touched.
            incomplete = safe_child(root, _prefix(root, identifier))
            if incomplete.exists():
                shutil.rmtree(incomplete)
            raise
        request = {"id": identifier, "schema": 1, "sequence": max((x["sequence"] for x in publications(root)), default=0) + 1,
                   "source_mode": "snapshot" if sources else "catalog", "ignored_files": ignored,
                   "recipe": recipe.public(), "models": models[3], "execution_probes": models[4],
                   "tasks": [{**t, "id": uuid.uuid4().hex} for t in plan["tasks"]],
                   "duplicate_renders_avoided": plan["duplicate_renders_avoided"],
                   "ai_protection": "UNVERIFIED", "master_changes": 0}
        atomic_json_write(root, _prefix(root, identifier) + "/request.json", request)
        return _run(root, request, models, progress)


def resume_publication(root, batch_id, vae_dirs, device="auto", pipeline_dir=None, temporal_dir=None, progress=None):
    with workspace_lock(root):
        request = _request(root, batch_id)
        # Verify committed work before loading expensive models or retrying failed items.
        for task in request["tasks"]:
            row = _source_row(root, request, task)
            if row["sha256"] != task["source_clean_sha256"]: raise RiposteError("PUBLICATION_MASTER_CHANGED")
            if safe_child(root, _prefix(root, batch_id) + f'/items/{task["id"]}/report.json').is_file():
                _verified_item(root, request, task)
        models = _models(vae_dirs, device, pipeline_dir, temporal_dir, progress)
        if models[3] != request["models"]: raise RiposteError("PUBLICATION_RESUME_MODEL_MISMATCH")
        return _run(root, request, models, progress)


def _source_row(root, request, task):
    """Verify only the selected master or its private, date-only input snapshot."""
    from .records import ImageSource
    row: ImageSource
    if request.get("source_mode", "catalog") == "catalog":
        row = find_image(root, task["image_id"])
    else:
        relative = _prefix(root, request["id"]) + f'/inputs/{_id(task["image_id"])}.png'
        try:
            audit = png_audit(safe_child(root, relative).read_bytes())
        except OSError:
            raise RiposteError("PUBLICATION_INPUT_MISSING") from None
        row = {"id": task["image_id"], "relative": relative, "day": audit["date"],
               "sha256": audit["sha256"], "width": audit["width"], "height": audit["height"]}
    if row["sha256"] != task["source_clean_sha256"] or row["day"] != task["date"]:
        raise RiposteError("PUBLICATION_MASTER_CHANGED")
    return row


def _run(root, request, models, progress):
    batch_id = request["id"]
    prefix = _prefix(root, batch_id)
    recipe = PublishRecipe.from_dict(request["recipe"])
    encoders, probe, temporal = models[:3]
    try:
        for task in request["tasks"]:
            item_prefix = f'{prefix}/items/{task["id"]}'
            if safe_child(root, item_prefix + "/report.json").is_file(): continue
            if progress: progress({"phase": "Preparing publishing image", "batch_id": batch_id,
                                   "item": task["index"] + 1, "items": len(request["tasks"]), "processed": 0, "total": recipe.guard.steps * recipe.guard.restarts})
            try:
                # A stopped process can leave clean, uncommitted PNGs. Only this
                # task's uncommitted directory is disposable; never touch a report.
                orphan = safe_child(root, item_prefix)
                if orphan.exists(): shutil.rmtree(orphan)
                row = _source_row(root, request, task)
                if row["sha256"] != task["source_clean_sha256"]: raise RiposteError("PUBLICATION_MASTER_CHANGED")
                with Image.open(safe_child(root, row["relative"])) as source:
                    clean = social_render(source, task["max_edge"])
                # A new seed per task, stable across interruption/resume; no global RNG.
                config = replace(recipe.guard, seed=(recipe.guard.seed + task["index"] * 7919) % 2**32)
                artist_mask = mask_for(recipe.masks, row)
                candidate, report = protect_release(clean, encoders, config, recipe.quality,
                                                     probe=probe, temporal=temporal, progress=progress,
                                                     **({"artist_mask": artist_mask} if artist_mask else {}))
                quality = quality_report(clean, candidate, recipe.quality, artist_mask)
                if quality["status"] != "PASS" or quality["identical_pixels"]:
                    raise RiposteError("PUBLICATION_QUALITY_FAILED")
                if progress: progress({"phase": "Verifying publishing output", "processed": config.steps * config.restarts,
                                       "total": config.steps * config.restarts})
                artifacts = {}
                for name, image in (("clean", clean), ("candidate", candidate)):
                    data = encode_clean(image, row["day"])
                    artifacts[name] = png_audit(data)["sha256"]
                    atomic_clean_write(root, item_prefix + f"/{name}.png", data)
                folder = folder_for(row["day"], candidate.width, candidate.height)
                relative = (folder / f'{folder.name}{task["index"] + 1:02d}.png').as_posix()
                item = {"id": task["id"], "batch_id": batch_id, "image_id": row["id"], "date": row["day"],
                        "source_clean_sha256": row["sha256"], "max_edge": task["max_edge"],
                        "width": candidate.width, "height": candidate.height, "relative": relative,
                        "artifact_sha256": artifacts, "quality": quality, "guard": report,
                        "transport": transport_report(clean, candidate), "ai_protection": "UNVERIFIED"}
                atomic_json_write(root, item_prefix + "/report.json", item)
            except Exception as exc:
                folder = safe_child(root, item_prefix)
                if folder.exists(): shutil.rmtree(folder)
                if isinstance(exc, RiposteError) and exc.code == "JOB_CANCELLED": raise
                code = exc.code if isinstance(exc, RiposteError) and re.fullmatch(r"[A-Z0-9_]+", exc.code) else "PUBLICATION_ITEM_FAILED"
                _replace_json(root, f'{prefix}/failures/{task["id"]}.json', {"id": task["id"], "code": code})
        _replace_json(root, prefix + "/outcome.json", {"status": "FINISHED", "ai_protection": "UNVERIFIED"})
    except BaseException:
        _replace_json(root, prefix + "/outcome.json", {"status": "INTERRUPTED", "ai_protection": "UNVERIFIED"})
        raise
    return publication_status(root, batch_id)


def _verified_item(root, request, task):
    prefix = _prefix(root, request["id"]) + f'/items/{task["id"]}'
    report_path = prefix + "/report.json"
    report, report_bytes = _read_record(root, report_path)
    if any(report.get(k) != task[k] for k in ("id", "image_id", "date", "source_clean_sha256", "max_edge")) or report.get("batch_id") != request["id"]:
        raise RiposteError("PUBLICATION_ITEM_BINDING_FAILED")
    from .policy import canonical_path
    canonical_path(report.get("relative", ""))
    images, raw = {}, {}
    for kind in ("clean", "candidate"):
        try:
            data = safe_child(root, prefix + f"/{kind}.png").read_bytes()
        except OSError:
            raise RiposteError("PUBLICATION_ARTIFACT_UNREADABLE") from None
        audit = png_audit(data)
        if audit["sha256"] != report.get("artifact_sha256", {}).get(kind) or audit["date"] != task["date"]:
            raise RiposteError("PUBLICATION_ARTIFACT_CHANGED")
        with Image.open(io.BytesIO(data)) as image: images[kind] = image.copy()
        raw[kind] = data
    row = _source_row(root, request, task)
    if row["sha256"] != task["source_clean_sha256"]:
        raise RiposteError("PUBLICATION_MASTER_CHANGED")
    with Image.open(safe_child(root, row["relative"])) as master:
        expected_clean = encode_clean(social_render(master, task["max_edge"]), task["date"])
    if expected_clean != raw["clean"]:
        raise RiposteError("PUBLICATION_CLEAN_BASELINE_CHANGED")
    recipe = PublishRecipe.from_dict(request["recipe"])
    artist_mask = mask_for(recipe.masks, row)
    quality = quality_report(images["clean"], images["candidate"], recipe.quality, artist_mask)
    if report.get("quality", {}).get("spatial_budget") != quality.get("spatial_budget"):
        raise RiposteError("ARTIST_MASK_BINDING_CHANGED")
    if quality["status"] != "PASS" or quality["identical_pixels"]:
        raise RiposteError("PUBLICATION_QUALITY_FAILED")
    expected_folder = folder_for(task["date"], images["candidate"].width, images["candidate"].height)
    if report["relative"] != (expected_folder / f'{expected_folder.name}{task["index"] + 1:02d}.png').as_posix():
        raise RiposteError("PUBLICATION_FILENAME_INVALID")
    if images["candidate"].size != (report.get("width"), report.get("height")):
        raise RiposteError("PUBLICATION_DIMENSION_MISMATCH")
    report_hash = hashlib.sha256(report_bytes).hexdigest()
    return report, images, raw, report_hash


def publication_status(root, batch_id):
    request = _request(root, batch_id)
    prefix = _prefix(root, batch_id)
    records = []
    for task in request["tasks"]:
        entry = {"id": task["id"], "image_id": task["image_id"], "max_edge": task["max_edge"],
                 "date": task["date"], "status": "PENDING", "review": "PENDING"}
        report_path = f'{prefix}/items/{task["id"]}/report.json'
        review_path = f'{prefix}/reviews/{task["id"]}.json'
        decision = {}
        has_review = safe_child(root, review_path).is_file()
        if has_review:
            try:
                decision = _read(root, review_path)
            except RiposteError:
                entry['review'] = 'STALE'
        if safe_child(root, report_path).is_file() or has_review:
            try:
                item, _, _, digest = _verified_item(root, request, task)
                entry.update({k: item[k] for k in ("relative", "width", "height", "quality", "artifact_sha256", "transport")})
                entry["status"] = "READY_FOR_REVIEW"
                bound = (decision.get("candidate_sha256") == item["artifact_sha256"]["candidate"]
                         and decision.get("report_sha256") == digest)
                if has_review:
                    entry["review"] = decision.get("decision", "PENDING") if bound else "STALE"
            except (RiposteError, OSError, KeyError, TypeError, ValueError) as exc:
                entry.update(status='BLOCKED', code=exc.code if isinstance(exc, RiposteError) else 'PUBLICATION_ARTIFACT_UNREADABLE')
                if has_review:
                    entry['review'] = 'STALE'
            # Revocation is an instruction to exclude an item, independent of
            # whether the bytes that were once accepted still exist.
            if decision.get('decision') == 'REJECTED':
                entry['review'] = 'REJECTED'
        elif safe_child(root, f'{prefix}/failures/{task["id"]}.json').is_file():
            entry.update(status="BLOCKED", code=_read(root, f'{prefix}/failures/{task["id"]}.json')["code"])
        records.append(entry)
    counts = {key: sum(x["status"] == key for x in records) for key in ("PENDING", "READY_FOR_REVIEW", "BLOCKED")}
    counts["ACCEPTED"] = sum(x["review"] == "ACCEPTED" for x in records)
    outcome_path = prefix + "/outcome.json"
    outcome = _read(root, outcome_path)["status"] if safe_child(root, outcome_path).exists() else "OPEN_OR_INTERRUPTED"
    return {"mode": "PUBLICATION_BATCH", "id": batch_id, "sequence": request["sequence"], "status": outcome,
            "items": records, "counts": counts, "recipe": request["recipe"], "master_changes": 0,
            "duplicate_renders_avoided": request["duplicate_renders_avoided"], "ai_protection": "UNVERIFIED",
            "source_mode": request.get("source_mode", "catalog"), "ignored_files": request.get("ignored_files", 0)}


def publications(root):
    folder = safe_child(root, state_relative(root, "publishing"))
    if not folder.exists(): return []
    rows = []
    for child in folder.iterdir():
        if re.fullmatch(r"[0-9a-f]{32}", child.name):
            try:
                value = publication_status(root, child.name)
                rows.append({k: value[k] for k in ("id", "sequence", "status", "counts", "ai_protection")})
            except RiposteError: continue
    return sorted(rows, key=lambda row: row["sequence"], reverse=True)


def review_publication(root, batch_id, item_ids, decision="ACCEPTED", visual_accepted=False, acknowledge_unverified=False):
    if decision not in {"ACCEPTED", "REJECTED"}: raise RiposteError("REVIEW_DECISION_INVALID")
    if decision == "ACCEPTED" and (not visual_accepted or not acknowledge_unverified):
        raise RiposteError("PUBLICATION_REVIEW_ACKNOWLEDGEMENT_REQUIRED")
    if not isinstance(item_ids, (list, tuple)) or not item_ids or len(set(item_ids)) != len(item_ids):
        raise RiposteError("PUBLICATION_SELECTION_INVALID")
    with workspace_lock(root):
        request = _request(root, batch_id)
        tasks = {t["id"]: t for t in request["tasks"]}
        if any(i not in tasks for i in item_ids): raise RiposteError("PUBLICATION_ITEM_NOT_FOUND")
        if decision == 'REJECTED':
            for identifier in item_ids:
                _replace_json(root, _prefix(root, batch_id) + f"/reviews/{identifier}.json",
                              {'decision': 'REJECTED', 'ai_protection': 'UNVERIFIED'})
            return publication_status(root, batch_id)
        # Validate the full review selection before recording any acceptance.
        # Keep only receipt fields. Retaining decoded images here grows memory
        # with every selected rendition, even after that item has been verified.
        checked = []
        for identifier in item_ids:
            verified = _verified_item(root, request, tasks[identifier])
            checked.append((identifier, verified[0]["artifact_sha256"]["candidate"], verified[3]))
            del verified
        for identifier, candidate_hash, digest in checked:
            _replace_json(root, _prefix(root, batch_id) + f"/reviews/{identifier}.json",
                          {"decision": decision, "candidate_sha256": candidate_hash,
                           "report_sha256": digest, "visual_accepted": bool(visual_accepted),
                           "acknowledge_unverified": bool(acknowledge_unverified), "ai_protection": "UNVERIFIED"})
        return publication_status(root, batch_id)


def publication_pixels(root, batch_id, item_id, kind="candidate", thumb=False, view="identity"):
    if kind not in {"clean", "candidate", "difference"}: raise RiposteError("PUBLICATION_IMAGE_INVALID")
    request = _request(root, batch_id)
    task = next((t for t in request["tasks"] if t["id"] == _id(item_id)), None)
    if task is None: raise RiposteError("PUBLICATION_ITEM_NOT_FOUND")
    item, images, raw, _ = _verified_item(root, request, task)
    from .metrics import TRANSFORMS, transform
    if view not in TRANSFORMS: raise RiposteError("TRANSFORM_INVALID")
    if kind != "difference" and not thumb and view == "identity": return raw[kind]
    if view != "identity": images = {k: transform(v, view) for k, v in images.items()}
    if kind == "difference":
        from .metrics import difference_image
        image = difference_image(images["clean"], images["candidate"])
    else: image = images[kind]
    if thumb: image.thumbnail((480, 480), Image.Resampling.LANCZOS)
    return encode_clean(image, item["date"])


def publication_zip(root, batch_id):
    with workspace_lock(root):
        return _publication_zip_locked(root, batch_id)


def _publication_zip_locked(root, batch_id):
        request = _request(root, batch_id)
        entries, total_bytes = [], 0
        for task in request["tasks"]:
            review_path = _prefix(root, batch_id) + f'/reviews/{task["id"]}.json'
            if not safe_child(root, review_path).is_file(): continue
            review = _read(root, review_path)
            if review.get("decision") != "ACCEPTED": continue
            item, _, raw, report_hash = _verified_item(root, request, task)
            if (review.get("candidate_sha256") != item["artifact_sha256"]["candidate"] or review.get("report_sha256") != report_hash
                or review.get("visual_accepted") is not True or review.get("acknowledge_unverified") is not True):
                raise RiposteError("PUBLICATION_REVIEW_STALE")
            total_bytes += len(raw["candidate"])
            if total_bytes > 536_870_912:
                raise RiposteError("PUBLICATION_ZIP_LIMIT_REVIEW_SMALLER_SELECTION")
            entries.append((item, raw["candidate"]))
        if not entries: raise RiposteError("NO_APPROVED_PUBLICATION_OUTPUTS")
        if sum(len(data) for _, data in entries) > 536_870_912:
            raise RiposteError("PUBLICATION_ZIP_LIMIT_REVIEW_SMALLER_SELECTION")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            for item, data in entries:
                y, m, d = map(int, item["date"].split("-"))
                # DOS ZIP timestamps cannot encode years before 1980. PNG date remains exact.
                stamp = (y, m, d) if 1980 <= y <= 2107 else (1980, 1, 1) if y < 1980 else (2107, 12, 31)
                info = zipfile.ZipInfo(item["relative"], (*stamp, 0, 0, 0))
                info.create_system = 0; info.external_attr = 0x20; info.extra = b""; info.comment = b""
                archive.writestr(info, data)
        return buffer.getvalue()


def export_publication(root, batch_id):
    with workspace_lock(root):
        data = _publication_zip_locked(root, batch_id)
        relative = state_relative(root, f"exports/{_id(batch_id)}/RIPOSTE.zip")
        dest = safe_child(root, relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.parent / (".publish-" + uuid.uuid4().hex + ".tmp")
        try:
            with temp.open("xb") as stream: stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(temp, dest)
        finally: temp.unlink(missing_ok=True)
    return {"relative": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "contents": "APPROVED_DATE_ONLY_PNGS", "ai_protection": "UNVERIFIED"}


def open_in_workshop(root, batch_id, item_id):
    """An optional helper handoff; publish outputs don't depend on lab state."""
    from .lab import trials, _store_trial
    with workspace_lock(root):
        request = _request(root, batch_id)
        task = next((t for t in request["tasks"] if t["id"] == _id(item_id)), None)
        if task is None: raise RiposteError("PUBLICATION_ITEM_NOT_FOUND")
        item, images, _, _ = _verified_item(root, request, task)
        for trial in trials(root):
            if (trial.get("publication_batch_id") == batch_id and trial.get("publication_item_id") == item_id
                and trial.get("artifact_sha256", {}).get("candidate") == item["artifact_sha256"]["candidate"]):
                return trial
        row = _source_row(root, request, task)
        return _store_trial(root, row, images["clean"], images["candidate"],
                            {**item["guard"], "publication_batch_id": batch_id, "publication_item_id": item_id})
