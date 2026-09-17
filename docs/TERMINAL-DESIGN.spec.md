# RIPOSTE / MIVIN terminal design specification / 0.5

The 0.5 terminal revision retains the architectural, motion and consent contracts
below. Its foreground-only palette, semantic reports and contextual controls
supersede the earlier colour and selection details. See [REVISION-v05.md](REVISION-v05.md)
and [PATCH-v05-MERGE.md](PATCH-v05-MERGE.md) for design provenance and current verification.

## Mandate

A constrained medium is not a reduced design ambition. The product is artwork security; the interface makes the real actions discoverable, coherent and enjoyable without inventing processing, hiding destructive effects or making the supporting workshop the application. Aesthetic motion is delivered product work, not a generic spinner used to imply completeness.

This is a project-specific implementation of the user's MIVIN terminal brief. It uses the visual principles in the retrieved MIVIM visual-development specification (authored material, distinct operational compositions, discoverable actions, actual events, pause/linear alternatives), without importing that other application's native-agent or repository-management semantics.

## Authored direction: COUNTERSTROKE

A quiet editorial working surface carries a depth-resolved set of hinged raster plates. The geometry opens and closes slightly, travelling illumination reveals its lattice, and an incoming stroke is reflected away from the plates. Those details give RIPOSTE its own terminal identity while referring to image-integrated interference rather than an impenetrable lock. The geometry is decoration, never an efficacy claim.

The renderer is **ordinary ASCII plus Rich colour/style**. No braille-cell requirement, Unicode box border, web canvas, emoji, video playback or copied font geometry is necessary. The same cell data drives the Rich stream, linear text and development captures. The image preview is an actual sampled raster expressed in coloured ASCII; it cannot establish visual approval at source resolution.

`material.py` inverse-projects each character cell onto three affine image planes and resolves overlap with a cell depth buffer. Projected outline segments establish a silhouette. Analytic hinge/light/trajectory phases share caller-supplied time. This is an authored integration of familiar graphics methods, not a claim of a new rendering theorem or of reproducing an outside protection algorithm.

## Reference use

Uizze's selected **Sauce Labs** reference supplied useful principles: a continuous dark surface, mint emphasis, monospaced identity and a connected process instead of independent dashboard cards. The newly returned **Hex** reference contributed editorial rules and small technical annotations; its landing-page composition and light marketing hero were not copied into the terminal.

- Sauce Labs: https://uizze.com/packs/d271a6c4-942f-4abf-a3de-66795f15f031
- Hex: https://uizze.com/packs/3e32db74-a61d-4e72-93b8-1fb949af2c00

The requested **Frontend Design Premium** and **Design Partner** names were searched in the plugin directory. Exact matching callable plugins were not returned. No contribution from either is fabricated; unrelated plugins were not installed as substitutes. No third-party screenshot or font file is bundled.

## Composition contracts

| State | Delivered composition | Forbidden shortcut |
|---|---|---|
| Home | Quiet identity/material band; actual counters; seven task actions; focused action/effect | Hero animation repeated above every screen, fake security statistics |
| Library | Date/size/dimension rows, selection marks, search, full clean ID | Extension-based folders, raw-source names or metadata history |
| Artwork | Large character preview with date and native dimensions | Calling the character preview full-resolution review |
| Protection | Essential fields first; `f` exposes the full recipe without discarding values; per-field explanation; current-session model choices | Inaccessible models, guessed settings, a fake Run button |
| Migration | Read-only results then a visibly different source-replacement boundary | Auto-apply, raw backups, Enter-only destructive confirmation |
| Active operation | Actual stage/counts/item/time and bounded event tape; separate aesthetic activity trace | Percentage inferred from animation or elapsed time |
| Batch/output | Committed output states, exact-byte image access, review, resume, pack | Automatic approval based on a proxy score |
| Result/command | Semantic Overview, complete Details and explicit JSON views, or a quoted equivalent command | Excerpt represented as full result; shell evaluation |
| Settings/help | Discoverable palette/motion/workspace/browser options; shared contextual key hints and F1 help | Memorized hidden shortcuts as the only access |
| Workshop | Secondary helper list, all inherited operations retained | Making research instrumentation the product's main path |

## Layout and colour

The whole surface uses a shared baseline, gutters and spacing. ASCII rules delimit working regions without surrounding every value in a card. Focus combines a `>` marker and text weight; it is not conveyed by colour alone. Source-replacement warnings use warning colour plus explicit language. Every cell, preview, cursor and animation uses the host terminal's default background; reverse video and explicit background fills are excluded.

The default `goks` foreground palette retains the twelve supplied tokens and their intentional numbering gaps. Light, monochrome and dark are foreground alternatives; none changes the terminal wallpaper, opacity or background. ASCII preview tones may be lifted for legibility, without changing image pixels. `NO_COLOR` removes colour while preserving text/navigation. The designed range is 72×24 through 240×100 character cells, with specific inspection at 79×24, 100×34 and 132×46. Too-small screens do not permit hidden write actions; resize or select the linear mode.

## Motion contracts

The terminal is usable on its first frame. There is no artificial load delay, unskippable splash or authentication barrier. Animation is caller-time-driven and repeatable; F2 freezes it without freezing processing, counts, elapsed time or input. F3 changes palette without discarding selection or form state. Refresh is capped, default 12 fps, configurable 4–30. No background animation process survives exit.

COUNTERSTROKE occupies the home identity region and, when there is room, the active-operation margin. It is not placed over the illustration or the editable form. A liveness trail during operations is labeled activity, not progress; the adjacent engine numerator/denominator is only rendered when the engine actually supplies it. A new engine phase clears a previous phase's count.

## Interaction and privacy

Enter selects a library image; `i` inspects it without changing the selection.
Space remains a compatibility alias. A shared hint registry supplies footers and
contextual F1 help. `t` switches report views; complete Details and explicit JSON
retain fields omitted from an operation summary. Machine JSON remains separate.

Typer and the native/linear interfaces produce the same allowlisted `Request`; `service.execute` invokes the actual existing backend. No command string is evaluated. F4 quotes the corresponding PowerShell command for inspection, and long commands scroll. A valid ID, range, model selection and backend checkpoint retain their existing enforcement.

Source replacement requires an explicit Apply request or the interactive literal REPLACE. Acceptance requires the actual review booleans and an interactive literal ACCEPT; a viewer handoff does not set them. Source/model paths are transient inputs, not terminal history. Error rendering uses sanitized codes. Bracketed paste is bounded and treated as data, unknown control sequences are consumed as units, and shell/terminal-control injection is not a navigation mechanism.

A non-daemon, foreground-owned worker runs slow operations while the UI remains responsive. Cooperative operations accept checkpoint cancellation. Source, review and package commits wait rather than being abandoned. The raw keyboard context, Rich screen, signal handlers and workers all have cleanup paths. SIGKILL and power loss are explicitly outside Python cleanup guarantees.

## Actual implementation map

| Concern | Module |
|---|---|
| Typed command contracts / entry | `cli.py` |
| Shared allowlisted operations | `terminal/service.py` |
| Action/field schema and quoted command generation | `terminal/actions.py` |
| Session-only navigation and editor state | `terminal/state.py` |
| Pure cell surface / Rich segments | `terminal/surface.py` |
| Original geometry and activity material | `terminal/material.py` |
| Distinct task scenes | `terminal/render.py` |
| Foreground palette tokens | `terminal/palette.py` |
| Shared hints, contextual help and field disclosure | `terminal/interaction.py` |
| Semantic reports, complete field trees and JSON spans | `terminal/reports.py` |
| Input validation, state transitions, write boundaries | `terminal/controller.py` |
| Foreground-owned operation lifecycle | `terminal/jobs.py` |
| Native keys, bounded paste, cooked-mode restoration | `terminal/keyboard.py` |
| Safe SIGTERM ownership | `terminal/signals.py` |
| Actual-image ASCII sampler | `terminal/preview.py` |
| Native/linear event loops | `terminal/app.py` |
| Rich human / JSON automation output | `terminal/output.py`, `terminal/help.py` |

## Technical references

Consulted official interfaces rather than a copied terminal template:

- Typer context/callback entry: https://typer.tiangolo.com/tutorial/commands/context/
- Typer help and command grouping: https://typer.tiangolo.com/tutorial/commands/help/
- Typer parameter reference: https://typer.tiangolo.com/reference/typer/
- Rich Live screen and refresh lifecycle: https://rich.readthedocs.io/en/latest/live.html
- Rich console/render interface: https://rich.readthedocs.io/en/latest/console.html

## Evidence interpretation

PNG/GIF captures in `evidence/` are generated from the same ASCII cell renderer used by the application. They are not native Windows screenshots. `terminal-session.cast` is a separate recording of the actual running Rich application in a POSIX pseudo-terminal. Developer fixtures are original geometric illustrations, not user art or protection-efficacy evidence. The installed default renderer never loads these capture files to animate the application.
