"""Authored action deck and form schema; choices are data, never shell code."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import math
import shlex
from ..errors import RiposteError
from .service import Request, EFFECTS


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "text"
    default: Any = ""
    help: str = ""
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    optional: bool = False


@dataclass(frozen=True)
class Action:
    key: str
    title: str
    section: str
    summary: str
    fields: tuple[Field, ...] = ()

    @property
    def effect(self): return EFFECTS.get(self.key, "INSPECT")


DEVICE = Field("device", "Device", "choice", "auto", "Explicit runtime target. Auto follows the installed runtime.", ("auto", "cpu", "cuda", "mps"))
VAE_FIELDS = tuple(Field(f"vae{i}", f"Local encoder {i}", "path", "", "Local config + safetensors directory; never stored in session history.", optional=True) for i in range(1, 5))
INPAINT = Field("inpaint", "Inpainting model", "path", "", "Optional local nine-channel inpainting pipeline.", optional=True)
VIDEO = Field("video", "Video model", "path", "", "Optional SVD temporal objective; not text-guided video.", optional=True)
IMAGE = Field("image_id", "Image ID", "id", "", "Exact 32-character ID from the clean library.")
TRIAL = Field("trial_id", "Trial ID", "id", "", "Exact trial ID from the optional workshop.")
BATCH = Field("batch_id", "Batch ID", "id", "", "Exact publishing batch ID.")
ITEM = Field("item_id", "Output ID", "id", "", "Exact item ID within the batch.")
MODEL = Field("model", "Generation model", "path", "", "Explicit local model; paths are not written into result records.")
STEPS = Field("steps", "Iterations", "int", 24, "Real optimization iterations per restart.", minimum=1, maximum=1000)
SEED = Field("seed", "Seed", "int", 7, "Deterministic starting seed, not a reproducibility certificate.", minimum=0, maximum=4294967295)
EPSILON = Field("epsilon", "Channel-change cap", "int", 4, "Maximum integer 8-bit channel change; edge/white budgets may be lower.", minimum=1, maximum=16)
WHITE = Field("preserve_white", "Preserve smooth white", "bool", True, "Leave zero-budget white pixels unchanged.")
EDGES = Field("edges", "Publishing edges", "ints", (1536,), "1-3 distinct final edges, comma-separated. No upscale.", minimum=64, maximum=4096)
PUB_FIELDS = (EDGES, EPSILON, STEPS, Field("restarts", "Search restarts", "int", 2, "Keep the best acceptable checkpoint across starts.", minimum=1, maximum=4), SEED, WHITE,
              Field("delta_e76_p95", "Colour-difference cap", "float", 6.0, "95th percentile CIELAB Delta E76 limit.", minimum=.1, maximum=40),
              Field("rms_fraction", "Local RMS fraction", "float", .95, "Local-tile RMS as a fraction of the pixel cap.", minimum=.1, maximum=1),
              DEVICE, *VAE_FIELDS, INPAINT, VIDEO)
MAX_EDGE = Field("max_edge", "Maximum edge", "int", 1536, "Public raster limit; no enlargement.", minimum=64, maximum=4096)
INPUT_FIELDS = tuple(Field(f"input{i}", "File or folder" if i == 1 else f"Additional file/folder {i}", "path", "",
                           "Choose a file or a folder of images. Folders include subfolders. Originals stay in place.", optional=i > 1) for i in range(1, 5))
SORT_FIELDS = (
    Field("date_mode", "Date basis", "choice", "download", "Creation/birth time with modified-time fallback, or an explicit alternative.", ("download", "modified", "embedded")),
    Field("discard_sidecars", "Discard metadata sidecars", "bool", False, "Authorize known metadata sidecar deletion during Apply, not during preview."))

ACTIONS = (
    Action("riposte", "RIPOSTE", "PRIMARY", "Protect files or folders. Keep originals and their folder structure.", (*INPUT_FIELDS, SORT_FIELDS[0], *PUB_FIELDS)),
    Action("sort-riposte", "Sort + RIPOSTE", "PRIMARY", "Preview sorting, confirm replacement, then protect the organized collection.", (*SORT_FIELDS, *PUB_FIELDS)),
    Action("publish", "Protect & publish", "PRIMARY", "Selected clean images -> independently optimized publishing files.", PUB_FIELDS),
    Action("organize", "Sort", "PRIMARY", "Preview image/video sorting into img/vid folders; originals saved for undo.", SORT_FIELDS),
    Action("categories", "Filename categories", "PRIMARY", "Discover filename terms and review session groups. No files or rules are written.", (
        Field("min_count", "Minimum file count", "int", 2, "Each term counts once per filename, wherever it occurs.", minimum=1, maximum=1_000_000_000),
        Field("max_words", "Maximum phrase words", "int", 3, "Suggest contiguous phrases up to three words.", minimum=1, maximum=3),
        Field("limit", "Suggestions shown", "int", 100, "Show the most frequent suggestions; all eligible filenames are counted.", minimum=1, maximum=500),
        Field("category_specs", "Category groups", "words", (), "Select or rename: Hockey=hockey. Merge: Hockey=hockey;goalie. Separate categories with commas. Session only.", optional=True),
        Field("ignore", "Ignore suggestions", "words", (), "Comma-separated words or phrases to hide from suggestions.", optional=True),
        Field("fillers", "Filler words", "text", "a,an,and,at,by,for,from,in,of,on,or,the,to,with", "Comma-separated filler words. Clear to include every nonnumeric word.", optional=True))),
    Action("undo-sort", "Undo last sort", "PRIMARY", "Preview restoring original files and names. Conflicts block restoration."),
    Action("audit", "Audit clean workspace", "PRIMARY", "Verify date-only images and calendar/size organization."),
    Action("doctor", "Local model setup", "SYSTEM", "Inspect runtime or execute a local encoder input-gradient probe.", (*VAE_FIELDS, DEVICE, Field("execute", "Run encoder probe", "bool", False, "Execution-only diagnostic; does not certify protection."))),
    Action("resume", "Resume publishing", "PRIMARY", "Reuse committed outputs; retry unfinished work with matching models.", (BATCH, *VAE_FIELDS, DEVICE, INPAINT, VIDEO)),
    Action("review", "Record output review", "PRIMARY", "Approve exact pixels or revoke approval for future packs.", (BATCH,
        Field("item_ids", "Output IDs", "ids", (), "Comma-separated exact output IDs."),
        Field("decision", "Decision", "choice", "ACCEPTED", "Acceptance applies only to exact committed bytes.", ("ACCEPTED", "REJECTED")),
        Field("visual_accepted", "Visual quality accepted", "bool", False, "Assert only after viewing actual image pixels, not the ASCII thumbnail."),
        Field("acknowledge_unverified", "AI resistance unverified", "bool", False, "Acknowledge that approval is aesthetic, not an efficacy certificate."))),
    Action("package", "Package approved images", "PRIMARY", "Exact accepted PNG bytes, calendar/size names; no research reports.", (BATCH,)),
    Action("upgrade", "Upgrade legacy state", "SYSTEM", "Rename old SHROUD application state; image and IDs stay intact."),
    Action("guard", "Standalone candidate", "WORKSHOP", "Expert single-image engine path; normal publishing is elsewhere.", (IMAGE, *VAE_FIELDS, MAX_EDGE, EPSILON,
        Field("steps", "Iterations", "int", 48, "Real optimization iterations.", minimum=1, maximum=1000), SEED,
        Field("engine", "Engine", "choice", "coupled", "Select an existing experimental image objective.", ("coupled", "encoder")), DEVICE, WHITE, INPAINT)),
    Action("compare", "Import external candidate", "WORKSHOP", "Sanitize an external candidate and compare against the clean baseline.", (IMAGE,
        Field("candidate", "Candidate PNG", "path", "", "Existing local candidate; not copied with raw metadata."), MAX_EDGE,
        Field("method", "Method label", "text", "external", "A label, not evidence that an upstream engine executed."))),
    Action("qualify", "Encoder comparison", "WORKSHOP", "Matched controls and actual transports; encoder proxy only.", (TRIAL, *VAE_FIELDS, DEVICE)),
    Action("challenge", "Five-arm generation", "WORKSHOP", "Clean, candidate and three controls through a local reference generator.", (TRIAL, MODEL,
        Field("task", "Task", "choice", "edit", "Local CUDA reference baseline.", ("edit", "inpaint", "video")),
        Field("steps", "Generation steps", "int", 25, "Steps per generation call.", minimum=1, maximum=100),
        Field("seeds", "Seeds", "ints", (7, 19), "Comma-separated seeds; each adds five calls per view.", minimum=0, maximum=4294967295),
        Field("views", "Transport views", "words", ("identity", "jpeg70"), "Comma-separated: identity, jpeg85, resize75, jpeg70, jpeg60, resize50-jpeg80, offset-crop85, blur06."))),
    Action("benchmark", "Legacy paired generation", "WORKSHOP", "Compatibility runner; five-arm challenge is the controlled helper.", (TRIAL, MODEL,
        Field("task", "Task", "choice", "edit", "Image edit or image-conditioned video.", ("edit", "video")),
        Field("steps", "Generation steps", "int", 25, "Denoising steps.", minimum=1, maximum=100))),
    Action("export", "Expert trial export", "WORKSHOP", "Unreviewed compatibility export; not the approved-image package.", (TRIAL,
        Field("acknowledge_unverified", "AI resistance unverified", "bool", False, "Required for this expert compatibility export."))),
    Action("trials", "Browse workshop trials", "WORKSHOP", "Read saved trial evidence; never promoted to protection certification.", (
        Field("trial_id", "Trial ID (optional)", "id", "", "Leave empty to list trials.", optional=True),)),
    Action("evaluations", "Saved encoder results", "WORKSHOP", "Read saved controlled encoder evidence.", (TRIAL,)),
    Action("generations", "Saved generation runs", "WORKSHOP", "Read saved full-generation run summaries.", (TRIAL,)),
    Action("generation", "Complete generation report", "WORKSHOP", "Inspect a saved run and its committed frame names.", (
        Field("run_id","Generation run ID","id","","Exact saved generation run ID."),)),
    Action("frame", "Inspect generation frame", "WORKSHOP", "Open or inspect one verified saved frame without generating again.", (
        Field("run_id","Generation run ID","id","","Exact saved generation run ID."),
        Field("relative","Committed frame name","text","","Exact relative frame name from its generation report; no arbitrary file path."),
        Field("open_viewer","Open local image viewer","bool",False,"Explicit local handoff of the verified frame. No approval is recorded."))),
    Action("handoff", "Exact-file workshop handoff", "WORKSHOP", "Copy committed publishing pixels to the helper, without resizing or rerendering.", (BATCH, ITEM)),
)
BY_KEY = {action.key: action for action in ACTIONS}


def defaults(action: Action, models: dict | None = None) -> dict:
    values = {f.key: f.default for f in action.fields}
    if models:
        for key in values.keys() & models.keys(): values[key] = models[key]
    return values


def parse_value(field: Field, raw: Any) -> Any:
    if field.optional and raw in (None, "", ()):
        return ""
    try:
        if field.kind == "bool":
            if isinstance(raw, bool): return raw
            if str(raw).lower() in ("on", "yes", "true", "1"): return True
            if str(raw).lower() in ("off", "no", "false", "0"): return False
            raise ValueError
        if field.kind == "choice":
            if raw not in field.choices: raise ValueError
            return raw
        if field.kind in ("ints", "ids", "words"):
            seq = tuple(x.strip() for x in raw.split(",") if x.strip()) if isinstance(raw, str) else tuple(raw)
            if not seq: raise ValueError
            if field.kind == "ints":
                sub = Field(field.key, field.label, "int", minimum=field.minimum, maximum=field.maximum)
                seq = tuple(parse_value(sub, x) for x in seq)
            if field.kind == "ids":
                seq = tuple(parse_value(Field(field.key, field.label, "id"), x) for x in seq)
            if len(set(seq)) != len(seq): raise ValueError
            return seq
        if field.kind == "int":
            if isinstance(raw, bool) or isinstance(raw, float) and not raw.is_integer(): raise ValueError
            value = int(raw)
        elif field.kind == "float":
            value = float(raw)
            if not math.isfinite(value): raise ValueError
        else:
            text = str(raw).strip()
            if not text or len(text) > 4096 or any(ord(c) < 32 or ord(c) == 127 for c in text): raise ValueError
            if field.kind == "id" and (len(text) != 32 or any(c not in "0123456789abcdef" for c in text)): raise ValueError
            # Pasted paths may include matching quote delimiters; no environment interpolation.
            if field.kind == "path" and len(text) > 1 and text[0] == text[-1] and text[0] in "\"'": text = text[1:-1]
            return text
        if field.minimum is not None and value < field.minimum: raise ValueError
        if field.maximum is not None and value > field.maximum: raise ValueError
        return value
    except (ValueError, TypeError, OverflowError):
        raise RiposteError("FIELD_VALUE_INVALID") from None


def make_request(key: str, root: Path | None, values: dict, selected=()) -> Request:
    action = BY_KEY[key]
    parsed = {f.key: parse_value(f, values.get(f.key, f.default)) for f in action.fields}
    for f in action.fields:
        if f.kind=="path" and parsed.get(f.key): parsed[f.key]=Path(parsed[f.key])
    vaes = [parsed.pop(f"vae{i}", "") for i in range(1, 5)]
    if any(f.key.startswith("vae") for f in action.fields): parsed["vae_dirs"] = [Path(p) for p in vaes if p]
    if key == "publish": parsed["image_ids"] = list(selected)
    if key == "riposte": parsed["input_paths"] = [Path(p) for p in values["input_paths"]] if values.get("input_paths") else [parsed.pop(f"input{i}") for i in range(1, 5) if parsed.get(f"input{i}")]
    for i in range(1, 5): parsed.pop(f"input{i}", None)
    if key == "sort-riposte": parsed["all_images"] = True
    if key == "review": parsed["item_ids"] = list(parsed["item_ids"])
    return Request(key, root, parsed)


def request_argv(request: Request) -> list[str]:
    """Generate a real Typer command, never execute the rendered command line."""
    name = {"plan": "publish", "riposte-plan": "riposte", "sort-riposte-plan": "sort-riposte", "apply": "organize", "undo-sort-apply": "undo-sort", "handoff": "workshop", "open-image": "image"}.get(request.name, request.name)
    args = ["riposte", name]
    if request.root is not None and name != "doctor": args.append(str(request.root))
    values = request.values
    pos = {"inspect": ("image_id",), "guard": ("image_id",), "compare": ("image_id", "candidate"),
           "qualify": ("trial_id",), "challenge": ("trial_id",), "benchmark": ("trial_id",), "export": ("trial_id",),
           "publications": ("batch_id",), "resume": ("batch_id",), "review": ("batch_id",), "package": ("batch_id",),
           "trials": ("trial_id",), "evaluations": ("trial_id",), "generations": ("trial_id",), "generation": ("run_id",), "frame": ("run_id", "relative"), "workshop": ("batch_id", "item_id")}.get(name, ())
    for key in pos:
        if values.get(key): args.append(str(values[key]))
    aliases = {"category_specs": "category", "input_paths": "input", "open_viewer": "open", "vae_dirs": "vae", "image_ids": "image", "all_images": "all", "edges": "edge", "item_ids": "item", "seeds": "seed", "views": "view"}
    for key, value in values.items():
        if name == "categories" and key == "fillers" and value == "":
            args.extend(["--fillers", ""])
            continue
        if key in pos or value is None or value == "" or value == [] or value == (): continue
        if name == "guard" and key == "inpaint": option = "pipeline"
        else: option = aliases.get(key, key).replace("_", "-")
        if isinstance(value, bool):
            if key == "preserve_white":
                if not value: args.append("--no-preserve-white")
            elif value: args.append("--" + option)
        elif isinstance(value, (list, tuple)):
            for entry in value: args.extend(["--" + option, str(entry)])
        else: args.extend(["--" + option, str(value)])
    if request.name in {"plan", "riposte-plan", "sort-riposte-plan"}: args.append("--plan")
    if request.name in {"apply", "sort-riposte", "undo-sort-apply"}: args.append("--apply")
    if request.name == "open-image": args.append("--open")
    return args


def command_line(request: Request, shell="powershell") -> str:
    args = request_argv(request)
    if shell == "powershell":
        def quote(x): return x if x and all(c.isalnum() or c in "-_=./:" for c in x) else "'" + x.replace("'", "''") + "'"
        return " ".join(quote(x) for x in args)
    return shlex.join(args)
