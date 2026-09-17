"""Typer command surface and native Rich entry. No argparse compatibility shell."""
from __future__ import annotations
from enum import Enum
import os
from pathlib import Path
import sys
from typing import Annotated, Optional
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
                  epilog="No command opens the animated terminal. Piped direct results are JSON. ROOT is a dedicated artwork folder.")

Root = Annotated[Path, typer.Argument(help="Existing dedicated artwork folder; everything inside is in scope.")]
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


def command(name=None, panel="PRIMARY"):
    return app.command(name, cls=RichCommand, rich_help_panel=panel)


def dispatch(ctx, name, root=None, **values):
    for key, value in list(values.items()):
        if isinstance(value, Enum): values[key] = value.value
    raise typer.Exit(run_direct(Request(name, root, values), ctx.obj or Presentation()))


@command("ui", "INTERFACE")
def ui(ctx: typer.Context, root: Annotated[Optional[Path], typer.Argument(help="Initial artwork workspace.")] = None,
       linear: Annotated[bool, typer.Option("--linear", help="Explicit numbered, line-input menus; also works with a script on stdin.")] = False):
    """Open the interactive Rich ASCII terminal."""
    from .terminal.app import launch
    raise typer.Exit(launch(root or (Path(ctx.find_root().params["root"]) if ctx.find_root().params.get("root") else None), ctx.obj, linear=linear or ctx.obj.plain))


@command("organize", "CLEAN COLLECTION")
def organize(ctx: typer.Context, root: Root,
             apply: Annotated[bool, typer.Option("--apply", help="AUTHORIZE removing each verified source after sanitized replacement. No raw backups.")] = False,
             discard_sidecars: Annotated[bool, typer.Option("--discard-sidecars", help="Authorize known metadata sidecar/cache removal on apply.")] = False,
             date_mode: Annotated[DateMode, typer.Option(help="Date-only retention basis.")] = DateMode.download):
    """Read-only recursive plan; --apply explicitly replaces sources."""
    dispatch(ctx, "apply" if apply else "organize", root, discard_sidecars=discard_sidecars, date_mode=date_mode)


@command("audit", "CLEAN COLLECTION")
def audit(ctx: typer.Context, root: Root):
    """Verify clean image containers and calendar/size organization."""
    dispatch(ctx, "audit", root)


@command("list", "CLEAN COLLECTION")
def list_images(ctx: typer.Context, root: Root,
                year: Annotated[Optional[str], typer.Option(help="2026, 2025, 2024, or EVERYTHING_ELSE.")] = None,
                month: Annotated[Optional[str], typer.Option(help="English name, abbreviation, or 1-12.")] = None,
                size: Annotated[Optional[str], typer.Option(help="SML, MED, LRG, or XTL.")] = None,
                search: Annotated[str, typer.Option(help="Literal search of clean canonical names, dates and IDs.")] = "",
                limit: Annotated[Optional[int], typer.Option(min=1, help="Maximum returned rows.")] = None,
                offset: Annotated[int, typer.Option(min=0, help="Skip returned rows.")] = 0):
    """List and target cleaned artwork; never sort by file extension."""
    dispatch(ctx, "list", root, year=year, month=month, size=size, search=search, limit=limit, offset=offset)


@command("inspect", "CLEAN COLLECTION")
def inspect(ctx: typer.Context, root: Root, image_id: Annotated[str, typer.Argument(help="Exact clean image ID.")]):
    """Independently audit a selected clean image and show its record."""
    dispatch(ctx, "inspect", root, image_id=image_id)


@command("publish", "PROTECT + PUBLISH")
def publish(ctx: typer.Context, root: Root,
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
            size: Annotated[Optional[str], typer.Option(help="Size-bin filter, with --all only.")] = None):
    """Protect a selected batch at each final size; clean masters stay unchanged."""
    dispatch(ctx, "plan" if plan else "publish", root, image_ids=image or [], all_images=all_images, vae_dirs=vae or [],
             edges=edge or [1536], epsilon=epsilon, steps=steps, restarts=restarts, seed=seed,
             preserve_white=preserve_white, inpaint=inpaint, video=video, device=device,
             delta_e76_p95=delta_e76_p95, rms_fraction=rms_fraction, year=year, month=month, size=size)


# Discoverable alias, identical parameter schema and backend path.
app.command("protect", cls=RichCommand, rich_help_panel="PROTECT + PUBLISH", help="Alias of publish; same full parameter surface.")(publish)


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
    """Explicit legacy-state rename; artwork and identifiers are preserved."""
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
