# RIPOSTE 0.5.0 / reconstructed terminal revision

This is the design/provenance record supplied inside the shelved 0.5.0 archive.
Its historical execution claims describe that archive, not this working checkout.
See [selective integration](PATCH-v05-MERGE.md) for current merge decisions and checks.

## Source provenance

The failed post-0.4 response did not leave a recoverable modified source tree in the mounted files or the file lookup. This release is **newly reconstructed from the actual delivered 0.4.0 ZIP**, implementing the requested design changes. It is not described as recovery of missing source bytes. The previous archive and original terminal source/evidence are preserved separately; its 667 inherited test cases remain unchanged.

## Delivered changes

- Terminal-owned backgrounds in every Rich cell: panels, focus rows, prompts, animation, image previews, reports and direct-command activity. Explicit fill arguments cannot paint the host. No reverse-video selection. Foreground carets and ASCII selection markers remain visible. Rich's default background is used; RIPOSTE does not change terminal wallpaper, opacity or background settings.
- `goks` (greys of knights sunset), the exact twelve user-provided tokens, is the default. The unspecified `gokn3` and `gokn10` are not invented. Dark grey tokens remain available for low-emphasis foreground uses. Light/monochrome/dark are foreground-only alternatives.
- Dedicated migration, audit, publishing-plan, batch, archive, runtime and image reports. Human direct output and the interactive report viewer share one semantic renderer. Unknown/expert data uses a readable field tree, not an unstyled JSON dump.
- The report viewer has Overview, complete Details, and syntax-coloured JSON views. `t` cycles views; Arrow/Page/Home/End navigation retains complete data. Machine `--json` output remains unchanged and separate.
- A single action-hint registry supplies the footer and contextual F1 help. Enter selects an image; `i` inspects it. Space remains only an optional compatibility alias. Enter on a migration report opens REPLACE confirmation, never starts deletion alone.
- Essential protection fields appear first. `f` expands all engine/quality/model controls without discarding hidden values. Contextual help explains the focused field rather than displaying a generic permanent tooltip.
- Main publishing, organization, model and browser backends are preserved. This is an interface revision and introduces no new AI-efficacy claim.

## Visual output

The evidence renderer draws actual application cells. PNGs on dark/light canvases simulate a host terminal background; the application itself does not set those backgrounds. The additional RGBA PNG has no background pixels. The animated GIF is a capture of the live ASCII geometry, not a file played inside the app.

ASCII artwork glyphs are tone-lifted on dark foreground palettes so dark ink remains legible without a painted white rectangle. The original PNG and protection pixels are untouched; full-resolution review remains a local image-viewer action.

## Relevant implementation references

Rich documents the terminal-default background and independently selectable foreground styles: https://rich.readthedocs.io/en/latest/style.html

Rich syntax themes can also use the terminal background; the RIPOSTE report tokenizer shares semantic palette roles with the cell renderer instead of introducing a second filled code surface: https://rich.readthedocs.io/en/latest/syntax.html

No new design-reference screenshot or font file is bundled. The user's explicit background/palette and output-design requirements take precedence over the earlier marketing-page reference palettes.
