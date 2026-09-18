"""Typer's actual parameter records, composed in an ASCII Rich help sheet."""
from __future__ import annotations
import io
import os
import sys
from rich.console import Console
from rich.table import Table
from rich.text import Text
from .palette import PALETTES
from rich import box
from typer.core import TyperGroup, TyperCommand


def format_help(command, ctx, formatter):
    stream = io.StringIO()
    console = Console(file=stream, width=min(ctx.terminal_width or 100, 140), markup=False, highlight=False,
                      force_terminal=sys.stdout.isatty() and os.environ.get("TERM") != "dumb", no_color="NO_COLOR" in os.environ)
    chosen = getattr(getattr(ctx, "obj", None), "theme", "goks")
    palette = PALETTES.get(chosen, PALETTES["goks"])
    console.print(Text("\n  RIPOSTE / IMAGE SECURITY", style="bold " + palette["accent"]))
    console.print(Text("  " + (command.help or "Local image protection and publication.")))
    console.print(Text("\n  " + command.get_usage(ctx)))
    records = []
    for param in command.get_params(ctx):
        record = param.get_help_record(ctx)
        if record: records.append(record)
    if records:
        table = Table(box=box.ASCII2, title="PARAMETERS", title_justify="left", show_header=False, padding=(0, 1))
        table.add_column(style="bold", min_width=22); table.add_column()
        for left, right in records: table.add_row(Text(left), Text(right))
        console.print(table)
    if isinstance(command, TyperGroup):
        groups = {}
        for name in command.list_commands(ctx):
            sub = command.get_command(ctx, name)
            if sub is None or sub.hidden: continue
            groups.setdefault(getattr(sub, "rich_help_panel", None) or "COMMANDS", []).append((name, sub.get_short_help_str(80)))
        for title, rows in groups.items():
            table = Table(box=None, title=title, title_justify="left", show_header=False, padding=(0, 1))
            table.add_column(style="bold " + palette["accent"], min_width=16); table.add_column()
            for left, right in rows: table.add_row(Text(left), Text(right))
            console.print(table)
    if command.epilog: console.print(Text("\n  " + command.epilog))
    formatter.write(stream.getvalue())


class RichCommand(TyperCommand):
    def format_help(self, ctx, formatter): format_help(self, ctx, formatter)


class RichGroup(TyperGroup):
    def format_help(self, ctx, formatter): format_help(self, ctx, formatter)
