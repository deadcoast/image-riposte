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
72 columns by 24 rows. All nine main actions, including Undo last sort, must be visible there, with a
textual focus marker and visible arrow/Enter hints. Wider screens may show the
wordmark and a description beside the menu. Number labels are keyboard shortcuts,
not stages in a required pipeline. Headers show the current task, never a global
choose/configure/protect/review/export sequence.

Use **image**, **folder**, and the actual operation name in interface copy.
Explain selection scope before showing a location browser. Keep destructive
replacement and visual acceptance explicit. See [UX-CONTRACT.md](UX-CONTRACT.md)
for the behavior contract and [evidence/menu-startup/README.md](evidence/menu-startup/README.md)
for tested scope. Earlier visual specifications remain historical design context.
