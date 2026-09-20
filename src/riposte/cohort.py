"""Prospective local artwork cohorts with exact finite-sample missingness bounds.

These bounds are not confidence intervals. Distinct rasters and local random
selection do not establish statistical independence or held-out model families.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction
import hashlib
from pathlib import Path
import random
import re
import secrets
import uuid

from .errors import RiposteError
from .experiment import (ENDPOINTS, _array, _bound_run, _digest, _object, _prefix as _experiment_prefix,
                         _protocol as _experiment_protocol, _read, _reviews, _text,
                         begin_experiment, conditioning, execution_identity, finish_experiment)
from .qualification import CONTROL_SEEDS, _verified_pair
from .records import Progress
from .store import atomic_json_write, safe_child, state_relative, workspace_lock


def _prefix(root: Path, identifier: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise RiposteError("COHORT_NOT_FOUND")
    return state_relative(root, f"cohorts/{identifier}")


def _integer(value: object) -> int:
    if type(value) is not int:
        raise RiposteError("COHORT_RECORD_INVALID")
    return value


def _fraction(value: Fraction) -> dict[str, object]:
    return {"numerator": value.numerator, "denominator": value.denominator, "value": float(value)}


def bounded_mean(values: Sequence[Fraction | None]) -> dict[str, object]:
    """Sharp selected-sample bounds under only -1 <= each unknown score <= 1."""
    if not values or any(value is not None and not -1 <= value <= 1 for value in values):
        raise RiposteError("COHORT_SCORE_INVALID")
    observed = [value for value in values if value is not None]
    total = sum(observed, Fraction(0))
    missing = len(values) - len(observed)
    return {"selected_artworks": len(values), "scored_artworks": len(observed), "unscored_artworks": missing,
            "mean": _fraction(total / len(values)) if not missing else None,
            "bounds": {"lower": _fraction((total - missing) / len(values)),
                       "upper": _fraction((total + missing) / len(values)),
                       "kind": "FINITE_SAMPLE_MISSINGNESS_NOT_CONFIDENCE_INTERVAL"},
            "ai_protection": "UNVERIFIED"}


def _pool(root: Path, trial_ids: Sequence[str], progress: Progress | None = None) -> list[dict[str, object]]:
    from .generation import generation_report
    from .lab import trial_report
    # One scan for prior outcomes, not a full run-directory scan for each trial.
    folder = safe_child(root, state_relative(root, "generations"))
    generated: set[str] = set()
    generated_images: set[str] = set()
    for child in folder.iterdir() if folder.exists() else []:
        if re.fullmatch(r"[0-9a-f]{32}", child.name):
            if not safe_child(root, state_relative(root, f"generations/{child.name}/report.json")).exists():
                continue
            try:
                trial_id = _text(generation_report(root, child.name)["trial_id"])
                generated.add(trial_id)
                generated_images.add(_text(trial_report(root, trial_id)["image_id"]))
            except RiposteError:
                raise RiposteError("COHORT_PRIOR_GENERATION_INVALID") from None
    entries: list[dict[str, object]] = []
    fingerprints: set[str] = set()
    image_ids: set[str] = set()
    for index, identifier in enumerate(sorted(trial_ids)):
        if progress:
            progress({"phase": "Verifying cohort sampling pool", "processed": index, "total": len(trial_ids)})
        trial, pair = _verified_pair(root, identifier)
        # Canonical pixel identity excludes PNG metadata/date and candidate changes.
        clean = pair["clean"].convert("RGB")
        digest = hashlib.sha256(f"RGB:{clean.width}:{clean.height}:".encode() + clean.tobytes()).hexdigest()
        if digest in fingerprints:
            raise RiposteError("COHORT_DUPLICATE_CLEAN_RASTER")
        fingerprints.add(digest)
        image_id = _text(trial["image_id"])
        if image_id in image_ids:
            raise RiposteError("COHORT_DUPLICATE_SOURCE_IMAGE")
        image_ids.add(image_id)
        if identifier in generated or image_id in generated_images:
            raise RiposteError("COHORT_TRIAL_ALREADY_GENERATED")
        entries.append({"trial_id": identifier, "image_id": image_id,
                        "trial_sha256": _digest(trial), "clean_pixels_sha256": digest})
    return entries


def cohort_challenge(root: Path, trial_ids: Sequence[str], model_dir: Path, sample_size: int,
                     task: str = "edit", seeds: tuple[int, ...] = (7, 19),
                     views: tuple[str, ...] = ("identity", "jpeg70"), steps: int = 25,
                     progress: Progress | None = None) -> dict[str, object]:
    """One explicit execution, one model load, one planned attempt per drawn artwork."""
    from .generation import LocalGenerator, _execute, _validate
    _validate(task, seeds, views, steps)
    if (type(sample_size) is not int or not 1 <= sample_size <= len(trial_ids)
            or len(set(trial_ids)) != len(trial_ids)):
        raise RiposteError("COHORT_PARAMETERS_INVALID")
    with workspace_lock(root):
        from .organizer import audit_workspace
        if audit_workspace(root)["checkpoint"] != "COMPLETE":
            raise RiposteError("ORGANIZATION_CHECKPOINT_REQUIRED")
        population = _pool(root, trial_ids, progress)
        if progress:
            progress({"phase": "Loading the selected cohort baseline", "processed": 0, "total": sample_size})
        generator = LocalGenerator(model_dir, task)
        # Canonical pool order makes the recorded draw replayable within this runtime.
        selection_seed = secrets.randbits(128)
        selected = random.Random(selection_seed).sample(population, sample_size)
        members = [{**row, "run_id": uuid.uuid4().hex} for row in selected]
        identifier = uuid.uuid4().hex
        protocol: dict[str, object] = {
            "schema": "riposte-cohort-v1", "id": identifier, "population": population, "members": members,
            "selection": {"kind": "LOCAL_RANDOM_WITHOUT_REPLACEMENT", "seed": selection_seed,
                          "scope": "Explicit pool only; near duplicates, independent authorship and prior external outcomes are not detectable."},
            "task": task, "model": generator.identity, "seeds": list(seeds), "views": list(views), "steps": steps,
            "control_seeds": list(CONTROL_SEEDS), "conditioning": conditioning(task, generator.identity), "endpoints": ENDPOINTS,
            **execution_identity(),
            "analysis": {"primary_review": "FIRST_COMPLETE_REVIEW_BY_APPEND_SEQUENCE",
                         "artwork_score": "Sum eligible paired control-minus-candidate differences divided by ALL planned groups; filtered/clean-failed groups contribute zero, with counts retained.",
                         "cohort_score": "Equal mean across selected artworks, not pooled eligible groups.",
                         "missing": "Unattempted, failed, unreviewed or incomplete members remain unknown in [-1,1]; never drop or replace them.",
                         "retries": "One planned attempt per member; a new command creates a separate cohort.",
                         "inference": "Finite selected-sample descriptive bounds, not confidence intervals or population efficacy."},
            "family_holdout": "UNKNOWN_NOT_ESTABLISHED_BY_WEIGHT_HASH",
            "commitment": "LOCAL_BEFORE_GENERATION_NOT_INDEPENDENT_PREREGISTRATION",
        }
        sealed: dict[str, object] = {"protocol": protocol, "sha256": _digest(protocol)}
        prefix = _prefix(root, identifier)
        atomic_json_write(root, f"{prefix}/protocol.json", sealed)
        if _read(safe_child(root, f"{prefix}/protocol.json")) != sealed:
            raise RiposteError("COHORT_PROTOCOL_CHANGED")
        try:
            for index, member in enumerate(members):
                if progress:
                    progress({"phase": "Generating committed cohort member", "item": index + 1, "items": sample_size})
                trial, pair = _verified_pair(root, _text(member["trial_id"]))
                if _digest(trial) != member["trial_sha256"]:
                    raise RiposteError("COHORT_TRIAL_CHANGED")
                assignment = {"id": identifier, "sha256": sealed["sha256"], "run_id": member["run_id"]}
                experiment = begin_experiment(root, trial, generator.identity, task, seeds, views, steps, CONTROL_SEEDS, assignment)
                try:
                    _execute(root, trial, pair, generator, task, seeds, views, steps, progress, experiment, sequence=1)
                except BaseException as exc:
                    finish_experiment(root, experiment, _failure_status(exc))
                    raise
                finish_experiment(root, experiment, "COMPLETE")
        except BaseException as exc:
            atomic_json_write(root, f"{prefix}/outcome.json", {"protocol_sha256": sealed["sha256"], "status": _failure_status(exc)})
            raise
        atomic_json_write(root, f"{prefix}/outcome.json", {"protocol_sha256": sealed["sha256"], "status": "COMPLETE"})
        return _status(root, identifier)


def _failure_status(exc: BaseException) -> str:
    cancelled = isinstance(exc, (KeyboardInterrupt, SystemExit)) or isinstance(exc, RiposteError) and exc.code == "JOB_CANCELLED"
    return "CANCELLED" if cancelled else "FAILED"


def _protocol(root: Path, identifier: str) -> dict[str, object]:
    sealed = _read(safe_child(root, f"{_prefix(root, identifier)}/protocol.json"))
    protocol = _object(sealed.get("protocol"))
    if (protocol.get("id") != identifier or protocol.get("schema") != "riposte-cohort-v1"
            or _digest(protocol) != sealed.get("sha256")):
        raise RiposteError("COHORT_PROTOCOL_CHANGED")
    return sealed


def _member(root: Path, member: Mapping[str, object], cohort: Mapping[str, object]) -> tuple[dict[str, object], Fraction | None]:
    protocol = _object(cohort["protocol"])
    identifier = _text(member["run_id"])
    prefix = _experiment_prefix(root, identifier)
    row: dict[str, object] = {"trial_id": member["trial_id"], "run_id": identifier, "status": "UNATTEMPTED", "score": None}
    if not safe_child(root, f"{prefix}/protocol.json").exists():
        return row, None
    sealed = _experiment_protocol(root, identifier)
    experiment = _object(sealed["protocol"])
    if (experiment.get("cohort") != {"id": protocol["id"], "sha256": cohort["sha256"], "run_id": identifier}
            or experiment.get("trial_id") != member["trial_id"] or experiment.get("trial_sha256") != member["trial_sha256"]
            or any(experiment.get(key) != protocol[key] for key in ("model", "task", "seeds", "views", "steps", "conditioning", "endpoints", "engine_sha256", "runtime"))):
        raise RiposteError("COHORT_MEMBER_CHANGED")
    path = safe_child(root, f"{prefix}/outcome.json")
    outcome = _read(path) if path.exists() else {"status": "OPEN", "protocol_sha256": sealed["sha256"]}
    if outcome.get("protocol_sha256") != sealed["sha256"]:
        raise RiposteError("COHORT_MEMBER_CHANGED")
    row["status"] = outcome.get("status")
    if row["status"] != "COMPLETE":
        return row, None
    _bound_run(root, identifier)
    reviews = _reviews(root, identifier, sealed, outcome)
    if any("sequence" not in review for review in reviews):
        raise RiposteError("COHORT_REVIEW_ORDER_UNKNOWN")
    primary = next((review for review in reviews if _object(review["analysis"])["status"] != "INCOMPLETE"), None)
    row["review_count"] = len(reviews)
    if primary is None:
        row["review_status"] = "INCOMPLETE" if reviews else "UNREVIEWED"
        return row, None
    analysis = _object(primary["analysis"])
    contrast = analysis["contrast"]
    numerator = _integer(_object(contrast)["numerator"]) if contrast is not None else 0
    score = Fraction(numerator, 3 * _integer(analysis["planned_groups"]))
    row.update({"primary_review_id": primary["id"], "primary_review_sequence": primary["sequence"],
                "review_status": analysis["status"], "analysis": analysis, "score": _fraction(score)})
    return row, score


def _status(root: Path, identifier: str) -> dict[str, object]:
    sealed = _protocol(root, identifier)
    protocol = _object(sealed["protocol"])
    path = safe_child(root, f"{_prefix(root, identifier)}/outcome.json")
    outcome = _read(path) if path.exists() else {"status": "OPEN", "protocol_sha256": sealed["sha256"]}
    if outcome.get("protocol_sha256") != sealed["sha256"]:
        raise RiposteError("COHORT_PROTOCOL_CHANGED")
    results = [_member(root, _object(member), sealed) for member in _array(protocol["members"])]
    if outcome["status"] == "COMPLETE" and any(row["status"] != "COMPLETE" for row, _ in results):
        raise RiposteError("COHORT_MEMBER_CHANGED")
    summary = bounded_mean([value for _, value in results])
    return {**sealed, "outcome": outcome, "members": [row for row, _ in results], "summary": summary,
            "ai_protection": "UNVERIFIED"}


def cohort_status(root: Path, identifier: str | None = None) -> dict[str, object]:
    with workspace_lock(root):
        if identifier is not None:
            return _status(root, identifier)
        folder = safe_child(root, state_relative(root, "cohorts"))
        cohorts: list[dict[str, object]] = []
        for child in sorted(folder.iterdir()) if folder.exists() else []:
            if not re.fullmatch(r"[0-9a-f]{32}", child.name):
                continue
            try:
                sealed = _protocol(root, child.name)
                cohorts.append({"id": child.name, "sha256": sealed["sha256"], "integrity": "PROTOCOL_ONLY"})
            except RiposteError:
                cohorts.append({"id": child.name, "integrity": "INVALID"})
        return {"cohorts": cohorts, "ai_protection": "UNVERIFIED"}
