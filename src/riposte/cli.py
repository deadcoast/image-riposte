"""Typer command surface and native Rich entry. No argparse compatibility shell."""
from __future__ import annotations
from enum import Enum
import os
from pathlib import Path
import sys
from typing import Annotated, Optional, ParamSpec, TypeVar, NoReturn, cast
from collections.abc import Callable
from .records import RequestValues
import click
import typer
from . import __version__
from .errors import RiposteError
from .terminal.help import RichCommand, RichGroup
from .terminal.output import Presentation, error, run_direct
from .terminal.service import Request

app = typer.Typer(name="riposte", cls=RichGroup, invoke_without_command=True, no_args_is_help=False,
                  add_completion=True, pretty_exceptions_enable=False, pretty_exceptions_show_locals=False,
                  help="Clean masters in. Reviewed publishing images out. No watermark or upload gate.",
                  epilog="No command opens the animated terminal. Piped direct results are JSON. ROOT is a dedicated image folder.")

Root = Annotated[Path, typer.Argument(help="Existing dedicated image folder; everything inside is in scope.")]
Vae = Annotated[Optional[list[Path]], typer.Option("--vae", help="Local encoder directory. Repeat for up to four; no automatic download.", rich_help_panel="LOCAL MODELS")]

class Device(str, Enum): auto="auto"; cpu="cpu"; cuda="cuda"; mps="mps"
class DateMode(str, Enum): download="download"; modified="modified"; embedded="embedded"
class Theme(str, Enum): goks="goks"; dark="dark"; light="light"; mono="mono"
class Engine(str, Enum): coupled="coupled"; encoder="encoder"
class Task(str, Enum): edit="edit"; inpaint="inpaint"; video="video"
class Decision(str, Enum): ACCEPTED="ACCEPTED"; REJECTED="REJECTED"


def _version(value: bool):
    if value:
        typer.echo(f"RIPOSTE {__version__}")
        raise typer.Exit()


@app.callback()
def root_callback(ctx: typer.Context,
                  root: Annotated[Optional[Path], typer.Option("--root", "-w", help="Initial workspace for the interactive terminal.")] = None,
                  json_output: Annotated[bool, typer.Option("--json", help="One JSON result on stdout; code-only errors on stderr.")] = False,
                  human: Annotated[bool, typer.Option("--human", help="Rich readable direct-command output, even when piped.")] = False,
                  plain: Annotated[bool, typer.Option("--plain", help="Linear menus and plain ASCII output; no ANSI or motion.")] = False,
                  no_color: Annotated[bool, typer.Option("--no-color", help="Disable colour; also respects NO_COLOR.")] = False,
                  no_animation: Annotated[bool, typer.Option("--no-animation", "--no-anim", help="Freeze aesthetic motion; keep actual status updates.")] = False,
                  theme: Annotated[Theme, typer.Option(help="Terminal palette.")] = Theme.goks,
                  fps: Annotated[int, typer.Option(min=4, max=30, help="Maximum terminal refresh frequency, not processing speed.")] = 12,
                  events: Annotated[bool, typer.Option("--events", help="Code-defined progress JSON Lines on stderr for direct commands.")] = False,
                  version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True, help="Show installed release.")] = False):
    if json_output and human: raise RiposteError("OUTPUT_MODE_CONFLICT")
    presentation = Presentation(True if json_output else False if human else None, plain, no_color,
                                no_animation or os.environ.get("RIPOSTE_NO_ANIMATION") == "1", theme.value, fps, events)
    ctx.obj = presentation
    if ctx.invoked_subcommand is None:
        from .terminal.app import launch
        code = launch(root, presentation, linear=plain)
        raise typer.Exit(code)


_P = ParamSpec("_P")
_R = TypeVar("_R")


def command(name: str | None = None, panel: str = "PRIMARY") -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    return app.command(name, cls=RichCommand, rich_help_panel=panel)


def dispatch(ctx: typer.Context, name: str, root: Path | None = None, **values: object) -> NoReturn:
    for key, value in list(values.items()):
        if isinstance(value, Enum): values[key] = value.value
    raise typer.Exit(run_direct(Request(name, root, cast(RequestValues, values)), ctx.obj or Presentation()))


@command("ui", "INTERFACE")
def ui(ctx: typer.Context, root: Annotated[Optional[Path], typer.Argument(help="Initial image workspace.")] = None,
       linear: Annotated[bool, typer.Option("--linear", help="Explicit numbered, line-input menus; also works with a script on stdin.")] = False):
    """Open the interactive Rich ASCII terminal."""
    from .terminal.app import launch
    raise typer.Exit(launch(root or (Path(ctx.find_root().params["root"]) if ctx.find_root().params.get("root") else None), ctx.obj, linear=linear or ctx.obj.plain))


@command("organize", "CLEAN COLLECTION")
@command("sort", "WORKFLOWS")
def organize(ctx: typer.Context, root: Root,
             apply: Annotated[bool, typer.Option("--apply", help="AUTHORIZE sorting sources. Private original copies are retained for undo.")] = False,
             discard_sidecars: Annotated[bool, typer.Option("--discard-sidecars", help="Authorize known metadata sidecar/cache removal on apply.")] = False,
             date_mode: Annotated[DateMode, typer.Option(help="Date-only retention basis.")] = DateMode.download,
             categories: Annotated[bool, typer.Option("--categories", help="Use saved category rules and preview exact destinations.")] = False,
             assign: Annotated[Optional[list[str]], typer.Option("--assign", help="Manual source-relative-path=category-slug; repeat. Use =auto to clear a saved manual choice.")] = None,
             plan_id: Annotated[Optional[str], typer.Option("--plan-id", help="Exact preview ID; required with --apply. Repreview after input or policy changes.")] = None):
    """Read-only recursive plan; --apply explicitly replaces sources."""
    dispatch(ctx, "apply" if apply else "organize", root, discard_sidecars=discard_sidecars, date_mode=date_mode,
             categories=categories, assignments=assign or [], plan_id=plan_id)


@command("undo-sort", "WORKFLOWS")
def undo_sort(ctx: typer.Context, root: Root,
              apply: Annotated[bool, typer.Option("--apply", help="Restore the last recorded sort after checking for conflicts.")] = False,
              sort_id: Annotated[Optional[str], typer.Option(help="Require the exact sort ID shown by a previous undo preview.")] = None):
    """Preview undo; --apply restores original names, bytes and modified times."""
    dispatch(ctx, "undo-sort-apply" if apply else "undo-sort", root, sort_id=sort_id)


@command("health", "WORKFLOWS")
def health(ctx: typer.Context, root: Root,
           max_entries: Annotated[int, typer.Option(min=1, max=200_000, help="Bound storage inspection; partial totals stay explicit.")] = 100_000) -> None:
    """Inspect storage and recovery without writing, pruning or reclaiming locks."""
    dispatch(ctx, "health", root, max_entries=max_entries)


@command("duplicates", "WORKFLOWS")
def duplicates(ctx: typer.Context, root: Root,
               visual: Annotated[bool, typer.Option("--visual/--no-visual", help="Add normalized-pixel and visual evidence to exact byte comparisons.")] = True,
               videos: Annotated[bool, typer.Option("--videos/--no-videos", help="Sample video frames with local FFmpeg; byte comparison is always available.")] = True,
               include_float: Annotated[bool, typer.Option("--include-float/--no-include-float", help="Inspect float storage independently of sorting.")] = True,
               max_files: Annotated[int, typer.Option(min=1, max=200_000, help="Maximum inventoried files; hitting a limit reports incomplete coverage.")] = 100_000,
               max_visual: Annotated[int, typer.Option(min=1, max=20_000, help="Maximum distinct media decoded after byte-copy collapse.")] = 10_000,
               max_pairs: Annotated[int, typer.Option(min=1, max=500_000, help="Maximum visual candidate pairs.")] = 100_000,
               max_findings: Annotated[int, typer.Option(min=1, max=50_000, help="Maximum reported findings; truncation is explicit.")] = 20_000,
               max_file_bytes: Annotated[int, typer.Option(min=1, max=64 * 1024**3, help="Largest individual file to hash.")] = 4 * 1024**3,
               report: Annotated[Optional[Path], typer.Option(help="Explicitly export a new JSON (full evidence) or CSV (finding summary) file. Never overwrite.")] = None) -> None:
    """Find DUPLICATE, MAYBE DUPLICATE and CLOSELY RELATED files. Never sorts or removes sources."""
    dispatch(ctx, "duplicates", root, visual=visual, videos=videos, include_float=include_float,
             max_files=max_files, max_visual=max_visual, max_pairs=max_pairs, max_findings=max_findings,
             max_file_bytes=max_file_bytes, duplicate_report=report)


@command("categories", "CLEAN COLLECTION")
def categories(ctx: typer.Context, root: Root,
               min_count: Annotated[int, typer.Option(min=1, max=1_000_000_000, help="Minimum distinct filenames per suggestion.")] = 2,
               max_words: Annotated[int, typer.Option(min=1, max=3, help="Longest suggested phrase in words.")] = 3,
               limit: Annotated[int, typer.Option(min=1, max=500, help="Maximum suggestions shown; all files are counted.")] = 100,
               category: Annotated[Optional[list[str]], typer.Option("--category", help="Session draft: Hockey=hockey;goalie. Repeat for more categories.")] = None,
               ignore: Annotated[Optional[list[str]], typer.Option("--ignore", help="Hide this suggestion; repeat for more terms.")] = None,
               fillers: Annotated[str, typer.Option(help="Comma-separated filler words; empty includes every nonnumeric word.")] = "a,an,and,at,by,for,from,in,of,on,or,the,to,with") -> None:
    """Discover filename categories and review explicit groups. No files or rules are written."""
    dispatch(ctx, "categories", root, min_count=min_count, max_words=max_words, limit=limit,
             category_specs=category or [], ignore=ignore or [], fillers=fillers)


@command("category-rules", "CLEAN COLLECTION")
def category_rules(ctx: typer.Context, root: Root,
                   category: Annotated[Optional[list[str]], typer.Option("--category", help="Complete replacement selection: Hockey=hockey;goalie. Repeat for each group.")] = None,
                   exclude: Annotated[Optional[list[str]], typer.Option("--exclude", help="Exclude matching titles from this category: Hockey=table hockey;toy.")] = None,
                   priority: Annotated[Optional[list[str]], typer.Option("--priority", help="Category priority: Hockey=10. Higher wins; equal highest matches need review.")] = None,
                   slug: Annotated[Optional[list[str]], typer.Option("--slug", help="Stable folder name: Hockey=hockey. Repeat to override generated names.")] = None,
                   clear: Annotated[bool, typer.Option("--clear", help="Preview an empty replacement ruleset; use --save to commit it.")] = False,
                   save: Annotated[bool, typer.Option("--save", help="AUTHORIZE saving the complete ruleset privately. Never moves media.")] = False,
                   expected_revision: Annotated[Optional[str], typer.Option("--expected-revision", help="Revision from the rule preview; 'missing' for the first save.")] = None,
                   review: Annotated[bool, typer.Option("--review", help="Read-only matching-file counts and examples using these rules.")] = False) -> None:
    """Inspect saved rules or preview a replacement. --save requires the current revision."""
    dispatch(ctx, "category-rules-save" if save else "category-rules", root,
             category_specs=category or [], exclusions=exclude or [], priorities=priority or [],
             slugs=slug or [], clear=clear, expected_revision=expected_revision, review=review)


@command("audit", "CLEAN COLLECTION")
def audit(ctx: typer.Context, root: Root):
    """Verify clean image containers and calendar/size organization."""
    dispatch(ctx, "audit", root)


@command("list", "CLEAN COLLECTION")
def list_images(ctx: typer.Context, root: Root,
                year: Annotated[Optional[str], typer.Option(help="Four-digit calendar year, or legacy EVERYTHING_ELSE.")] = None,
                month: Annotated[Optional[str], typer.Option(help="English name, abbreviation, or 1-12.")] = None,
                size: Annotated[Optional[str], typer.Option(help="SML, MED, LRG, or XTL.")] = None,
                search: Annotated[str, typer.Option(help="Literal search of clean canonical names, dates and IDs.")] = "",
                limit: Annotated[Optional[int], typer.Option(min=1, help="Maximum returned rows.")] = None,
                offset: Annotated[int, typer.Option(min=0, help="Skip returned rows.")] = 0):
    """List and target cleaned image; never sort by file extension."""
    dispatch(ctx, "list", root, year=year, month=month, size=size, search=search, limit=limit, offset=offset)


@command("library-search", "CLEAN COLLECTION")
def library_search(ctx: typer.Context, root: Root,
                   search: Annotated[str, typer.Option(help="Private original title, category, canonical path, date or ID; literal Unicode substring.")] = "",
                   category: Annotated[str, typer.Option(help="Exact saved category folder slug, matched without case.")] = "",
                   title_state: Annotated[str, typer.Option(help="all, known or unknown original titles.")] = "all",
                   year: Optional[str] = None, month: Optional[str] = None, size: Optional[str] = None,
                   limit: Annotated[int, typer.Option(min=1, max=500)] = 50,
                   offset: Annotated[int, typer.Option(min=0, max=1_000_000_000)] = 0,
                   expected_revision: Annotated[Optional[str], typer.Option(help="Previous search revision; reject changed pages.")] = None) -> None:
    """Explicit private lookup. Output contains original filenames; keep it local."""
    dispatch(ctx, "library-search", root, search=search, category=category, title_state=title_state,
             year=year, month=month, size=size, limit=limit, offset=offset, expected_revision=expected_revision)


@command("inspect", "CLEAN COLLECTION")
def inspect(ctx: typer.Context, root: Root, image_id: Annotated[str, typer.Argument(help="Exact clean image ID.")]):
    """Independently audit a selected clean image and show its record."""
    dispatch(ctx, "inspect", root, image_id=image_id)


@command("publish", "PROTECT + PUBLISH")
@command("riposte", "WORKFLOWS")
@command("sort-riposte", "WORKFLOWS")
def publish(ctx: typer.Context, root: Root,
            budget_mask: Annotated[Optional[Path], typer.Option(help="Optional grayscale PNG mask for one selected image: black preserves, white permits automatic limits.")] = None,
            budget_map: Annotated[Optional[Path], typer.Option(help="Private mask map exported from publishing; binds masks to exact clean source hashes.")] = None,
            view_budget: Annotated[Optional[int], typer.Option(min=1, max=600, help="With --plan: open this numbered mask overlay in your local image viewer. Creates only a private date-only preview cache.")] = None,
            budget_revision: Annotated[Optional[str], typer.Option(help="Exact budget revision from --plan; reject changed masks, sizes or quality limits.")] = None,
            budget_offset: Annotated[int, typer.Option(min=0, max=599, help="With --plan: skip this many masked rasters; previews return at most three.")] = 0,
            recipe_name: Annotated[Optional[str], typer.Option("--recipe", help="Load saved publishing settings; explicit setting flags override them. Paths and approvals are never loaded.")] = None,
            recipe_revision: Annotated[Optional[str], typer.Option("--recipe-revision", help="Optional exact recipe revision from recipes; reject a changed selection.")] = None,
            image: Annotated[Optional[list[str]], typer.Option("--image", help="Target exact clean image IDs; repeat for a selection.")] = None,
            all_images: Annotated[bool, typer.Option("--all", help="Explicitly select the full collection, optionally filtered.")] = False,
            vae: Vae = None,
            edge: Annotated[Optional[list[int]], typer.Option("--edge", min=64, max=4096, help="Independent final publishing edge. Repeat up to three.")] = None,
            epsilon: Annotated[int, typer.Option(min=1, max=16, help="Integer per-channel change cap.")] = 4,
            steps: Annotated[int, typer.Option(min=1, max=1000, help="Optimization iterations per restart.")] = 24,
            restarts: Annotated[int, typer.Option(min=1, max=4, help="Seeded starts; keep the best feasible candidate.")] = 2,
            seed: Annotated[int, typer.Option(min=0, max=4294967295)] = 7,
            plan: Annotated[bool, typer.Option("--plan", help="Read-only selection and sizing preview; no model needed.")] = False,
            preserve_white: Annotated[bool, typer.Option("--preserve-white/--no-preserve-white")] = True,
            inpaint: Annotated[Optional[Path], typer.Option(help="Optional local nine-channel inpainting objective.")] = None,
            video: Annotated[Optional[Path], typer.Option(help="Optional local SVD temporal objective, not text-guided.")] = None,
            device: Device = Device.auto,
            delta_e76_p95: Annotated[float, typer.Option(min=.1, max=40, help="95th percentile colour-difference limit.")] = 6.,
            rms_fraction: Annotated[float, typer.Option(min=.1, max=1, help="Local RMS fraction of the pixel-change cap.")] = .95,
            year: Annotated[Optional[str], typer.Option(help="Calendar filter, with --all only.")] = None,
            month: Annotated[Optional[str], typer.Option(help="Month filter, with --all only.")] = None,
            size: Annotated[Optional[str], typer.Option(help="Size-bin filter, with --all only.")] = None,
            input_paths: Annotated[Optional[list[Path]], typer.Option("--input", help="Source file or folder; repeat to combine selections. Preserves originals; mutually exclusive with --image/--all.")] = None,
            date_mode: Annotated[DateMode, typer.Option(help="Date basis for selected raw inputs or sorting.")] = DateMode.download,
            apply: Annotated[bool, typer.Option("--apply", help="Sort + RIPOSTE only: authorize source replacement then protection. Otherwise this workflow previews.")] = False,
            discard_sidecars: Annotated[bool, typer.Option(help="Sort + RIPOSTE only: authorize metadata sidecar deletion during sorting.")] = False,
            categories: Annotated[bool, typer.Option("--categories", help="Sort + RIPOSTE only: use saved category rules.")] = False,
            assign: Annotated[Optional[list[str]], typer.Option("--assign", help="Manual source-relative-path=category-slug; repeat.")] = None,
            plan_id: Annotated[Optional[str], typer.Option("--plan-id", help="Combined preview ID required with sort-riposte --apply; binds sorting and protection choices.")] = None):
    """Protect a selected batch at each final size; clean masters stay unchanged."""
    combined = ctx.info_name == "sort-riposte"
    if view_budget is not None and (not plan or combined):
        raise RiposteError("ARTIST_MASK_PREVIEW_REQUIRED")
    if not combined and (apply or discard_sidecars or categories or assign or plan_id):
        raise RiposteError("SORT_CONSENT_REQUIRES_COMBINED_WORKFLOW")
    operation = ("sort-riposte-plan" if plan or not apply else "sort-riposte") if combined else ("plan" if plan else "publish")
    if ctx.info_name == "riposte": operation = "riposte-plan" if plan else "riposte"
    dispatch(ctx, operation, root, image_ids=image or [], all_images=all_images, vae_dirs=vae or [],
             budget_mask=budget_mask, budget_map=budget_map, view_budget=view_budget, budget_revision=budget_revision, budget_offset=budget_offset,
             recipe_name=recipe_name, recipe_revision=recipe_revision,
             recipe_overrides=[("edges" if key == "edge" else key) for key in ("edge", "epsilon", "steps", "restarts", "seed", "preserve_white", "delta_e76_p95", "rms_fraction")
                               if (source := ctx.get_parameter_source(key)) is not None and source.name != "DEFAULT"],
             edges=edge or [1536], epsilon=epsilon, steps=steps, restarts=restarts, seed=seed,
             preserve_white=preserve_white, inpaint=inpaint, video=video, device=device,
             delta_e76_p95=delta_e76_p95, rms_fraction=rms_fraction, year=year, month=month, size=size,
             input_paths=input_paths or [], date_mode=date_mode, discard_sidecars=discard_sidecars,
             categories=categories, assignments=assign or [], plan_id=plan_id)


# Discoverable alias, identical parameter schema and backend path.
app.command("protect", cls=RichCommand, rich_help_panel="PROTECT + PUBLISH", help="Alias of publish; same full parameter surface.")(publish)


@command("recipes", "PROTECT + PUBLISH")
def recipes(ctx: typer.Context, root: Root,
            name: Annotated[Optional[str], typer.Argument(help="Leave empty to list saved recipes.")] = None,
            preview: Annotated[bool, typer.Option(help="Preview named settings, including a new recipe with defaults.")] = False,
            save: Annotated[bool, typer.Option(help="Explicitly save only these publishing settings; never starts processing.")] = False,
            expected_revision: Annotated[Optional[str], typer.Option(help="Library revision from preview; use missing for the first save.")] = None,
            edge: Annotated[Optional[list[int]], typer.Option("--edge", min=64, max=4096)] = None,
            epsilon: Annotated[Optional[int], typer.Option(min=1, max=16)] = None,
            steps: Annotated[Optional[int], typer.Option(min=1, max=1000)] = None,
            restarts: Annotated[Optional[int], typer.Option(min=1, max=4)] = None,
            seed: Annotated[Optional[int], typer.Option(min=0, max=4294967295)] = None,
            preserve_white: Annotated[Optional[bool], typer.Option("--preserve-white/--no-preserve-white")] = None,
            delta_e76_p95: Annotated[Optional[float], typer.Option(min=.1, max=40)] = None,
            rms_fraction: Annotated[Optional[float], typer.Option(min=.1, max=1)] = None):
    """List, inspect or preview a named recipe; save only with an explicit revision."""
    from .recipes import inspect_recipes
    settings = {key: value for key, value in dict(edges=edge, epsilon=epsilon, steps=steps,
                restarts=restarts, seed=seed, preserve_white=preserve_white,
                delta_e76_p95=delta_e76_p95, rms_fraction=rms_fraction).items() if value is not None}
    if save:
        if name is None: raise RiposteError("RECIPE_NAME_REQUIRED")
        if expected_revision is None: raise RiposteError("RECIPE_REVISION_REQUIRED")
        draft = inspect_recipes(root, name, settings=settings)
        dispatch(ctx, "recipes-save", root, recipe_name=name, recipe_settings=draft["settings"], expected_revision=expected_revision)
    if expected_revision is not None: raise RiposteError("RECIPE_REVISION_REQUIRES_SAVE")
    dispatch(ctx, "recipes", root, recipe_name=name, recipe_settings=settings if preview or settings else None)


@command("publications", "PROTECT + PUBLISH")
def publications(ctx: typer.Context, root: Root, batch_id: Annotated[Optional[str], typer.Argument(help="Leave empty to list batches.")] = None):
    """List batches or inspect their real output/review states."""
    dispatch(ctx, "publications", root, batch_id=batch_id)


@command("resume", "PROTECT + PUBLISH")
def resume(ctx: typer.Context, root: Root, batch_id: str, vae: Vae = None,
           inpaint: Optional[Path] = None, video: Optional[Path] = None, device: Device = Device.auto):
    """Resume unfinished output work with matching local model identities."""
    dispatch(ctx, "resume", root, batch_id=batch_id, vae_dirs=vae or [], inpaint=inpaint, video=video, device=device)


@command("review", "PROTECT + PUBLISH")
def review(ctx: typer.Context, root: Root, batch_id: str,
           item: Annotated[list[str], typer.Option("--item", help="Exact output IDs; repeat for a reviewed selection.")],
           decision: Decision = Decision.ACCEPTED,
           visual_accepted: Annotated[bool, typer.Option("--visual-accepted")] = False,
           acknowledge_unverified: Annotated[bool, typer.Option("--acknowledge-unverified")] = False):
    """Accept exact pixels or revoke approval. Not a protection certificate."""
    dispatch(ctx, "review", root, batch_id=batch_id, item_ids=item, decision=decision,
             visual_accepted=visual_accepted, acknowledge_unverified=acknowledge_unverified)


@command("package", "PROTECT + PUBLISH")
def package(ctx: typer.Context, root: Root, batch_id: str):
    """Write a calendar/size ZIP containing only exact approved PNGs."""
    dispatch(ctx, "package", root, batch_id=batch_id)


@command("image", "PROTECT + PUBLISH")
def image(ctx: typer.Context, root: Root,
          image_id: Annotated[Optional[str], typer.Option("--image-id", "--image", help="Clean master ID.")] = None,
          batch_id: Annotated[Optional[str], typer.Option("--batch-id", "--batch", help="Publishing batch ID.")] = None,
          item_id: Annotated[Optional[str], typer.Option("--item-id", "--item", help="Publishing output ID.")] = None,
          trial_id: Annotated[Optional[str], typer.Option("--trial-id", "--trial", help="Workshop trial ID.")] = None,
          kind: Annotated[str, typer.Option(help="candidate, clean, or difference.")] = "candidate",
          view: Annotated[str, typer.Option(help="Actual publication transform; identity opens exact raster.")] = "identity",
          open_viewer: Annotated[bool, typer.Option("--open", help="Explicitly hand the audited PNG to the local image viewer.")] = False):
    """Inspect or open verified pixels without starting the browser workshop."""
    if sum(bool(v) for v in (image_id, batch_id, trial_id)) != 1 or bool(item_id) != bool(batch_id):
        raise RiposteError("IMAGE_TARGET_INVALID")
    dispatch(ctx, "open-image" if open_viewer else "image", root, image_id=image_id, batch_id=batch_id,
             item_id=item_id, trial_id=trial_id, kind=kind, view=view)


@command("doctor", "LOCAL RUNTIME")
def doctor(ctx: typer.Context, vae: Vae = None,
           execute: Annotated[bool, typer.Option("--execute", help="Actually load and exercise encoder input gradients.")] = False,
           device: Device = Device.auto):
    """Inspect local runtime or execute a selected local encoder probe."""
    dispatch(ctx, "doctor", vae_dirs=vae or [], execute=execute, device=device)


@command("upgrade", "LOCAL RUNTIME")
def upgrade(ctx: typer.Context, root: Root):
    """Explicit legacy-state rename; image and identifiers are preserved."""
    dispatch(ctx, "upgrade", root)


@command("serve", "INTERFACE")
def serve(ctx: typer.Context, root: Root,
          port: Annotated[int, typer.Option(min=1024, max=65535)] = 8765,
          no_browser: Annotated[bool, typer.Option("--no-browser")] = False):
    """Run the existing local browser interface as an optional alternative."""
    import threading
    import webbrowser
    import uvicorn
    from .server import create_app
    application = create_app(root)
    url = f"http://127.0.0.1:{port}/#token={application.state.token}"
    # Transient local session credential, not a source pathname or saved log.
    typer.echo("RIPOSTE / local browser session\n" + url, err=True)
    timer = None
    if not no_browser:
        timer = threading.Timer(1.5, lambda: webbrowser.open(url)); timer.daemon = True; timer.start()
    try: uvicorn.run(application, host="127.0.0.1", port=port, access_log=False, log_level="critical")
    finally:
        if timer: timer.cancel()


@command("guard", "OPTIONAL WORKSHOP")
def guard(ctx: typer.Context, root: Root, image_id: str, vae: Vae = None,
          max_edge: Annotated[int, typer.Option(min=64, max=4096)] = 1536,
          epsilon: Annotated[int, typer.Option(min=1, max=16)] = 4,
          steps: Annotated[int, typer.Option(min=1, max=1000)] = 48,
          seed: Annotated[int, typer.Option(min=0, max=4294967295)] = 7,
          engine: Engine = Engine.coupled,
          pipeline: Annotated[Optional[Path], typer.Option(help="Optional local inpainting pipeline, coupled only.")] = None,
          device: Device = Device.auto,
          preserve_white: Annotated[bool, typer.Option("--preserve-white/--no-preserve-white")] = True):
    """Expert standalone candidate path. Normal batches use publish."""
    dispatch(ctx, "guard", root, image_id=image_id, vae_dirs=vae or [], max_edge=max_edge, epsilon=epsilon,
             steps=steps, seed=seed, engine=engine, inpaint=pipeline, device=device, preserve_white=preserve_white)


@command("compare", "OPTIONAL WORKSHOP")
def compare(ctx: typer.Context, root: Root, image_id: str, candidate: Path, max_edge: Annotated[int, typer.Option(min=64, max=4096)] = 1536, method: str = "external"):
    """Sanitize and compare an externally processed candidate."""
    dispatch(ctx, "compare", root, image_id=image_id, candidate=candidate, max_edge=max_edge, method=method)


@command("qualify", "OPTIONAL WORKSHOP")
def qualify(ctx: typer.Context, root: Root, trial_id: str, vae: Vae = None, device: Device = Device.auto):
    """Controlled encoder comparison; not an efficacy verdict."""
    dispatch(ctx, "qualify", root, trial_id=trial_id, vae_dirs=vae or [], device=device)


@command("challenge", "OPTIONAL WORKSHOP")
def challenge(ctx: typer.Context, root: Root, trial_id: str,
              model: Annotated[Path, typer.Option(help="Local CUDA generation pipeline.")], task: Task = Task.edit,
              steps: Annotated[int, typer.Option(min=1, max=100)] = 25,
              seed: Annotated[Optional[list[int]], typer.Option("--seed", min=0, max=4294967295)] = None,
              view: Annotated[Optional[list[str]], typer.Option("--view")] = None):
    """Generate clean/candidate/three-control arms with matched seeds."""
    dispatch(ctx, "challenge", root, trial_id=trial_id, model=model, task=task, steps=steps, seeds=seed, views=view)


@command("benchmark", "OPTIONAL WORKSHOP")
def benchmark(ctx: typer.Context, root: Root, trial_id: str, model: Annotated[Path, typer.Option()], task: Task = Task.edit, steps: Annotated[int, typer.Option(min=1, max=100)] = 25):
    """Legacy paired generation compatibility path."""
    if task == Task.inpaint: raise RiposteError("BENCHMARK_TASK_INVALID")
    dispatch(ctx, "benchmark", root, trial_id=trial_id, model=model, task=task, steps=steps)


@command("experiment", "OPTIONAL WORKSHOP")
def experiment(ctx: typer.Context, root: Root, run_id: Annotated[Optional[str], typer.Argument()] = None) -> None:
    """List attempts or inspect a protocol, bound outputs and recorded reviews."""
    dispatch(ctx, "experiment", root, **({"run_id": run_id} if run_id else {}))


@command("cohort-challenge", "OPTIONAL WORKSHOP")
def cohort_challenge(ctx: typer.Context, root: Root,
                     trial: Annotated[list[str], typer.Option("--trial", help="Explicit sampling pool; repeat for every eligible trial.")],
                     model: Annotated[Path, typer.Option(help="Local CUDA baseline used for every selected artwork.")],
                     sample_size: Annotated[int, typer.Option(min=1, help="Number drawn without replacement from the fixed pool.")],
                     task: Task = Task.edit, steps: Annotated[int, typer.Option(min=1, max=100)] = 25,
                     seed: Annotated[Optional[list[int]], typer.Option("--seed", min=0, max=4294967295)] = None,
                     view: Annotated[Optional[list[str]], typer.Option("--view")] = None) -> None:
    """Commit the full cohort, then generate one attempt per selected artwork."""
    dispatch(ctx, "cohort-challenge", root, trial_ids=trial, model=model, sample_size=sample_size,
             task=task, steps=steps, seeds=seed, views=view)


@command("cohort", "OPTIONAL WORKSHOP")
def cohort(ctx: typer.Context, root: Root, cohort_id: Annotated[Optional[str], typer.Argument()] = None) -> None:
    """List committed cohorts or inspect all members and missing-outcome bounds."""
    dispatch(ctx, "cohort", root, **({"cohort_id": cohort_id} if cohort_id else {}))


@command("panel-create", "OPTIONAL WORKSHOP")
def panel_create(ctx: typer.Context, root: Root,
                 run: Annotated[list[str], typer.Option(help="Completed experiment ID; repeat to include more.")],
                 reviewers: Annotated[int, typer.Option(min=2, max=8)] = 2,
                 rubric: Annotated[Optional[Path], typer.Option(help="Optional task-rubric JSON; default anchors are unvalidated.")] = None) -> None:
    """Freeze calibration items, rubric and separate reviewer assignments."""
    dispatch(ctx, "panel-create", root, run_ids=run, reviewers=reviewers, **({"rubric": rubric} if rubric else {}))


@command("panel", "OPTIONAL WORKSHOP")
def panel(ctx: typer.Context, root: Root, panel_id: Annotated[Optional[str], typer.Argument()] = None) -> None:
    """List panels or inspect exact agreement, missing decisions and disagreement."""
    dispatch(ctx, "panel", root, **({"panel_id": panel_id} if panel_id else {}))


@command("panel-packet", "OPTIONAL WORKSHOP")
def panel_packet(ctx: typer.Context, root: Root, panel_id: str, reviewer_id: str) -> None:
    """Export the local blinded packet for one assigned reviewer slot."""
    dispatch(ctx, "panel-packet", root, panel_id=panel_id, reviewer_id=reviewer_id)


@command("panel-review", "OPTIONAL WORKSHOP")
def panel_review(ctx: typer.Context, root: Root, panel_id: str,
                 ratings: Annotated[Path, typer.Option(help="Final ratings.json for one slot; nulls remain missing.")]) -> None:
    """Record one final response. Corrections require a new panel."""
    dispatch(ctx, "panel-review", root, panel_id=panel_id, ratings=ratings)


@command("experiment-packet", "OPTIONAL WORKSHOP")
def experiment_packet(ctx: typer.Context, root: Root, run_id: str) -> None:
    """Export verified frames with concealed arm labels and a ratings template."""
    dispatch(ctx, "experiment-packet", root, run_id=run_id)


@command("experiment-review", "OPTIONAL WORKSHOP")
def experiment_review(ctx: typer.Context, root: Root, run_id: str,
                      ratings: Annotated[Path, typer.Option(help="Completed ratings.json from this experiment's review packet.")]) -> None:
    """Append endpoint decisions and a descriptive matched-control contrast."""
    dispatch(ctx, "experiment-review", root, run_id=run_id, ratings=ratings)


@command("export", "OPTIONAL WORKSHOP")
def export(ctx: typer.Context, root: Root, trial_id: str,
           acknowledge_unverified: Annotated[bool, typer.Option("--acknowledge-unverified")] = False):
    """Unreviewed expert trial export. Approved images use package."""
    dispatch(ctx, "export", root, trial_id=trial_id, acknowledge_unverified=acknowledge_unverified)


@command("trials", "OPTIONAL WORKSHOP")
def trials(ctx: typer.Context, root: Root, trial_id: Optional[str] = typer.Argument(None)):
    """List trials or read one complete trial report."""
    dispatch(ctx, "trials", root, trial_id=trial_id)


@command("evaluations", "OPTIONAL WORKSHOP")
def evaluations(ctx: typer.Context, root: Root, trial_id: str):
    """Read saved controlled encoder results."""
    dispatch(ctx, "evaluations", root, trial_id=trial_id)


@command("generations", "OPTIONAL WORKSHOP")
def generations(ctx: typer.Context, root: Root, trial_id: str):
    """Read saved generation-run summaries."""
    dispatch(ctx, "generations", root, trial_id=trial_id)


@command("generation", "OPTIONAL WORKSHOP")
def generation(ctx: typer.Context, root: Root, run_id: str):
    """Read one complete saved generation report, including committed frame names."""
    dispatch(ctx,"generation",root,run_id=run_id)


@command("frame", "OPTIONAL WORKSHOP")
def frame(ctx: typer.Context, root: Root, run_id: str,
          relative: Annotated[str,typer.Argument(help="Exact relative frame name listed in the committed run report.")],
          open_viewer: Annotated[bool,typer.Option("--open",help="Open the verified date-only frame in a local viewer.")]=False):
    """Inspect or open an exact saved generation frame; no generator runs."""
    dispatch(ctx,"frame",root,run_id=run_id,relative=relative,open_viewer=open_viewer)


@command("workshop", "OPTIONAL WORKSHOP")
def workshop(ctx: typer.Context, root: Root, batch_id: Optional[str] = typer.Argument(None), item_id: Optional[str] = typer.Argument(None)):
    """Open helper menus, or hand off BATCH_ID ITEM_ID as exact pixels."""
    if batch_id or item_id:
        if not batch_id or not item_id: raise RiposteError("PUBLICATION_ITEM_NOT_FOUND")
        dispatch(ctx, "handoff", root, batch_id=batch_id, item_id=item_id)
    from .terminal.app import launch
    raise typer.Exit(launch(root, ctx.obj, initial="workshop", linear=ctx.obj.plain))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    presentation = Presentation(True if "--json" in argv else False if "--human" in argv else None,
                                plain="--plain" in argv, no_color="--no-color" in argv)
    try:
        result = app(args=argv, prog_name="riposte", standalone_mode=False)
        return int(result) if isinstance(result, int) else 0
    except RiposteError as exc:
        error(exc.code, presentation); return 2
    except (click.BadParameter, click.UsageError, click.NoSuchOption, click.MissingParameter):
        # Click's error text can echo a private path or untrusted terminal controls.
        # The custom help page explains valid values without printing rejected input.
        error("CLI_ARGUMENT_INVALID", presentation); return 2
    except (click.Abort, KeyboardInterrupt):
        error("INTERRUPTED", presentation); return 130
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    except Exception:
        error("OPERATION_FAILED", presentation); return 2


if __name__ == "__main__":
    raise SystemExit(main())
