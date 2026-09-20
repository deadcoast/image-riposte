"""Local precommitment and descriptive, presentation-blinded generation review.

Hashes detect drift under a trusted local operator; they are not an independent
timestamp or protection against rewriting the complete experiment history.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import re
import sys
from typing import cast
import uuid
from zipfile import ZipFile, ZipInfo

from . import __version__
from .errors import RiposteError
from .sanitize import png_audit
from .store import atomic_json_write, safe_child, state_relative, workspace_lock

ROLES = ("clean", "candidate", "control_1", "control_2", "control_3")
ENDPOINTS = {
    "task_success": "The requested edit/inpaint change is present, or the video has coherent visible motion. Judge the entire sequence.",
    "source_preserved": "The main illustration remains recognizable and its central subject is preserved throughout the output.",
    "usable": "The output has no severe visual artifacts, broken anatomy/structure or temporal instability that defeats the requested use.",
}
REVIEW_LIMIT = 1_048_576


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RiposteError("EXPERIMENT_RECORD_INVALID")
    return cast(dict[str, object], value)


def _array(value: object) -> list[object]:
    if not isinstance(value, list):
        raise RiposteError("EXPERIMENT_RECORD_INVALID")
    return cast(list[object], value)


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise RiposteError("EXPERIMENT_RECORD_INVALID")
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _prefix(root: Path, identifier: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise RiposteError("EXPERIMENT_NOT_FOUND")
    return state_relative(root, f"experiments/{identifier}")


def _read(path: Path) -> dict[str, object]:
    try:
        return _object(json.loads(path.read_bytes(), object_pairs_hook=_unique_fields))
    except (OSError, ValueError):
        raise RiposteError("EXPERIMENT_RECORD_INVALID") from None


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RiposteError("EXPERIMENT_RECORD_INVALID")
        result[key] = value
    return result


def conditioning(task: str, model: Mapping[str, object] | None = None) -> dict[str, object]:
    from .kontext import KIND, conditioning as kontext_conditioning
    if model is not None and model.get("kind") == KIND:
        if task != "edit":
            raise RiposteError("GENERATION_ARCHITECTURE_UNSUPPORTED")
        return kontext_conditioning()
    if task == "video":
        return {"mask_family": None, "prompt": None, "num_frames": 14, "decode_chunk_size": 2}
    return {"mask_family": "right" if task == "inpaint" else None,
            **({"mask_seed": "generation_seed"} if task == "inpaint" else {}),
            "prompt": "Preserve the main illustration and add a patterned background.",
            "strength": .65, "guidance_scale": 7.5}


def execution_identity() -> dict[str, object]:
    source = Path(__file__).parent
    return {"engine_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
            for name in ("experiment.py", "cohort.py", "generation.py", "kontext.py", "models.py", "views.py", "sanitize.py")},
            "runtime": {"python": sys.version.split()[0], "packages": {name: metadata.version(name)
                        for name in ("torch", "diffusers", "transformers", "numpy", "Pillow")}}}


def begin_experiment(root: Path, trial: Mapping[str, object], model: Mapping[str, object],
                     task: str, seeds: Sequence[int], views: Sequence[str], steps: int,
                     control_seeds: Sequence[int], assignment: Mapping[str, object] | None = None) -> dict[str, object]:
    """Called under the generation workspace lock, before the first model call."""
    identifier = _text(assignment["run_id"]) if assignment is not None else uuid.uuid4().hex
    optimization_views = trial.get("optimization_views")
    groups = [{"view": view, "seed": seed,
               "samples": {role: uuid.uuid4().hex for role in ROLES}}
              for view in views for seed in seeds]
    protocol: dict[str, object] = {
        "schema": "riposte-experiment-v1", "id": identifier, "trial_id": trial["id"],
        "date": trial["date"], "artifact_sha256": trial["artifact_sha256"],
        "trial_sha256": _digest(dict(trial)), "application_version": __version__,
        **execution_identity(),
        "model": dict(model), "task": task, "seeds": list(seeds), "views": list(views), "steps": steps,
        "conditioning": conditioning(task, model), "control_seeds": list(control_seeds), "groups": groups,
        "optimization_views": optimization_views,
        "model_family_holdout": "UNKNOWN_NOT_ESTABLISHED_BY_WEIGHT_HASH",
        "endpoints": ENDPOINTS,
        "analysis": {"joint_success": "task_success AND source_preserved AND usable",
                     "contrast": "mean(three control joint successes) - candidate joint success",
                     "eligibility": "Complete ratings for every planned sample; clean joint success; no reported filter flag in any arm.",
                     "missing": "Any null endpoint makes the entire review INCOMPLETE; no aggregate contrast.",
                     "unit": "One artwork. Seeds/views are repeated observations, not independent artworks.",
                     "inference": "Descriptive contrast only; no population estimate, significance test or efficacy verdict."},
        "commitment": "LOCAL_BEFORE_GENERATION_NOT_INDEPENDENT_PREREGISTRATION",
        "blinding": "Opaque sample labels in exported packet; operator can unblind using private protocol. Pixels may reveal conditions.",
    }
    if assignment is not None:
        protocol["cohort"] = dict(assignment)
    sealed: dict[str, object] = {"protocol": protocol, "sha256": _digest(protocol)}
    atomic_json_write(root, f"{_prefix(root, identifier)}/protocol.json", sealed)
    # Read back the exact receipt before spending generation work.
    if _read(safe_child(root, f"{_prefix(root, identifier)}/protocol.json")) != sealed:
        raise RiposteError("EXPERIMENT_PROTOCOL_CHANGED")
    return sealed


def finish_experiment(root: Path, sealed: Mapping[str, object], status: str) -> None:
    """Append a terminal receipt. An interrupted process leaves a visible OPEN run."""
    protocol = _object(sealed["protocol"])
    identifier = _text(protocol["id"])
    result: dict[str, object] = {"status": status, "protocol_sha256": sealed["sha256"]}
    if status == "COMPLETE":
        report = safe_child(root, state_relative(root, f"generations/{identifier}/report.json"))
        result["report_sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
    atomic_json_write(root, f"{_prefix(root, identifier)}/outcome.json", result)


def _protocol(root: Path, identifier: str) -> dict[str, object]:
    sealed = _read(safe_child(root, f"{_prefix(root, identifier)}/protocol.json"))
    protocol = _object(sealed.get("protocol"))
    if (sealed.get("sha256") != _digest(protocol) or protocol.get("id") != identifier
            or protocol.get("schema") != "riposte-experiment-v1"):
        raise RiposteError("EXPERIMENT_PROTOCOL_CHANGED")
    return sealed


def _frame(root: Path, identifier: str, relative: str, report: Mapping[str, object]) -> bytes:
    if not re.fullmatch(r"V\d{2}-S\d{2}-(clean|candidate|control_[123])/F\d{3}\.png", relative):
        raise RiposteError("EXPERIMENT_ARTIFACT_CHANGED")
    data = safe_child(root, state_relative(root, f"generations/{identifier}/{relative}")).read_bytes()
    audit = png_audit(data)
    if audit["sha256"] != _object(report["artifacts"]).get(relative) or audit["date"] != report["date"]:
        raise RiposteError("EXPERIMENT_ARTIFACT_CHANGED")
    return data


def _bound_run(root: Path, identifier: str) -> tuple[dict[str, object], dict[str, object], dict[str, list[str]]]:
    sealed = _protocol(root, identifier)
    protocol = _object(sealed["protocol"])
    outcome = _read(safe_child(root, f"{_prefix(root, identifier)}/outcome.json"))
    if outcome.get("status") != "COMPLETE":
        raise RiposteError("EXPERIMENT_NOT_COMPLETE")
    if outcome.get("protocol_sha256") != sealed["sha256"]:
        raise RiposteError("EXPERIMENT_PROTOCOL_CHANGED")
    path = safe_child(root, state_relative(root, f"generations/{identifier}/report.json"))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != outcome.get("report_sha256"):
        raise RiposteError("EXPERIMENT_REPORT_CHANGED")
    report = _object(json.loads(raw, object_pairs_hook=_unique_fields))
    from .qualification import _verified_pair
    trial, _ = _verified_pair(root, _text(protocol["trial_id"]))
    if _digest(trial) != protocol["trial_sha256"]:
        raise RiposteError("EXPERIMENT_TRIAL_CHANGED")
    if (report.get("experiment_sha256") != sealed["sha256"] or report.get("id") != identifier
            or any(report.get(key) != protocol[key] for key in ("trial_id", "date", "model", "task", "seeds", "views", "steps", "conditioning"))):
        raise RiposteError("EXPERIMENT_REPORT_CHANGED")
    planned, actual = _array(protocol["groups"]), _array(report["groups"])
    if len(planned) != len(actual):
        raise RiposteError("EXPERIMENT_GROUPS_CHANGED")
    samples: dict[str, list[str]] = {}
    seen: set[str] = set()
    for expected_value, group_value in zip(planned, actual, strict=True):
        expected, group = _object(expected_value), _object(group_value)
        if any(expected[key] != group.get(key) for key in ("view", "seed")):
            raise RiposteError("EXPERIMENT_GROUPS_CHANGED")
        roles = _object(group["roles"])
        if set(roles) != set(ROLES):
            raise RiposteError("EXPERIMENT_GROUPS_CHANGED")
        for role in ROLES:
            sample = _text(_object(expected["samples"])[role])
            frames = [_text(item) for item in _array(roles[role])]
            if (not frames or sample in samples or not re.fullmatch(r"[0-9a-f]{32}", sample)
                    or any(frame in seen for frame in frames) or len(set(frames)) != len(frames)):
                raise RiposteError("EXPERIMENT_GROUPS_CHANGED")
            for frame in frames:
                _frame(root, identifier, frame, report)
            seen.update(frames)
            samples[sample] = frames
    if seen != set(_object(report["artifacts"])):
        raise RiposteError("EXPERIMENT_ARTIFACT_CHANGED")
    return sealed, report, samples


def experiment_status(root: Path, identifier: str | None = None) -> dict[str, object]:
    """List attempts, including failed/open ones; verify exact bytes for complete runs."""
    with workspace_lock(root):
        if identifier is None:
            folder = safe_child(root, state_relative(root, "experiments"))
            entries: list[dict[str, object]] = []
            for child in sorted(folder.iterdir()) if folder.exists() else []:
                if not re.fullmatch(r"[0-9a-f]{32}", child.name):
                    continue
                try:
                    sealed = _protocol(root, child.name)
                    path = safe_child(root, f"{_prefix(root, child.name)}/outcome.json")
                    outcome = _read(path) if path.exists() else {"status": "OPEN"}
                    entries.append({"id": child.name, "trial_id": _object(sealed["protocol"])["trial_id"],
                                    "status": outcome.get("status"), "integrity": "NOT_CHECKED"})
                except RiposteError:
                    entries.append({"id": child.name, "status": "INVALID"})
            return {"experiments": entries, "ai_protection": "UNVERIFIED"}
        sealed = _protocol(root, identifier)
        path = safe_child(root, f"{_prefix(root, identifier)}/outcome.json")
        outcome = _read(path) if path.exists() else {"status": "OPEN", "protocol_sha256": sealed["sha256"]}
        if outcome.get("protocol_sha256") != sealed["sha256"]:
            raise RiposteError("EXPERIMENT_PROTOCOL_CHANGED")
        if outcome.get("status") == "COMPLETE":
            _bound_run(root, identifier)
        reviews = _reviews(root, identifier, sealed, outcome)
        return {**sealed, "outcome": outcome, "reviews": reviews, "ai_protection": "UNVERIFIED"}


def _reviews(root: Path, identifier: str, sealed: Mapping[str, object],
             outcome: Mapping[str, object]) -> list[dict[str, object]]:
    """Verify append order. Legacy unsequenced receipts retain their old scope."""
    folder = safe_child(root, f"{_prefix(root, identifier)}/reviews")
    reviews = []
    for path in sorted(folder.iterdir()) if folder.exists() else []:
        if not re.fullmatch(r"[0-9a-f]{32}\.json", path.name):
            continue
        review = _read(safe_child(root, f"{_prefix(root, identifier)}/reviews/{path.name}"))
        if (review.get("id") != path.stem or review.get("protocol_sha256") != sealed["sha256"]
                or review.get("report_sha256") != outcome.get("report_sha256")
                or review.get("sha256") != _digest({k: v for k, v in review.items() if k != "sha256"})):
            raise RiposteError("EXPERIMENT_REVIEW_CHANGED")
        reviews.append(review)
    legacy = [row for row in reviews if "sequence" not in row]
    numbered = [row for row in reviews if "sequence" in row]
    if any(type(row["sequence"]) is not int for row in numbered):
        raise RiposteError("EXPERIMENT_REVIEW_CHANGED")
    numbered.sort(key=lambda row: cast(int, row["sequence"]))
    if [row["sequence"] for row in numbered] != list(range(len(legacy) + 1, len(reviews) + 1)):
        raise RiposteError("EXPERIMENT_REVIEW_CHANGED")
    return legacy + numbered


def review_packet(root: Path, identifier: str) -> dict[str, object]:
    """Explicit local export; packet excludes role labels, seeds and model identities."""
    with workspace_lock(root):
        sealed, report, samples = _bound_run(root, identifier)
        protocol = _object(sealed["protocol"])
        relative = f"{_prefix(root, identifier)}/review-packet.zip"
        dest = safe_child(root, relative)
        if dest.exists():
            raise RiposteError("DESTINATION_EXISTS")
        temp = safe_child(root, f"{_prefix(root, identifier)}/.packet-{uuid.uuid4().hex}.tmp")
        template = {"protocol_sha256": sealed["sha256"],
                    "ratings": {sample: dict.fromkeys(ENDPOINTS) for sample in sorted(samples)}}
        try:
            with temp.open("xb") as stream:
                with ZipFile(stream, "w") as archive:
                    def put(name: str, data: bytes) -> None:
                        info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                        info.create_system = 0
                        info.external_attr = 0x20
                        archive.writestr(info, data)
                    put("ratings.json", json.dumps(template, indent=2).encode())
                    put("instructions.json", json.dumps({"task": protocol["task"], "conditioning": protocol["conditioning"],
                        "endpoints": protocol["endpoints"], "instructions": "Compare every full sequence to reference.png. Set every endpoint to true or false; leave null if uncertain. Do not infer task success from pixel differences. Labels conceal conditions, but pixels may reveal them."}, indent=2).encode())
                    reference = safe_child(root, state_relative(root, f"lab/{_text(protocol['trial_id'])}/clean.png")).read_bytes()
                    if png_audit(reference)["sha256"] != _object(protocol["artifact_sha256"])["clean"]:
                        raise RiposteError("EXPERIMENT_TRIAL_CHANGED")
                    put("reference.png", reference)
                    for sample in sorted(samples):
                        for index, frame in enumerate(samples[sample]):
                            put(f"samples/{sample}/F{index:03d}.png", _frame(root, identifier, frame, report))
                stream.flush()
                os.fsync(stream.fileno())
            safe_child(root, relative)
            try:
                os.link(temp, dest)
            except FileExistsError:
                raise RiposteError("DESTINATION_EXISTS") from None
        finally:
            temp.unlink(missing_ok=True)
        with dest.open("rb") as reader:
            digest = hashlib.file_digest(reader, "sha256").hexdigest()
        return {"relative": relative, "sha256": digest, "samples": len(samples),
                "protocol_sha256": sealed["sha256"], "blinding": "PRESENTATION_ONLY", "ai_protection": "UNVERIFIED"}


def _analyze(protocol: Mapping[str, object], report: Mapping[str, object],
             ratings: Mapping[str, dict[str, object]]) -> dict[str, object]:
    incomplete = any(value is None for row in ratings.values() for value in row.values())
    eligible = filtered = clean_failed = unreported = 0
    numerator = 0
    for planned_value, group_value in zip(_array(protocol["groups"]), _array(report["groups"]), strict=True):
        planned, group = _object(planned_value), _object(group_value)
        samples, flags = _object(planned["samples"]), _object(group["pipeline_flags"])
        if any(_object(flags[role]).get("content_filter_reported") is not True for role in ROLES):
            unreported += 1
        if any(any(value is True for value in _array(_object(flags[role]).get("content_filter_flags") or [])) for role in ROLES):
            filtered += 1
            continue
        joint = {role: all(value is True for value in ratings[_text(samples[role])].values()) for role in ROLES}
        if any(value is None for role in ROLES for value in ratings[_text(samples[role])].values()):
            continue
        if not joint["clean"]:
            clean_failed += 1
            continue
        eligible += 1
        numerator += sum(int(joint[role]) for role in ROLES[2:]) - 3 * int(joint["candidate"])
    denominator = 3 * eligible
    return {"status": "INCOMPLETE" if incomplete else "DESCRIPTIVE" if eligible else "INCONCLUSIVE",
            "planned_groups": len(_array(protocol["groups"])), "eligible_groups": eligible,
            "filtered_groups": filtered, "clean_failed_groups": clean_failed,
            "filter_unreported_groups": unreported,
            "contrast": {"numerator": numerator, "denominator": denominator, "value": numerator / denominator}
                        if denominator and not incomplete else None,
            "independent_artworks": 1, "ai_protection": "UNVERIFIED"}


def record_review(root: Path, identifier: str, ratings_path: Path) -> dict[str, object]:
    """Append validated endpoint decisions; never overwrite a prior review."""
    with workspace_lock(root):
        sealed, report, samples = _bound_run(root, identifier)
        try:
            with ratings_path.open("rb") as stream:
                raw = stream.read(REVIEW_LIMIT + 1)
            if len(raw) > REVIEW_LIMIT:
                raise RiposteError("EXPERIMENT_RATINGS_INVALID")
            submitted = _object(json.loads(raw, object_pairs_hook=_unique_fields))
        except (OSError, ValueError):
            raise RiposteError("EXPERIMENT_RATINGS_INVALID") from None
        if set(submitted) != {"protocol_sha256", "ratings"} or submitted["protocol_sha256"] != sealed["sha256"]:
            raise RiposteError("EXPERIMENT_RATINGS_INVALID")
        values = _object(submitted["ratings"])
        if set(values) != set(samples):
            raise RiposteError("EXPERIMENT_RATINGS_INVALID")
        ratings = {key: _object(value) for key, value in values.items()}
        if any(set(row) != set(ENDPOINTS) or any(value is not None and type(value) is not bool for value in row.values())
               for row in ratings.values()):
            raise RiposteError("EXPERIMENT_RATINGS_INVALID")
        outcome = _read(safe_child(root, f"{_prefix(root, identifier)}/outcome.json"))
        prior = _reviews(root, identifier, sealed, outcome)
        result: dict[str, object] = {"id": uuid.uuid4().hex, "protocol_sha256": sealed["sha256"],
            "sequence": len(prior) + 1,
            "report_sha256": outcome["report_sha256"], "ratings": ratings,
            "analysis": _analyze(_object(sealed["protocol"]), report, ratings),
            "reviewer_independence": "NOT_ESTABLISHED"}
        result["sha256"] = _digest(result)
        atomic_json_write(root, f"{_prefix(root, identifier)}/reviews/{result['id']}.json", result)
        return result
