"""Human Rich output and one-document JSON automation output."""
from __future__ import annotations
from dataclasses import dataclass
import json
import os
import sys
import time
from rich.console import Console
from rich import box
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.live import Live
from ..recovery import CATALOG, guidance
from .surface import Surface, PALETTES, ascii_text
from .material import activity_trace
from .jobs import Operation, safe_code
from .service import Request
from .signals import termination_guard, TerminationRequested


@dataclass
class Presentation:
    json_output: bool | None = None
    plain: bool = False
    no_color: bool = False
    no_animation: bool = False
    theme: str = "goks"
    fps: int = 12
    events: bool = False

    @property
    def machine(self):
        return self.json_output if self.json_output is not None else not sys.stdout.isatty() and not self.plain

    def console(self, stderr=False):
        return Console(stderr=stderr, markup=False, highlight=False,
                       no_color=self.no_color or self.plain or "NO_COLOR" in os.environ,
                       force_terminal=False if self.plain or os.environ.get("TERM") == "dumb" else None)


# Compatibility view; all presentations use the shared catalog below.
RECOVERY = {code: guidance(code).action for code in CATALOG["entries"]}


def error(code: str, presentation: Presentation, operation: str = ""):
    code = safe_code(code)
    if presentation.machine:
        print(json.dumps({"error": code}), file=sys.stderr)
    else:
        console = presentation.console(stderr=True)
        console.print(Text(f"\n  [STOP] {code}", style="bold " + PALETTES[presentation.theme]["danger"]))
        item = guidance(code, operation)
        console.print(Text("  " + item.title))
        console.print(Text("  Next action: " + item.action))


def result_table(rows, title=None):
    table = Table(title=title, box=box.ASCII2, header_style="bold", show_lines=False, expand=False, padding=(0, 1))
    if rows and isinstance(rows[0], dict):
        preferred = ["id", "relative", "day", "width", "height", "status", "review", "sequence", "counts", "code"]
        columns = [k for k in preferred if k in rows[0]]
        if not columns: columns = list(rows[0])[:5]
        for k in columns: table.add_column(k.upper(), overflow="fold")
        for row in rows:
            values = []
            for key in columns:
                value = row.get(key, "")
                if isinstance(value, dict): value = "  ".join(f"{k}: {v}" for k, v in value.items())
                values.append(Text(ascii_text(value)))
            table.add_row(*values)
    else:
        table.add_column("VALUE")
        for row in rows: table.add_row(Text(ascii_text(row)))
    return table


def emit(result, presentation: Presentation, command=""):
    if presentation.machine:
        print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
        return
    from .reports import overview, report_lines
    console = presentation.console()
    palette = PALETTES[presentation.theme]
    width = max(20, min(112, console.width - 4))
    report = overview(result, command, width)
    console.print(Text("\n  RIPOSTE / " + report.title.upper(), style=f"bold {palette['accent']}"))
    console.print(Text("  " + "-" * width, style=palette["line"]))
    console.print(Text("  [" + report.outcome + "]", style=f"bold {palette[report.tone]}"))
    console.print(Text("  " + report.explanation, style=palette["muted"]))
    console.print()
    for line in report_lines(report, result, "overview", width):
        console.print(Text("  ") + line.rich(presentation.theme))
    console.print()


class Activity:
    def __init__(self, operation, presentation, console):
        self.operation, self.presentation, self.console = operation, presentation, console

    def __rich__(self):
        s = self.operation.snapshot()
        width = max(32, min(self.console.width, 132))
        canvas = Surface(width, 10, self.presentation.theme)
        canvas.text(2, 1, "RIPOSTE / " + self.operation.request.name.upper(), "accent", bold=True)
        canvas.text(2, 3, s.phase, width=width - 4)
        position = f"engine position {s.processed}/{s.total}" if s.total is not None and s.processed is not None else f"{s.processed} inspected" if s.processed is not None else "waiting for an engine count"
        canvas.text(2, 4, position + f"   |   elapsed {s.elapsed:.1f}s", "muted", width=width - 4)
        if s.item: canvas.text(2, 5, f"output {s.item}/{s.items}", "muted")
        t = 0 if self.presentation.no_animation else s.elapsed
        activity_trace(canvas, 2, 6, width - 4, t, s.state)
        caption = "Ctrl+C requests a checkpoint stop" if s.cancellable else "Source/record commit: interrupt waits for completion"
        canvas.text(2, 8, caption, "warn" if not s.cancellable else "muted", width=width - 4)
        return canvas


def run_direct(request: Request, presentation: Presentation):
    with termination_guard():
        return _run_direct(request,presentation)


def _run_direct(request: Request, presentation: Presentation):
    op = Operation(request).start()
    console = presentation.console(stderr=True)
    live = console.is_terminal and not presentation.machine and not presentation.plain
    previous = None
    terminated = False

    def wait_loop():
        nonlocal previous
        while not op.done.is_set():
            try:
                if presentation.events:
                    snapshot = op.snapshot()
                    event = {k: getattr(snapshot, k) for k in ("state", "phase", "processed", "total", "item", "items")}
                    if event != previous:
                        print(json.dumps(event, ensure_ascii=True), file=sys.stderr, flush=True)
                        previous = event
                op.done.wait(.07)
            except KeyboardInterrupt:
                op.cancel()  # Non-cancellable commits still finish before exit.

    try:
        if live and not presentation.events:
            with Live(Activity(op, presentation, console), console=console, refresh_per_second=presentation.fps if not presentation.no_animation else 2,
                      transient=True, redirect_stdout=False, redirect_stderr=False): wait_loop()
        else: wait_loop()
    except TerminationRequested:
        terminated = True
        op.cancel()
    finally:
        # Even a terminal write failure must not abandon a source-owning worker.
        if not op.done.is_set():
            op.cancel()
            while not op.done.is_set():
                try: op.done.wait(.1)
                except KeyboardInterrupt: op.cancel()
        op.join()
    snapshot = op.snapshot()
    if snapshot.code: error(snapshot.code, presentation, request.name)
    elif op.result is not None: emit(op.result, presentation, request.name)
    return 143 if terminated else op.exit_code
