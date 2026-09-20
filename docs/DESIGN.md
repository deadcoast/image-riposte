# RIPOSTE terminal design

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
