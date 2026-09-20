"""One operation boundary shared by typed commands and the interactive terminal.

No shell strings are executed. Model/root paths live only in the caller's session.
The existing backend retains authority over sanitation, locks and image approvals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TYPE_CHECKING, cast
import io
import os
import re
import subprocess
import sys

from ..errors import RiposteError
from ..policy import Policy, MONTHS, BINS, YEARS
from ..records import CatalogRow, ImageInfo, ListOptions, PreviewSortOptions, Progress, RequestValues, SelectionFilters, SortOptions

if TYPE_CHECKING:
    from ..publication import PublishRecipe


@dataclass(frozen=True)
class Request:
    name: str
    root: Path | None = None
    values: RequestValues = field(default_factory=RequestValues)


# These are application effects, not a permission system for hostile local code.
EFFECTS = {
    "recipes": "INSPECT", "recipes-save": "SAVE_PUBLISHING_RECIPE",
    "duplicates": "INSPECT",
    "categories": "INSPECT",
    "category-rules": "INSPECT", "category-rules-save": "SAVE_CATEGORY_RULES",
    "riposte": "CREATE_CANDIDATES", "riposte-plan": "INSPECT",
    "sort-riposte-plan": "INSPECT", "sort-riposte": "REPLACE_SOURCES",
    "organize": "INSPECT", "apply": "REPLACE_SOURCES", "audit": "INSPECT",
    "undo-sort": "INSPECT", "undo-sort-apply": "RESTORE_SOURCES",
    "list": "INSPECT", "inspect": "INSPECT", "publish": "CREATE_CANDIDATES",
    "plan": "INSPECT", "publications": "INSPECT", "resume": "CREATE_CANDIDATES",
    "review": "RECORD_REVIEW", "package": "WRITE_APPROVED_PACK", "doctor": "INSPECT",
    "upgrade": "RENAME_APP_STATE", "guard": "CREATE_TRIAL", "compare": "CREATE_TRIAL",
    "qualify": "WRITE_EVALUATION", "challenge": "WRITE_GENERATIONS",
    "experiment": "INSPECT", "experiment-packet": "WRITE_REVIEW_PACKET", "experiment-review": "RECORD_REVIEW",
    "cohort": "INSPECT", "cohort-challenge": "WRITE_GENERATIONS",
    "panel": "INSPECT", "panel-create": "COMMIT_REVIEW_PANEL",
    "panel-packet": "WRITE_REVIEW_PACKET", "panel-review": "RECORD_REVIEW",
    "benchmark": "WRITE_GENERATIONS", "export": "WRITE_UNREVIEWED_EXPORT",
    "trials": "INSPECT", "evaluations": "INSPECT", "generations": "INSPECT",
    "generation": "INSPECT", "frame": "INSPECT", "handoff": "CREATE_EXACT_TRIAL", "image": "INSPECT", "open-image": "OPEN_LOCAL_VIEWER",
}
CANCELLABLE = frozenset({"duplicates", "cohort-challenge", "categories", "category-rules", "organize", "audit", "list", "inspect", "plan", "publish", "resume",
                         "guard", "qualify", "challenge", "doctor", "sort-riposte-plan", "riposte", "riposte-plan"})


def root_of(request: Request) -> Path:
    if request.root is None:
        raise RiposteError("WORKSPACE_REQUIRED")
    if request.name == "duplicates":
        from ..duplicates import scan_root
        return scan_root(Path(request.root))
    from ..store import check_root
    return check_root(Path(request.root).expanduser().absolute())


def parse_month(value: str | int | None) -> str | None:
    if value in (None, "", "all", "ALL"):
        return None
    word = str(value)
    if word.isdigit() and 1 <= int(word) <= 12:
        return MONTHS[int(word) - 1]
    matches = [m for m in MONTHS if m.lower() == word.lower() or m[:3].lower() == word.lower()]
    if len(matches) == 1:
        return matches[0]
    raise RiposteError("MONTH_FILTER_INVALID")


def select_rows(root: Path, *, year: str | None = None, month: str | int | None = None,
                size: str | None = None, search: str = "", limit: int | None = None,
                offset: int = 0) -> list[CatalogRow]:
    from ..store import catalog
    if year not in (None, "", "all", "EVERYTHING_ELSE") and (not isinstance(year, str) or not re.fullmatch(r"[0-9]{4}", year) or year == "0000"):
        raise RiposteError("YEAR_FILTER_INVALID")
    if size not in (None, "", "all", *BINS):
        raise RiposteError("SIZE_FILTER_INVALID")
    if type(offset) is not int or offset < 0 or (limit is not None and (type(limit) is not int or limit < 1)):
        raise RiposteError("PAGINATION_INVALID")
    month = parse_month(month)
    rows = catalog(root)
    filtered = []
    for row in rows:
        parts = row["relative"].split("/")
        if year not in (None, "", "all") and parts[0] != year: continue
        if month is not None and parts[1] != month: continue
        if size not in (None, "", "all") and parts[-2] != size: continue
        if search and search.lower() not in (row["relative"] + " " + row["id"] + " " + row["day"]).lower(): continue
        filtered.append(row)
    return filtered[offset:] if limit is None else filtered[offset:offset + limit]


def recipe(values: RequestValues) -> PublishRecipe:
    from ..publication import PublishRecipe
    from ..quality import QualityLimits
    from ..release_guard import ReleaseConfig
    return PublishRecipe(tuple(values.get("edges") or (1536,)),
                         ReleaseConfig(steps=values.get("steps", 24), restarts=values.get("restarts", 2),
                                       seed=values.get("seed", 7)),
                         QualityLimits(epsilon_255=values.get("epsilon", 4),
                                       preserve_white=values.get("preserve_white", True),
                                       delta_e76_p95=values.get("delta_e76_p95", 6.0),
                                       rms_fraction=values.get("rms_fraction", .95)))


def resolved_recipe(root: Path, values: RequestValues) -> PublishRecipe:
    from ..recipes import SETTINGS, resolve_recipe
    keys = values.get("recipe_overrides", tuple(SETTINGS))
    if any(key not in SETTINGS for key in keys):
        raise RiposteError("RECIPE_SETTINGS_INVALID")
    data: dict[str, object] = dict(values)
    return resolve_recipe(root, values.get("recipe_name"), revision=values.get("recipe_revision"),
                          overrides={key: data[key] for key in keys if key in data})


def image_selection(root: Path, values: RequestValues) -> list[str]:
    ids = list(values.get("image_ids") or [])
    all_images = values.get("all_images", False)
    if bool(ids) == bool(all_images):
        raise RiposteError("SELECT_IMAGES_OR_ALL")
    filters: SelectionFilters = {"year": values.get("year"), "month": values.get("month"), "size": values.get("size")}
    if ids and any(v not in (None, "", "all") for v in filters.values()):
        raise RiposteError("FILTERS_REQUIRE_ALL_SELECTION")
    return [r["id"] for r in select_rows(root, **filters)] if all_images else ids


def _paths(values: RequestValues) -> list[Path]:
    paths = values.get("vae_dirs", [])
    if len(paths) > 4: raise RiposteError("TOO_MANY_LOCAL_ENCODERS")
    return [Path(p).expanduser().absolute() for p in paths]


def _optional(values: RequestValues, key: Literal["inpaint", "video"]) -> Path | None:
    value = values.get(key)
    return Path(value).expanduser().absolute() if value else None


def execute(request: Request, progress: Progress | None = None) -> Any:
    """Invoke an allowlisted operation. All returned data is existing clean state."""
    name, v = request.name, request.values
    if name not in EFFECTS:
        raise RiposteError("COMMAND_NOT_AVAILABLE")
    if name == "doctor":
        from ..models import runtime_capabilities, inspect_vae
        if v.get("execute"):
            from ..runtime_probe import execute_local_probe
            if not v.get("vae_dirs"): raise RiposteError("LOCAL_VAE_DIRECTORY_REQUIRED")
            return execute_local_probe(_paths(v), device=v.get("device", "auto"), progress=progress)
        result: dict[str, object] = {"runtime": runtime_capabilities()}
        if v.get("vae_dirs"):
            entries = [inspect_vae(p) for p in _paths(v)]
            result["model" if len(entries) == 1 else "models"] = entries[0] if len(entries) == 1 else entries
        return result
    root = root_of(request)
    if name in {"recipes", "recipes-save"}:
        from ..recipes import inspect_recipes, save_recipe
        if name == "recipes-save":
            if not v.get("recipe_name") or v.get("recipe_settings") is None:
                raise RiposteError("RECIPE_NAME_REQUIRED")
            return save_recipe(root, cast(str, v["recipe_name"]), cast(dict[str, object], v["recipe_settings"]),
                               expected_revision=v.get("expected_revision") or "")
        return inspect_recipes(root, v.get("recipe_name"), settings=v.get("recipe_settings"))
    if name == "duplicates":
        from ..duplicates import ScanOptions, scan_duplicates
        from ..duplicate_review import DuplicateReview
        duplicate_options = ScanOptions(visual=v.get("visual", True), videos=v.get("videos", True),
                              include_float=v.get("include_float", True), max_files=v.get("max_files", 100_000),
                              max_visual=v.get("max_visual", 10_000), max_pairs=v.get("max_pairs", 100_000),
                              max_findings=v.get("max_findings", 20_000), max_file_bytes=v.get("max_file_bytes", 4 * 1024**3))
        report = scan_duplicates(root, duplicate_options, progress=progress)
        if v.get("duplicate_report"):
            report["export"] = DuplicateReview(report).export(Path(cast(str | Path, v["duplicate_report"])))
        return report
    if name in {"category-rules", "category-rules-save"}:
        from ..category_rules import category_rules
        return category_rules(root, categories=v.get("category_specs") or (),
                              exclusions=v.get("exclusions") or (), priorities=v.get("priorities") or (),
                              slugs=v.get("slugs") or (), clear=v.get("clear", False),
                              save=name == "category-rules-save", expected_revision=v.get("expected_revision"),
                              review=v.get("review", False), progress=progress)
    if name == "categories":
        from ..title_categories import discover_categories, DEFAULT_FILLERS
        fillers = v.get("fillers", DEFAULT_FILLERS)
        if isinstance(fillers, str): fillers = tuple(word.strip() for word in fillers.split(",") if word.strip())
        return discover_categories(root, min_count=v.get("min_count", 2), max_words=v.get("max_words", 3),
                                   limit=cast(int, v.get("limit", 100)), fillers=fillers,
                                   ignore=v.get("ignore") or (), categories=v.get("category_specs") or (), progress=progress)
    if name in {"undo-sort", "undo-sort-apply"}:
        from ..sort_history import undo_sort
        return undo_sort(root, apply=name == "undo-sort-apply", sort_id=v.get("sort_id"))
    if name in {"organize", "apply"}:
        from ..organizer import plan, organize
        options: SortOptions = {"categories": v.get("categories", False), "assignments": v.get("assignments") or ()} if v.get("categories") or v.get("assignments") else {}
        if name == "apply" and v.get("plan_id") is not None: options["plan_id"] = v["plan_id"]
        policy = Policy(date_mode=v.get("date_mode", "download"), discard_sidecars=v.get("discard_sidecars", False))
        if name == "apply":
            return organize(root, policy, progress, **options)
        return plan(root, policy, progress, **cast(PreviewSortOptions, options))
    if name == "audit":
        from ..organizer import audit_workspace
        return audit_workspace(root)
    if name == "list":
        return select_rows(root, **cast(ListOptions, {k: v[k] for k in ("year", "month", "size", "search", "limit", "offset") if k in v}))
    if name == "inspect":
        from ..store import find_image, safe_child
        from ..sanitize import png_audit
        row = find_image(root, v["image_id"])
        audit = png_audit(safe_child(root, row["relative"]).read_bytes())
        if audit["sha256"] != row["sha256"]: raise RiposteError("CATALOG_FILE_CHANGED")
        return {"mode": "CLEAN_IMAGE", **row, "audit": audit, "metadata_policy": "DATE_ONLY"}
    if name in {"sort-riposte", "sort-riposte-plan"}:
        from ..organizer import plan, organize
        from ..publication import _models, publication_plan, start_publication
        from ..sort_plan import receipt
        if v.get("input_paths"):
            raise RiposteError("SORT_USES_WORKSPACE_ROOT")
        # Validate selection before replacement; new IDs are resolved only for
        # reviewed image destinations after sorting.
        selected = image_selection(root, v)
        configuration = resolved_recipe(root, v)
        if not v.get("all_images"):
            publication_plan(root, selected, configuration)
        policy = Policy(date_mode=v.get("date_mode", "download"), discard_sidecars=v.get("discard_sidecars", False))
        options = {"categories": v.get("categories", False), "assignments": v.get("assignments") or ()} if v.get("categories") or v.get("assignments") else {}
        sorting = plan(root, policy, progress, **cast(PreviewSortOptions, options))
        filters: SelectionFilters = {"year": v.get("year"), "month": v.get("month"), "size": v.get("size")}
        plan_id = receipt({"version": "riposte-combined-sort-1", "sorting": sorting["plan_id"],
                           "all_images": v.get("all_images", False), "selected": sorted(selected),
                           "filters": filters, "recipe": configuration.public(),
                           "models": [str(path) for path in _paths(v)], "device": v.get("device", "auto"),
                           "inpaint": str(_optional(v, "inpaint") or ""), "video": str(_optional(v, "video") or "")})
        if name == "sort-riposte-plan":
            return {"mode": "SORT_RIPOSTE_PLAN", "sorting": sorting, "plan_id": plan_id, "ready": sorting["ready"],
                    "selection": "ALL_MATCHING_AFTER_SORT" if v.get("all_images") else "SELECTED_CATALOG_IMAGES",
                    "recipe": configuration.public(), "writes": False, "requires": "EXPLICIT_REPLACE_CONSENT"}
        if not v.get("plan_id"):
            raise RiposteError("SORT_PREVIEW_REQUIRED")
        if v["plan_id"] != plan_id:
            raise RiposteError("SORT_PREVIEW_CHANGED")
        if not sorting["ready"]:
            return {"mode": "SORT_RIPOSTE_RESULT", "checkpoint": "INCOMPLETE", "sorting": sorting, "protection": "NOT_STARTED"}
        # Execute all chosen model probes before replacing any source. Keep the
        # loaded models for the following publication instead of loading twice.
        loaded = _models(_paths(v), v.get("device", "auto"), _optional(v, "inpaint"), _optional(v, "video"), progress)
        destinations = {item["destination"]: item["expected"]["sha256"] for item in sorting["files"]
                        if item["kind"] == "IMAGE" and item.get("action") in {"KEEP", "SORT"}}
        options["plan_id"] = sorting["plan_id"]
        sorting = organize(root, policy, progress, **options)
        if sorting["checkpoint"] != "COMPLETE":
            return {"mode": "SORT_RIPOSTE_RESULT", "checkpoint": "INCOMPLETE", "sorting": sorting, "protection": "NOT_STARTED"}
        try:
            current = {row["relative"]: row for row in select_rows(root)}
            if any(relative not in current or current[relative]["sha256"] != digest for relative, digest in destinations.items()):
                raise RiposteError("SORT_PREVIEW_CHANGED")
            # Resolve new catalog IDs only for the exact reviewed destinations;
            # a later unrelated catalog addition cannot join this selection.
            if v.get("all_images"):
                selected = [row["id"] for row in select_rows(root, **filters)
                            if destinations.get(row["relative"]) == row["sha256"]]
            result = start_publication(root, selected, _paths(v), configuration,
                                       device=v.get("device", "auto"), progress=progress, _loaded_models=loaded)
        except RiposteError as exc:
            return {"mode": "SORT_RIPOSTE_RESULT", "checkpoint": "INCOMPLETE", "sorting": sorting,
                    "protection": "STOPPED", "code": exc.code, "recovery": "Use RIPOSTE to retry protection; sorting has completed."}
        return {**result, "workflow": "SORT_RIPOSTE", "sorting": sorting}
    if name in {"publish", "plan", "riposte", "riposte-plan"}:
        from ..publication import publication_plan, start_publication
        inputs = [Path(p).expanduser().absolute() for p in v.get("input_paths", [])]
        if inputs and (v.get("image_ids") or v.get("all_images") or any(v.get(k) for k in ("year", "month", "size"))):
            raise RiposteError("INPUT_SELECTION_CONFLICT")
        ids, configuration = ([] if inputs else image_selection(root, v)), resolved_recipe(root, v)
        intake = {"input_paths": inputs, "date_mode": v.get("date_mode", "download")}
        if name in {"plan", "riposte-plan"}: return publication_plan(root, ids, configuration, **intake)
        return start_publication(root, ids, _paths(v), configuration, device=v.get("device", "auto"),
                                 pipeline_dir=_optional(v, "inpaint"), temporal_dir=_optional(v, "video"), progress=progress, **intake)
    if name == "publications":
        from ..publication import publication_status, publications
        return publication_status(root, v["batch_id"]) if v.get("batch_id") else publications(root)
    if name == "resume":
        from ..publication import resume_publication
        return resume_publication(root, v["batch_id"], _paths(v), device=v.get("device", "auto"),
                                  pipeline_dir=_optional(v, "inpaint"), temporal_dir=_optional(v, "video"), progress=progress)
    if name == "review":
        from ..publication import review_publication
        return review_publication(root, v["batch_id"], v["item_ids"], v.get("decision", "ACCEPTED"),
                                  v.get("visual_accepted", False), v.get("acknowledge_unverified", False))
    if name == "package":
        from ..publication import export_publication
        return export_publication(root, v["batch_id"])
    if name == "upgrade":
        from ..store import upgrade_workspace
        return upgrade_workspace(root)
    if name == "guard":
        from ..lab import create_candidate
        return create_candidate(root, v["image_id"], _paths(v), max_edge=v.get("max_edge", 1536),
                                epsilon=v.get("epsilon", 4), steps=v.get("steps", 48), seed=v.get("seed", 7),
                                engine=v.get("engine", "coupled"), pipeline_dir=_optional(v, "inpaint"),
                                device=v.get("device", "auto"), preserve_white=v.get("preserve_white", True), progress=progress)
    if name == "compare":
        from ..lab import compare_external
        return compare_external(root, v["image_id"], Path(v["candidate"]).expanduser().absolute(),
                                v.get("max_edge", 1536), v.get("method", "external"))
    if name == "qualify":
        from ..qualification import qualify_trial
        return qualify_trial(root, cast(str, v["trial_id"]), _paths(v), device=v.get("device", "auto"), progress=progress)
    if name == "challenge":
        from ..generation import controlled_generation
        return controlled_generation(root, cast(str, v["trial_id"]), Path(v["model"]).expanduser().absolute(), v.get("task", "edit"),
                                     seeds=tuple(v.get("seeds") or (7, 19)), views=tuple(v.get("views") or ("identity", "jpeg70")),
                                     steps=v.get("steps", 25), progress=progress)
    if name == "benchmark":
        from ..benchmark import run_benchmark
        return run_benchmark(root, cast(str, v["trial_id"]), Path(v["model"]).expanduser().absolute(),
                             task=v.get("task", "edit"), steps=v.get("steps", 25))
    if name == "export":
        from ..lab import export_candidate
        return export_candidate(root, cast(str, v["trial_id"]), v.get("acknowledge_unverified", False))
    if name == "trials":
        from ..lab import trials, trial_report
        return trial_report(root, cast(str, v["trial_id"])) if v.get("trial_id") else trials(root)
    if name == "evaluations":
        from ..qualification import evaluations
        return evaluations(root, cast(str, v["trial_id"]))
    if name == "experiment":
        from ..experiment import experiment_status
        return experiment_status(root, v.get("run_id"))
    if name == "panel":
        from ..review_panel import panel_status
        return panel_status(root, v.get("panel_id"))
    if name == "panel-create":
        from ..review_panel import create_panel
        return create_panel(root, v["run_ids"], v.get("reviewers", 2),
                            Path(v["rubric"]).expanduser().absolute() if "rubric" in v else None)
    if name == "panel-packet":
        from ..review_panel import panel_packet
        return panel_packet(root, v["panel_id"], v["reviewer_id"])
    if name == "panel-review":
        from ..review_panel import record_panel_review
        return record_panel_review(root, v["panel_id"], Path(v["ratings"]).expanduser().absolute())
    if name == "cohort":
        from ..cohort import cohort_status
        return cohort_status(root, v.get("cohort_id"))
    if name == "cohort-challenge":
        from ..cohort import cohort_challenge
        return cohort_challenge(root, v["trial_ids"], Path(v["model"]).expanduser().absolute(), v["sample_size"],
                                v.get("task", "edit"), tuple(v.get("seeds") or (7, 19)),
                                tuple(v.get("views") or ("identity", "jpeg70")), v.get("steps", 25), progress)
    if name == "experiment-packet":
        from ..experiment import review_packet
        return review_packet(root, v["run_id"])
    if name == "experiment-review":
        from ..experiment import record_review
        return record_review(root, v["run_id"], Path(v["ratings"]).expanduser().absolute())
    if name == "generations":
        from ..generation import generation_runs
        return generation_runs(root, cast(str, v["trial_id"]))
    if name == "generation":
        from ..generation import generation_report
        return generation_report(root, v["run_id"])
    if name == "frame":
        return view_image(root, v, open_viewer=v.get("open_viewer",False))
    if name == "handoff":
        from ..publication import open_in_workshop
        return open_in_workshop(root, v["batch_id"], v["item_id"])
    if name in {"image", "open-image"}:
        return view_image(root, v, open_viewer=name == "open-image")
    raise RiposteError("COMMAND_NOT_AVAILABLE")


def image_bytes(root: Path, values: RequestValues) -> bytes:
    from ..store import find_image, safe_child
    from ..sanitize import png_audit
    if values.get("run_id"):
        from ..generation import generation_frame
        return generation_frame(root,values["run_id"],values["relative"])
    if values.get("batch_id"):
        from ..publication import publication_pixels
        return publication_pixels(root, values["batch_id"], values["item_id"],
                                  values.get("kind", "candidate"), view=values.get("view", "identity"))
    if values.get("trial_id"):
        from ..lab import trial_pixels
        return trial_pixels(root, cast(str, values["trial_id"]), values.get("kind", "candidate"), values.get("view", "identity"))
    if values.get("view", "identity") != "identity" or values.get("kind", "candidate") not in {"candidate", "clean"}:
        raise RiposteError("CLEAN_MASTER_VIEW_INVALID")
    row = find_image(root, values["image_id"])
    raw = safe_child(root, row["relative"]).read_bytes()
    if png_audit(raw)["sha256"] != row["sha256"]:
        raise RiposteError("CATALOG_FILE_CHANGED")
    return raw


def view_image(root: Path, values: RequestValues, open_viewer: bool = False) -> ImageInfo:
    """Return image information or explicitly open an audited clean PNG.

    For canonical images, open the canonical path. For transformed/review images,
    write a date-only cache from verified bytes. No raw source or metadata is copied.
    The viewer is a local OS handoff, not evidence that somebody inspected pixels.
    """
    from ..sanitize import png_audit
    from ..store import safe_child, state_relative, atomic_clean_write, workspace_lock, find_image
    raw = image_bytes(root, values)
    audit = png_audit(raw)
    result = cast(ImageInfo, {"mode": "VERIFIED_IMAGE", **audit, "viewer": "NOT_OPENED"})
    if not open_viewer: return result
    if values.get("image_id") and not values.get("batch_id") and not values.get("trial_id"):
        relative = find_image(root, values["image_id"])["relative"]
    else:
        relative = state_relative(root, f'terminal-previews/{audit["sha256"]}.png')
        with workspace_lock(root):
            path = safe_child(root, relative)
            if path.exists():
                if path.read_bytes() != raw: raise RiposteError("PREVIEW_ARTIFACT_CHANGED")
            else: atomic_clean_write(root, relative, raw)
    path = safe_child(root, relative)
    try:
        if os.name == "nt":
            os.startfile(str(path))
        else:
            command = "open" if sys.platform == "darwin" else "xdg-open"
            completed = subprocess.run([command, str(path)], stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
            if completed.returncode: raise RiposteError("LOCAL_VIEWER_UNAVAILABLE")
    except (OSError, subprocess.SubprocessError):
        raise RiposteError("LOCAL_VIEWER_UNAVAILABLE") from None
    return {**result, "relative": relative, "viewer": "HANDOFF_REQUESTED"}


def result_exit_code(result: object) -> int:
    if isinstance(result, dict):
        if result.get("checkpoint") == "INCOMPLETE" or result.get("ready") is False:
            return 2
        counts = result.get("counts", {})
        if result.get("mode") == "PUBLICATION_BATCH" and (counts.get("BLOCKED", 0) or counts.get("PENDING", 0)):
            return 2
    return 0
