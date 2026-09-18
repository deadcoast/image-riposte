"""Keyboard/line-input controller over the existing RIPOSTE operation boundary."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import time
from .actions import ACTIONS, BY_KEY, Field, defaults, make_request, parse_value
from .jobs import Operation, safe_code
from .keyboard import Key
from .output import Presentation
from .preview import make_preview
from .render import view_rows, scroll_limit
from .service import Request, execute, image_bytes, root_of
from .interaction import fields_for, contextual_help
from .state import Session, Page, Editor
from .paths import Picker, starting_directory, validate_workspace, locations
from ..errors import RiposteError
from ..metrics import TRANSFORMS


class Controller:
    def __init__(self, root: Path | None, presentation: Presentation, *, initial="home", operation_factory=Operation):
        self.state = Session(root.expanduser().absolute() if root else None, presentation,
                             paused=presentation.no_animation)
        self.factory = operation_factory
        self.started = time.monotonic()
        self.pending_action = None
        if root:
            root_of(Request("list", self.state.root))
            self.refresh()
        if initial == "workshop": self.show(Page("workshop", "OPTIONAL WORKSHOP"), remember=False)

    def refresh(self):
        if self.state.root is None: return
        self.state.catalog = execute(Request("list", self.state.root))
        self.state.batches = execute(Request("publications", self.state.root))
        self.state.selected.intersection_update(r["id"] for r in self.state.catalog)

    def show(self, page, remember=True):
        if remember and self.state.page.name != "job": self.state.stack.append(self.state.page)
        self.state.page = page
        self.state.notice = ""

    def back(self):
        self.state.editor = None
        self.state.page = self.state.stack.pop() if self.state.stack else Page()
        self.state.notice = ""

    def edit_workspace(self):
        self.browse("workspace", "preferences")

    def begin_action(self, key):
        if key == "riposte": return self.browse("inputs", key)
        if key in {"organize", "sort-riposte"}: return self.browse("sort", key)
        if key == "undo-sort": return self.browse("undo", key)
        return self.action(key)

    def browse(self, mode, action=None, inputs=(), field=None):
        settings = dict(self.state.page.values) if self.state.page.name == "form" else {}
        purpose = {
            "inputs": "Select images or folders to protect, including subfolders. Originals stay in place; sorting is not required.",
            "sort": "Select the folder to sort, including its subfolders. Preview first; replacing originals requires REPLACE.",
            "undo": "Select the folder previously sorted. Preview recovery first; restoring originals requires UNDO.",
            "workspace": "Select a results folder. RIPOSTE saves clean snapshots, candidates and review records here; selected originals stay unchanged.",
            "existing": "Open an existing image/results folder to view its library and saved batches. Selection changes no files.",
            "field": "Choose the folder for this setting. Selecting a location does not run processing.",
        }[mode]
        if action == "sort-riposte": purpose = "Sort this folder and its subfolders, then protect the images. Preview first; replacing originals requires REPLACE."
        title = "RIPOSTE / SELECT INPUTS" if mode == "inputs" else "SORT + RIPOSTE / SELECT FOLDER" if action == "sort-riposte" else "SORT / SELECT FOLDER" if mode == "sort" else "SELECT RESULTS FOLDER" if mode == "workspace" else "SELECT FOLDER"
        if mode == "undo": title = "UNDO LAST SORT / SELECT FOLDER"
        picker = Picker(starting_directory(self.state.root), multiple=mode == "inputs", selected=list(inputs))
        if field and self.state.page.values.get(field):
            picker.enter(Path(self.state.page.values[field]).expanduser())
        self.show(Page("picker", title, action=action, result=picker,
                       values={"mode": mode, "purpose": purpose, "inputs": list(inputs), "field": field, "settings": settings}, rows=picker.rows()))

    def picker_key(self, key):
        p = self.state.page
        picker = p.result
        row = self.selected_row()
        if key.name == "backspace": picker.enter(picker.directory.parent); p.cursor = 0
        elif key.text == "l":
            p.rows = locations(); p.cursor = 0; p.values["locations"] = True; return
        elif key.text == "g":
            value = str(picker.directory)
            self.state.editor = Editor(Field("location", "Go to folder", "path", "", "Optional: paste an existing folder path, or Esc to keep browsing."), value, len(value), target="picker-location")
            return
        elif key.text == "s" and picker.multiple: picker.toggle(picker.directory)
        elif key.text == " " and row and row.get("path") and picker.multiple and not p.values.get("locations") and row["kind"] != "parent":
            picker.toggle(row["path"])
        elif key.name == "enter" and row:
            if row["kind"] == "accept": return self.accept_picker()
            if row["kind"] in {"directory", "parent"}:
                picker.enter(row["path"]); p.cursor = 0; p.values.pop("locations", None)
            elif row["kind"] == "file": picker.toggle(row["path"])
        p.rows = picker.rows()
        self.state.notice = picker.error

    def accept_picker(self):
        p = self.state.page
        picker = p.result
        mode = p.values["mode"]
        if mode == "inputs":
            if not picker.selected:
                self.state.notice = "Select files or folders with Space, or s for this folder."
                return
            self.browse("workspace", "riposte", picker.selected)
            self.state.page.values["settings"] = p.values["settings"]
            return
        if mode == "field":
            field = p.values["field"]
            self.back(); self.state.page.values[field] = str(picker.directory)
            return
        try:
            root = validate_workspace(picker.directory)
        except RiposteError as exc:
            self.state.notice = "Keep image/results folders separate from the application folder." if exc.code == "IMAGE_FOLDER_OVERLAPS_APPLICATION" else "Choose an accessible existing folder without linked paths."
            return
        self.state.root = root
        self.state.selected.clear()
        self.refresh()
        action = p.action
        if action == "browser":
            self.state.handoff = ["serve", str(root)]; self.state.running = False; return
        if action == "riposte":
            paths = p.values["inputs"]
            return self.action(action, {**p.values["settings"], "input1": str(paths[0]), "input_paths": paths})
        if action: return self.action(action)
        self.back()

    def require_workspace(self, next_action):
        if self.state.root: return True
        self.browse("existing", next_action)
        return False

    def library(self):
        if not self.require_workspace("library"): return
        self.refresh()
        self.show(Page("library", "CLEAN LIBRARY", rows=self.state.catalog))

    def batches(self):
        if not self.require_workspace("batches"): return
        self.refresh()
        self.show(Page("batches", "PUBLISHING BATCHES", rows=self.state.batches))

    def batch(self, identifier, *, remember=True, result=None):
        value = result or execute(Request("publications", self.state.root, {"batch_id": identifier}))
        self.show(Page("batch", "REVIEW & PACKAGE", rows=value["items"], batch_id=identifier, result=value), remember=remember)

    def preferences(self):
        rows = [
            {"key": "workspace", "title": "Image workspace", "value": "SELECTED" if self.state.root else "NOT SELECTED"},
            {"key": "theme", "title": "Palette", "value": self.state.presentation.theme.upper()},
            {"key": "motion", "title": "ASCII motion", "value": "PAUSED" if self.state.paused else "LIVE"},
            {"key": "fps", "title": "Refresh ceiling", "value": str(self.state.presentation.fps) + " fps"},
            {"key": "linear", "title": "Linear interface", "value": "SWITCH"},
            {"key": "browser", "title": "Browser alternative", "value": "EXPLICIT HANDOFF"},
            {"key": "upgrade", "title": "Legacy state upgrade", "value": "NO IMAGES REWRITE"},
        ]
        if self.state.page.name == "preferences":
            self.state.page.rows = rows
        else: self.show(Page("preferences", "TERMINAL SETTINGS", rows=rows))

    def action(self, key, overrides=None):
        if key == "library": return self.library()
        if key == "batches": return self.batches()
        if key == "preferences": return self.preferences()
        if key == "workshop": return self.show(Page("workshop", "OPTIONAL WORKSHOP"))
        if key != "doctor" and not self.require_workspace(key): return
        if key == "publish" and not self.state.selected:
            self.library(); self.state.notice = "Press Enter to select images, then p to protect. Press i to inspect."
            return
        action = BY_KEY[key]
        values = defaults(action, self.state.models)
        if key == "riposte": values["input1"] = str(self.state.root)
        if overrides: values.update(overrides)
        if key == "upgrade":
            return self.confirm(Request("upgrade", self.state.root), "UPGRADE", "Rename legacy application state; keep image, dates and identifiers intact.")
        if not action.fields:
            return self.run(Request(key, self.state.root))
        self.show(Page("form", action.title.upper(), action=key, values=values))

    def request_from_form(self):
        p = self.state.page
        return make_request(p.action, self.state.root, p.values, sorted(self.state.selected))

    def save_model_session(self, values):
        for key in ("vae1", "vae2", "vae3", "vae4", "device", "inpaint", "video"):
            if key in values: self.state.models[key] = values[key]

    def run_form(self, preview=False):
        p = self.state.page
        request = self.request_from_form()
        self.save_model_session(p.values)
        if request.name in {"publish", "riposte"}:
            # The normal interactive primary button previews before creating files.
            request = Request(("plan" if request.name == "publish" else "riposte-plan") if preview else request.name, request.root, request.values)
        if request.name == "sort-riposte":
            request = Request("sort-riposte-plan", request.root, request.values)
        if request.name == "review":
            title = "Record visual approval for these exact output files." if request.values["decision"] == "ACCEPTED" else "Revoke this approval for future publishing packs."
            return self.confirm(request, "ACCEPT" if request.values["decision"] == "ACCEPTED" else "REJECT", title)
        self.run(request)

    def run(self, request):
        if self.state.operation and not self.state.operation.done.is_set():
            raise RiposteError("OPERATION_ALREADY_RUNNING")
        self.state.last_request = request
        self.state.operation_request = request
        self.show(Page("job", "ACTIVE OPERATION", request=request))
        self.state.operation = self.factory(request).start()

    def confirm(self, request, word, title):
        self.show(Page("confirm", title, confirm_word=word, confirm_request=request, values={"confirmation": ""}))

    def pump(self):
        operation = self.state.operation
        if operation is None or not operation.done.is_set(): return
        operation.join()
        snapshot, result = operation.snapshot(), operation.result
        request = self.state.operation_request
        self.state.operation = None
        try: self.refresh()
        except RiposteError as exc: self.state.notice = safe_code(exc.code)
        if self.state.exit_after_job:
            self.state.running = False
            return
        if snapshot.code:
            self.show(Page("result", "OPERATION STOPPED", code=snapshot.code, request=request), remember=False)
        elif request.name in {"publish", "riposte", "sort-riposte", "resume", "review"} and isinstance(result, dict) and result.get("id"):
            self.batch(result["id"], remember=False, result=result)
        elif request.name == "open-image":
            self.back()
            self.state.notice = "Audited PNG handed to the local viewer; no approval was recorded."
        else:
            heading = {"plan": "PUBLISHING PLAN", "organize": "MIGRATION PREVIEW", "apply": "ORGANIZATION RESULT",
                       "package": "APPROVED IMAGE PACK", "doctor": "LOCAL RUNTIME"}.get(request.name, "OPERATION RESULT")
            self.show(Page("result", heading, result=result, request=request), remember=False)

    def selected_row(self):
        rows = view_rows(self.state)
        if not rows: return None
        self.state.page.cursor = min(self.state.page.cursor, len(rows) - 1)
        return rows[self.state.page.cursor]

    def inspect_asset(self, row):
        report = execute(Request("inspect", self.state.root, {"image_id": row["id"]}))
        preview = make_preview(image_bytes(self.state.root, {"image_id": row["id"]}))
        self.show(Page("asset", "CLEAN IMAGE", image_id=row["id"], report=report, preview=preview))

    def inspect_item(self, row, batch_id):
        if row.get("status") != "READY_FOR_REVIEW":
            self.show(Page("result", "OUTPUT NEEDS ATTENTION", result=row))
            return
        preview = make_preview(image_bytes(self.state.root, {"batch_id": batch_id, "item_id": row["id"]}))
        self.show(Page("item", "EXACT OUTPUT REVIEW", batch_id=batch_id, item_id=row["id"], report=row, preview=preview))

    def reload_preview(self):
        p = self.state.page
        p.preview = make_preview(image_bytes(self.state.root, {"batch_id": p.batch_id, "item_id": p.item_id,
                                                              "kind": p.kind, "view": p.view}))

    def toggle_selection(self, row):
        if row["id"] in self.state.selected: self.state.selected.remove(row["id"])
        elif len(self.state.selected) < 200: self.state.selected.add(row["id"])
        else: self.state.notice = "A publishing selection is limited to 200 images."

    def move(self, amount):
        p = self.state.page
        if p.name in {"result", "help", "command"}:
            p.scroll = min(scroll_limit(self.state), max(0, p.scroll + amount))
            return
        count = len(fields_for(p)) + 1 if p.name == "form" else len(view_rows(self.state))
        p.cursor = max(0, min(max(0, count - 1), p.cursor + amount))

    def field_edit(self):
        p = self.state.page
        fields = fields_for(p)
        if p.cursor >= len(fields):
            return self.run_form(preview=p.action in {"publish", "riposte", "sort-riposte"})
        f = fields[p.cursor]
        if p.action == "riposte" and f.key == "input1" and p.values.get("input_paths"):
            return self.browse("inputs", "riposte", p.values["input_paths"])
        value = p.values.get(f.key, f.default)
        if f.kind == "bool": p.values[f.key] = not value; return
        if f.kind == "choice":
            p.values[f.key] = f.choices[(f.choices.index(value)+1) % len(f.choices)]
            return
        value = ", ".join(str(x) for x in value) if isinstance(value, (list, tuple)) else str(value)
        self.state.editor = Editor(f, value, len(value))

    def accept_editor(self):
        e = self.state.editor
        try:
            value = parse_value(e.field, e.value)
            if e.target == "picker-location":
                picker = self.state.page.result
                path = Path(value).expanduser().absolute()
                if not path.is_dir(): raise ValueError
                picker.enter(path)
                if picker.error: raise ValueError
                self.state.page.rows = picker.rows()
                self.state.page.cursor = 0
                self.state.page.values.pop("locations", None)
                self.state.editor = None
                return
            if e.target == "workspace":
                path = Path(value).expanduser().absolute()
                root_of(Request("list", path))
                self.state.root = path
                self.state.selected.clear(); self.state.stack.clear()
                self.state.page = Page()
                self.refresh()
                self.state.editor = None
                if self.pending_action:
                    action = self.pending_action; self.pending_action = None; self.action(action)
                return
            if e.target == "fps":
                self.state.presentation.fps = value
                self.preferences()
            else:
                self.state.page.values[e.field.key] = value
                if e.field.key.startswith("input"): self.state.page.values.pop("input_paths", None)
            self.state.editor = None
        except (RiposteError, OSError, ValueError): e.error = True

    def editor_key(self, key):
        e = self.state.editor
        if key.name == "escape": self.state.editor = None; self.pending_action = None; return
        if key.name == "enter": return self.accept_editor()
        if key.name in {"interrupt", "eof"}:
            self.state.editor = None
            if key.name == "eof": self.state.running = False
            return
        if key.name == "left": e.position = max(0, e.position-1)
        elif key.name == "right": e.position = min(len(e.value), e.position+1)
        elif key.name == "home": e.position = 0
        elif key.name == "end": e.position = len(e.value)
        elif key.name == "clear": e.value = ""; e.position = 0
        elif key.name == "backspace" and e.position:
            e.value = e.value[:e.position-1] + e.value[e.position:]; e.position -= 1
        elif key.name == "delete": e.value = e.value[:e.position] + e.value[e.position+1:]
        elif key.name in {"char", "paste"}:
            text = "".join(c for c in key.text if ord(c) >= 32 and ord(c) != 127)
            text = text[:4096-len(e.value)]
            e.value = e.value[:e.position] + text + e.value[e.position:]; e.position += len(text)
        e.error = False

    def freeze_motion(self):
        self.state.paused = not self.state.paused
        self.state.presentation.no_animation = self.state.paused
        if self.state.paused: self.state.frozen_time = time.monotonic()-self.started
        if self.state.page.name == "preferences": self.preferences()

    def cycle_theme(self):
        values = ("goks", "light", "mono", "dark")
        p = self.state.presentation
        p.theme = values[(values.index(p.theme)+1)%len(values)]
        if self.state.page.name == "preferences": self.preferences()

    def key(self, key: Key):
        try: self._key(key)
        except RiposteError as exc:
            self.show(Page("result", "OPERATION STOPPED", code=safe_code(exc.code), request=self.state.last_request))
        except Exception:
            self.show(Page("result", "OPERATION STOPPED", code="OPERATION_FAILED", request=self.state.last_request))

    def _key(self, key):
        if self.state.width < 72 or self.state.height < 24:
            if self.state.operation:
                if key.name in {"interrupt", "eof", "escape"} or key.text=="q":
                    self.state.operation.cancel(); self.state.exit_after_job=True
            elif key.name in {"interrupt", "eof"} or key.text=="q": self.state.running=False
            return
        if self.state.editor: return self.editor_key(key)
        p = self.state.page
        ch = key.text.lower() if key.name == "char" else ""
        if key.name == "f2": return self.freeze_motion()
        if key.name == "f3": return self.cycle_theme()
        if p.name == "job":
            if key.name in {"escape", "interrupt", "eof"} or ch == "q":
                self.state.operation.cancel()
                self.state.exit_after_job = key.name == "eof" or ch == "q"
                if not self.state.operation.cancellable: self.state.notice = "Commit continues safely; the terminal will wait."
            return
        if p.query_edit:
            if key.name in {"escape", "enter"}: p.query_edit = False
            elif key.name == "backspace": p.query = p.query[:-1]; p.cursor = 0
            elif key.name == "clear": p.query = ""; p.cursor = 0
            elif key.name in {"char", "paste"}: p.query = (p.query+key.text)[:200]; p.cursor = 0
            elif key.name in {"eof", "interrupt"}: p.query_edit = False
            return
        if p.name == "confirm":
            if key.name in {"escape", "interrupt"}: return self.back()
            if key.name == "eof": self.state.running = False; return
            if key.name == "backspace": p.values["confirmation"] = p.values["confirmation"][:-1]
            elif key.name == "clear": p.values["confirmation"] = ""
            elif key.name in {"char", "paste"}: p.values["confirmation"] = (p.values["confirmation"]+key.text)[:20]
            elif key.name == "enter":
                if p.values["confirmation"] == p.confirm_word:
                    return self.run(p.confirm_request)
                self.state.notice = "The confirmation word did not match. No write was started."
            return
        if key.name == "f1": return self.show(Page("help", "CONTEXTUAL HELP", result=contextual_help(self.state)))
        if key.name == "f4":
            request = p.request or self.state.last_request
            if p.name == "form":
                try:
                    request = self.request_from_form()
                    if request.name == "publish": request= Request("plan",request.root,request.values)
                    elif request.name in {"riposte", "sort-riposte"}: request = Request(request.name + "-plan", request.root, request.values)
                except RiposteError: self.state.notice = "Fill required fields to view the direct command."; return
            return self.show(Page("command", "DIRECT COMMAND", request=request))
        if key.name in {"eof", "interrupt"} or ch == "q": self.state.running = False; return
        if key.name == "escape" or ch == "0": return self.back()
        if key.name in {"up", "backtab"} or ch == "k": return self.move(-1)
        if key.name in {"down", "tab"} or ch == "j": return self.move(1)
        if key.name == "pageup": return self.move(-max(1, self.state.height-16))
        if key.name == "pagedown": return self.move(max(1, self.state.height-16))
        if key.name == "home": p.cursor = 0; p.scroll = 0; return
        if key.name == "end": return self.move(1000000)
        if ch == "/" and p.name in {"home", "library", "batches", "batch", "workshop"}: p.query_edit = True; return
        if p.name in {"home", "workshop"}:
            if ch.isdigit() and ch != "0":
                n = int(ch)-1
                if n < len(view_rows(self.state)):
                    p.cursor = n
                    row = self.selected_row()
                    return self.begin_action(row["key"])
            if key.name == "enter":
                row = self.selected_row()
                if row: return self.begin_action(row["key"])
        elif p.name == "picker": return self.picker_key(key)
        elif p.name == "library":
            row = self.selected_row()
            if (key.name == "enter" or ch == " ") and row: return self.toggle_selection(row)
            if ch == "a":
                rows = view_rows(self.state)
                if len(set(r['id'] for r in rows)|self.state.selected) > 200:
                    self.state.notice = "Selection exceeds 200. Narrow the search or choose individual images."; return
                self.state.selected.update(r["id"] for r in rows)
            elif ch == "n": self.state.selected.clear()
            elif ch == "i" and row: return self.inspect_asset(row)
            elif ch == "p": return self.action("publish")
        elif p.name == "asset":
            if key.name == "enter" or ch == " ": return self.toggle_selection(p.report)
            if ch == "v": return self.run(Request("open-image", self.state.root, {"image_id": p.image_id}))
            if ch == "p":
                if p.image_id not in self.state.selected: self.toggle_selection(p.report)
                return self.action("publish")
        elif p.name == "form":
            if ch == "b":
                fields = fields_for(p)
                if p.cursor < len(fields) and fields[p.cursor].kind == "path":
                    if fields[p.cursor].key.startswith("input"): return self.browse("inputs", "riposte", p.values.get("input_paths", ()))
                    if fields[p.cursor].key == "candidate":
                        self.state.notice = "Press Enter to paste the candidate image file path."; return
                    return self.browse("field", field=fields[p.cursor].key)
            if ch == "f" and p.action in {"publish", "riposte", "sort-riposte"}:
                focused = fields_for(p)[p.cursor].key if p.cursor < len(fields_for(p)) else None
                p.advanced = not p.advanced
                p.cursor = next((i for i, f in enumerate(fields_for(p)) if f.key == focused), 0)
                return
            if key.name == "enter" or ch == " ": return self.field_edit()
            if key.name in {"left", "right"}:
                fields = fields_for(p)
                if p.cursor < len(fields) and fields[p.cursor].choices:
                    f = fields[p.cursor]; index = f.choices.index(p.values[f.key])
                    p.values[f.key] = f.choices[(index + (1 if key.name == "right" else -1))%len(f.choices)]
            if ch == "v" and p.action == "organize": return self.run(Request("audit",self.state.root))
            if ch == "u" and p.action == "organize": return self.run(Request("undo-sort", self.state.root))
            if ch == "c" and p.action == "organize": return self.action("categories")
            if ch == "p" and p.action in {"publish", "riposte", "sort-riposte", "organize"}: return self.run_form(preview=True)
            if ch == "r": return self.run_form(preview=p.action=="organize")
        elif p.name == "batches":
            row = self.selected_row()
            if key.name == "enter" and row: return self.batch(row["id"])
        elif p.name == "batch":
            row = self.selected_row()
            if key.name == "enter" and row: return self.inspect_item(row, p.batch_id)
            if ch == "d": return self.show(Page("result", "BATCH REPORT", result=p.result, request=Request("publications",self.state.root,{"batch_id":p.batch_id})))
            if ch == "p": return self.run(Request("package", self.state.root, {"batch_id": p.batch_id}))
            if ch == "r": return self.action("resume", {"batch_id": p.batch_id})
        elif p.name == "item":
            if key.name == "enter": ch = "v"
            if ch in {"c", "b", "d"}:
                p.kind = {"c":"candidate", "b":"clean", "d":"difference"}[ch]
                return self.reload_preview()
            if ch == "t":
                views = list(TRANSFORMS); p.view = views[(views.index(p.view)+1)%len(views)]
                return self.reload_preview()
            if ch == "v": return self.run(Request("open-image", self.state.root, {"batch_id":p.batch_id,"item_id":p.item_id,"kind":p.kind,"view":p.view}))
            if ch == "a": return self.action("review", {"batch_id":p.batch_id,"item_ids":(p.item_id,)})
            if ch == "x": return self.confirm(Request("review", self.state.root, {"batch_id":p.batch_id,"item_ids":[p.item_id],"decision":"REJECTED"}), "REJECT", "Revoke this output's approval for future publishing packs.")
            if ch == "w": return self.action("handoff", {"batch_id":p.batch_id,"item_id":p.item_id})
        elif p.name == "result":
            request = p.request
            if ch == "t" and not p.code:
                views = ("overview", "details", "json")
                p.report_view = views[(views.index(p.report_view) + 1) % len(views)]
                p.scroll = 0
                return
            if key.name == "enter":
                if p.code: return self.back()
                if request and request.name == "organize": ch = "a"
                elif request and request.name == "undo-sort" and p.result.get("ready"): ch = "u"
                elif request and request.name in {"plan", "riposte-plan", "sort-riposte-plan"}: ch = "r"
                elif request and request.name == "package": return self.batches()
                else: return self.back()
            if ch == "a" and request and request.name == "organize":
                return self.confirm(Request("apply", request.root, request.values), "REPLACE", "Apply the displayed metadata-cleaning and calendar/size policy to this workspace.")
            if ch == "u" and request and request.name == "undo-sort" and p.result.get("ready"):
                return self.confirm(Request("undo-sort-apply", request.root, {"sort_id": p.result["sort_id"]}), "UNDO", "Restore original names and bytes from the last sort. Remove only its verified sorted copies.")
            if ch == "r" and request and request.name == "plan":
                return self.run(Request("publish", request.root, request.values))
            if ch == "r" and request and request.name == "riposte-plan":
                return self.run(Request("riposte", request.root, request.values))
            if ch == "r" and request and request.name == "sort-riposte-plan":
                return self.confirm(Request("sort-riposte", request.root, request.values), "REPLACE",
                                    "Replace verified sources during sorting, then protect the organized collection.")
            if ch == "b": return self.batches()
        elif p.name == "preferences":
            if key.name != "enter": return
            row = self.selected_row()
            if row["key"] == "workspace": return self.edit_workspace()
            if row["key"] == "theme": return self.cycle_theme()
            if row["key"] == "motion": return self.freeze_motion()
            if row["key"] == "fps":
                f = Field("fps", "Refresh ceiling", "int", 12, "4-30 terminal frames per second. Does not change processing speed.", minimum=4, maximum=30)
                self.state.editor = Editor(f, str(self.state.presentation.fps), len(str(self.state.presentation.fps)), target="fps")
            if row["key"] == "linear": self.state.switch_linear=True; self.state.running=False
            if row["key"] == "upgrade": return self.action("upgrade")
            if row["key"] == "browser":
                if not self.require_workspace("browser"): return
                self.state.handoff=["serve",str(self.state.root)]; self.state.running=False

    def shutdown(self):
        op=self.state.operation
        if op:
            op.cancel()
            while not op.done.is_set():
                try: op.done.wait(.1)
                except KeyboardInterrupt: op.cancel()
            op.join()
