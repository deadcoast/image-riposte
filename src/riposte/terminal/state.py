"""Session-only UI state. Pure renderers never write image or app state."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from .actions import Field
from .output import Presentation

HOME = (
    ("sorter", "Riposte Sorter", "Ready-to-use sorting: Sort, Dry Run, Enter Path"),
    ("riposte", "RIPOSTE", "Protect files or folders; preserve originals"),
    ("sort-riposte", "Sort + RIPOSTE", "Organize, then protect in one workflow"),
    ("library", "Image library", "Browse and select cleaned images"),
    ("batches", "Publishing batches", "Review, resume, package"),
    ("doctor", "Local models", "Configure local processing"),
    ("preferences", "Terminal & workspace", "Palette, motion, workspace"),
    ("organize", "Full Sort Workshop", "Configure dates, categories, assignments and sidecars"),
    ("undo-sort", "Undo last sort", "Preview restoring original files and names"),
    ("workshop", "Workshop", "Optional expert protection helpers"),
)

@dataclass
class Page:
    name: str = "home"
    title: str = "MAIN MENU"
    cursor: int = 0
    query: str = ""
    query_edit: bool = False
    scroll: int = 0
    report_view: str = "overview"
    advanced: bool = False
    display_cache: dict = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)
    action: str | None = None
    values: dict = field(default_factory=dict)
    result: Any = None
    request: Any = None
    code: str | None = None
    image_id: str | None = None
    batch_id: str | None = None
    item_id: str | None = None
    preview: Any = None
    kind: str = "candidate"
    view: str = "identity"
    report: dict = field(default_factory=dict)
    confirm_word: str = ""
    confirm_request: Any = None
    success_page: str | None = None

@dataclass
class Editor:
    field: Field
    value: str
    position: int = 0
    error: bool = False
    target: str = "field"
    error_message: str = ""

@dataclass
class Session:
    root: Path | None
    presentation: Presentation
    page: Page = field(default_factory=Page)
    stack: list[Page] = field(default_factory=list)
    selected: set[str] = field(default_factory=set)
    catalog: list[dict] = field(default_factory=list)
    batches: list[dict] = field(default_factory=list)
    models: dict = field(default_factory=dict)
    editor: Editor | None = None
    operation: Any = None
    operation_request: Any = None
    last_request: Any = None
    notice: str = ""
    paused: bool = False
    frozen_time: float = 0.0
    running: bool = True
    exit_after_job: bool = False
    switch_linear: bool = False
    handoff: list[str] | None = None
    width: int = 100
    height: int = 34
