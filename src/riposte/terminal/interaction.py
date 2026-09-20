"""Single vocabulary for visible controls, contextual help and field disclosure."""
from __future__ import annotations
from dataclasses import dataclass
from .actions import BY_KEY

@dataclass(frozen=True)
class Hint:
    key: str
    label: str
    explanation: str

GLOBAL = (
    Hint("F1", "Help", "Explain the controls and focused action on this screen."),
    Hint("F2", "Motion", "Pause or resume decorative ASCII motion; processing continues."),
    Hint("F3", "Palette", "Cycle goks, light, monochrome and dark foregrounds; background stays terminal-owned."),
    Hint("F4", "Command", "Inspect the equivalent direct command. Nothing is executed by viewing it."),
    Hint("q", "Quit", "Exit menus; wait for any source-owning operation to stop safely."),
)

def fields_for(page):
    fields = BY_KEY[page.action].fields
    if page.action == "riposte" and page.values.get("input_paths"):
        fields = tuple(f for f in fields if f.key not in {"input2", "input3", "input4"})
    if page.action in {"publish", "riposte", "sort-riposte"} and not page.advanced:
        return tuple(f for f in fields if f.key in {"input1", "date_mode", "discard_sidecars", "categories", "assignments", "edges", "epsilon", "preserve_white", "device", "vae1"})
    return fields


def hints(state):
    p=state.page
    if state.editor:
        primary = Hint("Enter", "Preview", "Use this folder and run the requested read-only sort preview.") if state.editor.target == "sort-path" and p.values.get("pending_sort") else Hint("Enter","Save","Validate and save this field; it does not run an operation.")
        return [primary,Hint("Esc","Discard","Leave the field unchanged."),Hint("Ctrl+U","Clear","Clear this field's input.")]
    if p.query_edit:return [Hint("Enter","Finish search","Keep the filter and return to the filtered list."),Hint("Esc","Finish search","Close search input without executing anything."),Hint("Ctrl+U","Clear filter","Show all rows again.")]
    if p.name == "sorter":
        return [Hint("Enter", "Choose", "Run the highlighted action; arrows move focus."),
                Hint("1/2/3", "Choose", "Sort / Dry Run / Enter Path."),
                Hint("g", "Enter Path", "Paste a folder without browsing."),
                Hint("b", "Browse", "Choose a folder with the keyboard."),
                Hint("u", "Undo", "Preview the last sort's recovery."),
                Hint("Esc", "Back", "Return to the main menu.")]
    rows={
        "picker":[Hint("Enter","Open / choose","Open a folder, toggle a file, or confirm the highlighted selection row."),Hint("Up/Down","Move","Move the highlight."),Hint("Space","Select","Select or unselect a file or folder for protection."),Hint("s","This folder","Select or unselect the current folder for protection."),Hint("Backspace","Parent","Browse the parent folder."),Hint("l","Locations","Browse home, Pictures, and drives."),Hint("g","Go to path","Optionally type or paste a folder location."),Hint("Esc","Cancel","Return without starting an operation.")],
        "home":[Hint("Enter","Open","Choose Riposte Sorter, RIPOSTE, or Sort + RIPOSTE. Arrows or visible numbers open an action."),Hint("Arrows","Move","Move the highlight; Enter opens the selected action."),Hint("1-9/w","Choose","Open the numbered action, or w for expert protection helpers."),Hint("/","Find","Filter the action list."),Hint("q","Quit","Leave RIPOSTE.")],
        "library":[Hint("Enter","Select","Add or remove the focused image from your publishing selection."),Hint("i","Inspect","Open the focused image without changing your selection."),Hint("p","Protect","Configure protection for selected images."),Hint("/","Find","Filter dates, canonical names or image IDs."),Hint("a","Select visible","Add every visible image, up to the selection limit."),Hint("n","Clear selection","Remove selected images from the current selection; files are unchanged.")],
        "asset":[Hint("Enter","Select","Toggle this image in your publishing selection."),Hint("p","Protect","Carry this image and the current selection into protection."),Hint("v","Open PNG","Open audited full-resolution pixels in your local viewer.")],
        "batches":[Hint("Enter","Open batch","See its output queue, approvals and blocked items."),Hint("/","Find","Filter the batch list.")],
        "batch":[Hint("Enter","Review output","Inspect the focused output; no approval is implied."),Hint("p","Package","Write a ZIP containing approved PNGs only."),Hint("r","Resume","Reload matching models and continue unfinished outputs."),Hint("d","Batch report","Read the complete batch result in the authored report viewer."),Hint("/","Find","Filter output states and IDs.")],
        "item":[Hint("Enter","Open PNG","View exact audited pixels; this does not record approval."),Hint("a","Approve","Open the explicit visual-approval form."),Hint("x","Reject","Revoke approval for future packs."),Hint("c/b/d","Image mode","Candidate / baseline / amplified difference."),Hint("t","Transport","Cycle real codec and resize previews."),Hint("w","Workshop","Pass this exact output to optional expert helpers.")],
        "workshop":[Hint("Enter","Configure","Configure the focused optional helper."),Hint("/","Find","Search helper actions.")],
        "preferences":[Hint("Enter","Change","Change the focused session setting." )],
        "confirm":[Hint("Enter","Confirm word","Only an exact confirmation word starts this write."),Hint("Esc","Cancel","No operation starts.")],
        "help":[Hint("Up/Down","Scroll","Read all help sections."),Hint("Esc","Return","Return to the prior screen.")],
        "command":[Hint("Up/Down","Scroll","Read the complete quoted command."),Hint("Esc","Return","No shell command is executed.")],
    }
    if p.name=="job":
        return [Hint("Esc","Request stop","Stop at a safe engine checkpoint; source/record commits finish before exit.")]
    if p.name=="form":
        fields=fields_for(p)
        if p.cursor<len(fields):
            f=fields[p.cursor]
            primary=Hint("Enter","Toggle" if f.kind=="bool" else "Change" if f.kind=="choice" else "Edit",f.help)
        else:primary=Hint("Enter","Preview" if p.action in {"publish","riposte","sort-riposte","organize"} else "Run",BY_KEY[p.action].summary)
        controls=[primary]
        if p.cursor<len(fields) and fields[p.cursor].kind=="path":controls.append(Hint("b","Browse","Choose this location in the file/folder browser."))
        if p.action in {"publish","riposte","sort-riposte","organize"}:controls.append(Hint("p","Preview","Read-only plan; no images are written."))
        if p.action=="organize":
            controls.append(Hint("g","Enter Path","Change the image folder while keeping these settings."))
            controls.append(Hint("s","Saved rules","Inspect or draft reusable categories; saving requires SAVE confirmation."))
            controls.append(Hint("c","Categories","Discover recurring filename terms and review category groups without changing files."))
            controls.append(Hint("u","Undo last sort","Preview recovery before an explicit UNDO confirmation."))
            controls.append(Hint("v","Audit","Verify existing clean files and workspace organization."))
        elif p.action=="sort-riposte":controls.append(Hint("r","Preview","Preview both stages before confirming source replacement."))
        elif p.action=="categories":
            controls.append(Hint("r","Discover / review","Read filename suggestions and category matches. No files or rules are saved."))
            controls.append(Hint("s","Saved rules","Open reusable category rules after reviewing suggestions."))
        else:controls.append(Hint("r","Run","Run these settings. Review acceptance still requires its separate confirmation."))
        if p.action in {"publish","riposte","sort-riposte"}:controls.append(Hint("f","Basic" if p.advanced else "Advanced","Show additional inputs, engine, quality and extra-model fields; no setting is discarded when collapsed."))
        controls.append(Hint("Left/Right","Choice","Cycle a focused choice field; other fields use Enter."))
        return controls+[Hint("Esc","Back","Return without starting another action.")]
    if p.name=="result":
        name=p.request.name if p.request else ""
        if p.code:
            controls = [Hint("Enter", "Return", "Return without starting another operation.")]
            if p.values.get("sorter_mode"): controls.append(Hint("g", "Enter Path", "Return to Riposte Sorter and choose another folder."))
            return controls + [Hint("Esc", "Back", "Return to the previous screen.")]
        primary=(Hint("Enter","Confirm undo","Open the explicit UNDO confirmation; conflicts block restoration.") if name=="undo-sort" and not p.code and p.result.get("ready")
                 else Hint("Enter","Confirm sort","Open the explicit REPLACE confirmation; no write from a single Enter.") if name=="organize" and not p.code and (not p.request.values.get("categories") or p.result.get("ready"))
                 else Hint("Enter","Confirm both stages","Open REPLACE confirmation before sorting and protection.") if name=="sort-riposte-plan" and not p.code
                 else Hint("Enter","Start protection","Run this planned selection with its configured models.") if name in {"plan","riposte-plan"} and not p.code
                 else Hint("Enter","Batches","Open publishing batches.") if name=="package" and not p.code
                 else Hint("Enter","Return","Return to the previous screen."))
        if p.values.get("sorter_mode") == "dry-run":
            primary = Hint("Enter", "Return", "Dry Run changes nothing. Return to Riposte Sorter to choose Sort.")
        elif p.values.get("sort_changes") is False:
            primary = Hint("Enter", "Return", "This preview has no changes to apply. Return to Riposte Sorter.")
        saving = [Hint("s", "Save rules", "Confirm SAVE to persist this reviewed replacement without moving files.")] if name == "category-rules" and not p.code and p.result.get("status") == "DRAFT" else []
        if p.values.get("sorter_mode"):
            if name == "organize" and not p.code:
                saving.append(Hint("w", "Full Sort Workshop", "Adjust this preview's settings; inspect blockers before previewing again."))
            saving.append(Hint("g", "Enter Path", "Return to Riposte Sorter and choose another folder."))
            return [primary,*saving,Hint("t","Report view","Cycle Overview, complete Details, and syntax-coloured JSON."),Hint("Up/Down","Scroll","Scroll the report; Page Up/Down move a page."),Hint("Esc","Back","Return to Riposte Sorter.")]
        return [primary,*saving,Hint("t","Report view","Cycle Overview, complete Details, and syntax-coloured JSON."),Hint("Up/Down","Scroll","Scroll the selected report view; Page Up/Down move a page."),Hint("b","Batches","Open publishing batches."),Hint("Esc","Back","Return to the previous screen.")]
    controls=rows.get(p.name,[])
    if p.name=="picker":
        controls=[h for h in controls if p.result.multiple or h.key not in {"Space","s"}]
        if not p.result.multiple:
            controls.insert(1, Hint("s", "Use folder", "Choose the highlighted folder directly, or the current folder on Use this folder."))
        cancel=next(h for h in controls if h.key=="Esc")
        controls.remove(cancel);controls.insert(3 if p.result.multiple else 2,cancel)
        path = next(h for h in controls if h.key == "g")
        controls.remove(path); controls.insert(3 if not p.result.multiple else 4, path)
        return controls
    if p.name not in {"home","confirm","help","command"}:controls=controls+[Hint("Esc","Back","Return to the previous screen.")]
    return controls


def context(state):
    p=state.page
    if state.editor:return state.editor.field.help
    if p.name=="home":
        from .render import view_rows
        rows=view_rows(state)
        return rows[min(p.cursor,len(rows)-1)]["summary"] if rows else "No matching actions."
    if p.name=="picker":return "Selection is read-only. Enter on the first row confirms your choice."
    if p.name=="sorter":return "Subfolders included; float storage excluded. Sort previews first."
    if p.name=="form":
        fields=fields_for(p)
        return fields[p.cursor].help if p.cursor<len(fields) else BY_KEY[p.action].summary
    if p.name=="library":return f"{len(state.selected)} selected. Enter selects; i inspects. Selection never changes files."
    if p.name=="item":return "Review actual pixels before approval. An ASCII preview is not a quality decision."
    if p.name=="result":
        if p.values.get("sorter_mode") and not p.code:
            if p.request.name == "organize" and not p.result.get("ready"): return "Blocked. Nothing changed. Review blockers; w opens the workshop."
            if p.values.get("sort_changes") is False: return "Nothing to sort. No files changed. Enter returns to the sorter."
            if p.values["sorter_mode"] == "dry-run": return "Dry Run only. No files changed. Enter returns to the sorter."
        return "Overview explains the result; Details preserves every field; JSON is optional."
    if p.name=="batch":return "Ready means generated, not approved. Only approved images enter a pack."
    return ""


def contextual_help(state):
    entries=list(hints(state))
    seen={h.key for h in entries}
    entries.extend(h for h in GLOBAL if h.key not in seen)
    return {"screen":state.page.title, "context":context(state),
            "controls":[{"key":h.key,"label":h.label,"explanation":h.explanation} for h in entries]}
