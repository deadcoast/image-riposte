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
    if page.action in {"publish", "riposte", "sort-riposte"} and not page.advanced:
        return tuple(f for f in fields if f.key in {"input1", "date_mode", "discard_sidecars", "edges", "epsilon", "preserve_white", "device", "vae1"})
    return fields


def hints(state):
    p=state.page
    if state.editor:return [Hint("Enter","Save","Validate and save this field; it does not run an operation."),Hint("Esc","Discard","Leave the field unchanged."),Hint("Ctrl+U","Clear","Clear this field's input.")]
    if p.query_edit:return [Hint("Enter","Finish search","Keep the filter and return to the filtered list."),Hint("Esc","Finish search","Close search input without executing anything."),Hint("Ctrl+U","Clear filter","Show all rows again.")]
    rows={
        "home":[Hint("Enter","Open","Choose Sort, RIPOSTE, or Sort + RIPOSTE. Arrows or visible numbers open an action."),Hint("/","Find","Filter the action list."),Hint("q","Quit","Leave RIPOSTE.")],
        "library":[Hint("Enter","Select","Add or remove the focused image from your publishing selection."),Hint("i","Inspect","Open the focused image without changing your selection."),Hint("p","Protect","Configure protection for selected images."),Hint("/","Find","Filter dates, canonical names or image IDs."),Hint("a","Select visible","Add every visible image, up to the selection limit."),Hint("n","Clear selection","Remove selected images from the current selection; files are unchanged.")],
        "asset":[Hint("Enter","Select","Toggle this illustration in your publishing selection."),Hint("p","Protect","Carry this image and the current selection into protection."),Hint("v","Open PNG","Open audited full-resolution pixels in your local viewer.")],
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
        if p.action in {"publish","riposte","sort-riposte","organize"}:controls.append(Hint("p","Preview","Read-only plan; no images are written."))
        if p.action=="organize":controls.append(Hint("v","Audit","Verify existing clean files and workspace organization."))
        elif p.action=="sort-riposte":controls.append(Hint("r","Preview","Preview both stages before confirming source replacement."))
        else:controls.append(Hint("r","Run","Run these settings. Review acceptance still requires its separate confirmation."))
        if p.action in {"publish","riposte","sort-riposte"}:controls.append(Hint("f","Basic" if p.advanced else "Advanced","Show additional inputs, engine, quality and extra-model fields; no setting is discarded when collapsed."))
        controls.append(Hint("Left/Right","Choice","Cycle a focused choice field; other fields use Enter."))
        return controls+[Hint("Esc","Back","Return without starting another action.")]
    if p.name=="result":
        name=p.request.name if p.request else ""
        primary=(Hint("Enter","Apply policy","Open the explicit REPLACE confirmation; no write from a single Enter.") if name=="organize" and not p.code
                 else Hint("Enter","Confirm both stages","Open REPLACE confirmation before sorting and protection.") if name=="sort-riposte-plan" and not p.code
                 else Hint("Enter","Start protection","Run this planned selection with its configured models.") if name in {"plan","riposte-plan"} and not p.code
                 else Hint("Enter","Batches","Open publishing batches.") if name=="package" and not p.code
                 else Hint("Enter","Return","Return to the previous screen."))
        return [primary,Hint("t","Report view","Cycle Overview, complete Details, and syntax-coloured JSON."),Hint("Up/Down","Scroll","Scroll the selected report view; Page Up/Down move a page."),Hint("b","Batches","Open publishing batches."),Hint("Esc","Back","Return to the previous screen.")]
    controls=rows.get(p.name,[])
    if p.name not in {"home","confirm","help","command"}:controls=controls+[Hint("Esc","Back","Return to the previous screen.")]
    return controls


def context(state):
    p=state.page
    if state.editor:return state.editor.field.help
    if p.name=="form":
        fields=fields_for(p)
        return fields[p.cursor].help if p.cursor<len(fields) else BY_KEY[p.action].summary
    if p.name=="library":return f"{len(state.selected)} selected. Enter selects; i inspects. Selection never changes files."
    if p.name=="item":return "Review actual pixels before approval. An ASCII preview is not a quality decision."
    if p.name=="result":return "Overview explains the result; Details preserves every field; JSON is optional."
    if p.name=="batch":return "Ready means generated, not approved. Only approved images enter a pack."
    return ""


def contextual_help(state):
    entries=list(hints(state))
    seen={h.key for h in entries}
    entries.extend(h for h in GLOBAL if h.key not in seen)
    return {"screen":state.page.title, "context":context(state),
            "controls":[{"key":h.key,"label":h.label,"explanation":h.explanation} for h in entries]}
