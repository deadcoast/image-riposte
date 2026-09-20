# RIPOSTE terminal design

Recovery presentation uses `recovery.py` and `static/recovery.js` with one packaged
`static/recovery-catalog.json`. Both consumers expose the same explanation, safe
next action and sanitized machine code; operation families refine unknown-failure
and cancellation advice. No guidance action invokes a write. Error screens keep
the code visible while Up/Down and Page Up/Down scroll the explanation at 72×24.
The browser keeps dismissible errors visible, including inside the active dialog;
informational category outcomes stay in file rows and never become blockers.

RIPOSTE is a local image protection and organization tool. People may protect a
few images, sort a folder after additions, or explicitly run both operations.
The main menu presents these independent choices before asking for locations.

The established Rich ASCII identity remains: the RIPOSTE wordmark, restrained
COUNTERSTROKE motion, fixed text positions, foreground-only palettes, and a host
owned terminal background. `terminal/surface.py` owns palette values;
`terminal/material.py` owns decorative motion. Terminal monospace is the font.
No new font, component toolkit, theme configuration, or runtime dependency is
introduced. F2 and `--no-animation` disable decorative motion.

`terminal/render.py` owns all screen layouts. The minimum interactive viewport is
72 columns by 24 rows. All main actions, including Undo last sort and the `w`
expert Workshop shortcut, must be visible there, with a
textual focus marker and visible arrow/Enter hints. Wider screens may show the
wordmark and a description beside the menu. Number labels are keyboard shortcuts,
not stages in a required pipeline. Headers show the current task, never a global
choose/configure/protect/review/export sequence.

Use **image**, **folder**, and the actual operation name in interface copy.
Explain selection scope before showing a location browser. Keep destructive
replacement and visual acceptance explicit. See [UX-CONTRACT.md](UX-CONTRACT.md)
for the behavior contract and [evidence/menu-startup/README.md](../evidence/menu-startup/README.md)
for tested scope. Earlier visual specifications remain historical design context.

## Riposte Sorter / 2026-09-19

The default first action opens one stable screen: selected folder, **1. Sort**,
**2. Dry Run**, **3. Enter Path**, followed by the date/media/category/size route.
The category segment is explicitly "if found". Missing, ambiguous or unknown
categories must never look like required setup; the ordinary route stays usable.
Local filename proposals belong in the same preview as saved-rule matches.
Show their evidence as heuristic, preserve established category names, and let
uncertain files take the ordinary route. Optional discovery groups reuse existing
rule-draft controls. Calendar navigation uses actual years and English months.
The existing configurable flow is **Full Sort Workshop**. Keep the same terminal
monospace, foreground palette and explicit `>` focus marker. Numbering identifies
actions, not required stages. Path input starts empty so a pasted path cannot be
appended accidentally. Static screens repaint on input or resize; queued keys
are drained in bounded bursts independently of decorative frame rate. Folder
activation consumes the same row snapshot that was displayed. No new dependency
or palette token is needed. Runtime palette values live in `terminal/palette.py`;
`surface.py` applies them to cells. Native Windows evidence and production-cell
captures are retained under `evidence/sorter-menu/`.

The polish pass keeps actions in fixed positions and uses explicit state text:
READ ONLY, BLOCKED, or NO CHANGES. Failed paths retain editable input and show
correction text with stable Enter/Esc controls. Confirmation shows its bound
folder and complete operation warning at 72x24. Long paths retain their start
and end when space requires abbreviation. The sorter also discloses that
`_float_` / `__float__` storage is excluded while image RIPOSTE remains available.
See `evidence/terminal-polish/` for actual tested scope and cell-render captures.


## Browser sorting extension

The browser retains its green local-workbench identity. `static/style.css` owns
runtime tokens (`--text`, `--muted`, `--line`, `--mint`, `--amber`, `--mono`);
category controls consume those tokens directly. No token generator or duplicate
theme is introduced. `static/category-sort.js` owns the sorting dialog's draft,
preview and consent state and uses `app.js` transport, job and feedback owners.
Native dialog/select behavior is intentional. Details disclosures keep rule
editing and undo secondary to reviewing exact destinations. Full paths wrap;
the dialog scrolls within the viewport. See the maintained canonical map in
`docs/UX-CONTRACT.md`. These documents intentionally live under `docs/`, following
the user's repository move; a root duplicate must not be recreated for tooling.

## Duplicate Finder / 2026-09-20

The independent finder enters from terminal **d** or browser **Duplicate Finder**.
Its one settings screen leads to the finding list. Source selection never starts
sorting or protection. Terminal main-menu numbering remains 1–9, with d and w
for the two additional actions, all visible at 72×24. Terminal reports reuse the
existing foreground palette, explicit focus marker, paged row window and help.

The browser keeps the current green workbench tokens and native form controls.
`static/duplicates.js` owns scan submission, filters, detail/member paging,
stale-response rejection and explicit report downloads. Shared authenticated
transport, image lifecycle and job cancellation remain in `app.js`. On this view,
the unrelated sorting CTA and protection workflow strip are hidden; / focuses
the duplicate path search. No new font, dependency, modal or theme is introduced.

Counts distinguish exact groups from pair relationships. Paths wrap as literal
text; matching evidence and provenance remain available without JSON-only review.
The paired media layout stacks below 600px and list/detail columns stack below
1050px. Preview dimensions reserve space and replaced/failed images release their
object URLs. Scan settings retain values after failure. Inline validation focuses
the first invalid number; findings remain useful when a scan has coverage gaps.
Native selects belong to the platform. The application owns form validation
(`novalidate`); minimum-score filtering and errors remain in the finder view.

The English local desktop audience and existing type scale remain the target.
Actual Chromium screenshots at 1100×900 and 390×844, keyboard/state fixtures and
the live six-image server run are in `evidence/duplicates/`. These do not establish
screen-reader acceptance, Japanese IME behavior or independent human usability.

## Sorting scan progress / PAC-035

The sorting dialog shows the current job phase and Cancel beside its inspection
controls. Counts appear only when the scanner supplies a bounded total; there is
no estimated percentage for unknown work. The same job drives the shared footer.
Cancel remains reachable inside the modal by keyboard and on narrow screens.
Cancellation preserves form inputs and requires a new inspection before consent.
Changing settings or closing the dialog invalidates earlier inspection receipts.
Replacement, saved-rule writes and undo commits finish without interruption.
The footer's version comes from the running server's state response.

## Guided categories / PAC-037

The sorting dialog keeps the existing green workbench palette, native controls
and shared job feedback. Each category is a fieldset with paired name/folder
fields, matching/excluded phrase lists and a numeric priority. It stacks into
one column below 600px. Folder identity stays explicit beside the editable name;
renaming a loaded category never silently renames its folder. Draft state appears
above the rows. Reload uses an inline Keep draft / Discard draft and load choice.
Review and Save remain separate actions; saved rules alone drive sort previews.

Per-file selectors live beside the exact destination, with 50 files per page.
The dialog owns the outer scroll and the existing file list owns its bounded
scroll. Pending selections remain in memory across pages and dialog closes.
Sensitive paths, matching phrases and choices are never put in browser storage
or URLs. Native dropdown geometry is platform owned, matching the date selector.
Old destinations are visibly marked after settings change. No new theme, font,
component library, runtime dependency or mandatory sorting step is introduced.
