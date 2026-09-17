# RIPOSTE 0.5.0

**Local artwork security. Native Typer commands. An authored, animated Rich ASCII interface.**

RIPOSTE reconstructs image files with date-only metadata, organizes a maintained artwork directory, applies experimental image-integrated protection through selected local models, and packages exact reviewed publishing images. The existing Typer command surface and native Rich terminal now share designed operation reports and foreground-only styling. The browser remains available; the workshop remains an optional helper.

## Terminal revision 0.5

Foreground-only `goks` is now the default. The host owns the background in every scene. Interactive results offer Overview / Details / JSON with `t`. Enter selects images, `i` inspects, `p` configures protection, and F1 explains the current screen. `f` expands advanced protection settings without resetting them.

The shelved revision was selectively integrated against the 0.4.0 archive while retaining this checkout's dependency and typing work. See the [merge record](docs/PATCH-v05-MERGE.md), [supplied design record](docs/REVISION-v05.md), and [build guide](docs/REBUILD.md). No workspace migration is needed.

## Start the terminal on Windows

Extract the application outside your artwork and model folders. Python 3.11+ is required.

```powershell
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples"
```

The launcher installs the core into a project-local `.venv`, then opens the animated terminal. Startup does not organize or remove images. Add `-Lab` to install the optional model-processing dependencies; weights are not bundled or automatically downloaded.

```powershell
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples" -Lab
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples" -NoAnimation
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples" -Theme light
```

`-Browser` explicitly starts the existing browser application. `-Linear` selects the plain line-input interface. The launcher preserves application/artwork separation checks. Native PowerShell execution was not available in the development host; the actual terminal was exercised in a POSIX pseudo-terminal, including cleanup and resize.

Once installed, the supplied local wrapper supports all commands without environment activation:

```powershell
.\riposte.cmd list "D:\Artwork\SocialSamples"
.\riposte.cmd --json publish "D:\Artwork\SocialSamples" --all --edge 1024 --plan
.\riposte.cmd ui "D:\Artwork\SocialSamples"
```

The installed console entry is `riposte`. Activate the project environment to use that shorter name, or invoke `.venv\Scripts\riposte.exe` directly. Manual setup when script execution is restricted:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\riposte.exe ui "D:\Artwork\SocialSamples"
```

On macOS/Linux:

```sh
bash START.sh "$HOME/Artwork/SocialSamples"
# Optional flags: --lab --browser --no-animation --linear --theme light
```

## Two complete entry paths, one operation boundary

With the installed entry available:

```text
riposte                                Animated workspace chooser
riposte --root ROOT                     Animated workspace already selected
riposte ui ROOT                         Explicit interactive entry
riposte ui ROOT --linear                Numbered, line-input alternative
riposte --help                          Complete typed command reference
riposte publish --help                  All publishing controls
```

Direct commands and interactive forms call the same operation service. The interface does not simulate an engine, shell out to a pretend CLI, or execute the text displayed in the command lens.

The main action deck is **Protect & publish / Image library / Clean & organize / Publishing batches / Local models / Terminal & workspace / Workshop**. The normal workflow never requires the workshop.

## The ASCII experience

COUNTERSTROKE is an authored depth-resolved lamellar image-plane material with moving hinges, travelling light and a reflected stroke. It is drawn from ordinary ASCII cells by Rich, not from terminal bitmaps, web views, a font pack or a pre-rendered movie. The entrance is immediately interactive: no artificial loading countdown or minimum animation duration.

Working screens have different compositions: selected artwork, editable protection fields, real batch outputs, explicit source-replacement confirmation, operation activity and full result inspection. Colour ASCII previews help identify an illustration; **they are not substitutes for full-resolution visual review**. Press `v` in an image inspector to hand audited PNG bytes to a local image viewer. The handoff does not approve the image.

| Key | Behaviour |
| --- | --- |
| Arrows or `j` / `k` | Move focus |
| Enter | Activate the highlighted action; select an image; edit or toggle the focused field |
| `i` in the library | Inspect the highlighted image without changing selection |
| Space | Optional compatibility alias for selection or checkbox toggling |
| `/` | Search visible actions, clean catalog or batches |
| Esc / `0` | Back; discard an unfinished field edit |
| F1 / F2 / F3 / F4 | Contextual help / pause motion / palette / equivalent direct command |
| `q` / Ctrl+C | Exit or request a cooperative stop; active source commits finish safely |

Library shortcuts are visible on the screen: `a` selects visible images, `n` clears, `p` opens protection. Forms use `p` for a read-only plan and `r` for the explicit operation; Clean & organize always previews first and also exposes `v` for the audit. The migration result requires a typed **REPLACE** confirmation before source replacement.

Designed terminal sizes include **132×46, 100×34 and 79×24**. Below 72×24, interactive actions are suspended behind a resize notice; exit/cancellation remains available. The line-input alternative does not need raw keyboard mode. `--no-color`, `NO_COLOR`, `--plain`, `--no-animation` and `RIPOSTE_NO_ANIMATION=1` are supported. Session preferences and local model paths are not written to a history file.

## Direct targeting and publishing

```powershell
# Read-only listing and image selection filters.
riposte list ROOT --year 2026 --month September --size MED
riposte list ROOT --search September --limit 20 --offset 0
riposte inspect ROOT IMAGE_ID

# Preview the reconstruction and organization; this writes nothing.
riposte organize ROOT --date-mode modified

# Explicitly authorize reconstruction followed by removal of verified sources.
riposte organize ROOT --apply --date-mode modified --discard-sidecars
riposte audit ROOT

# Preview selected final-size outputs, without a model requirement.
riposte publish ROOT --all --year 2026 --month 9 --edge 1024 --edge 1536 --plan

# Apply protection to selected clean images. No master image is changed.
riposte publish ROOT --image IMAGE_ID --vae "D:\Models\Encoder" --edge 1536 --epsilon 4 --steps 24 --restarts 2

# Open exact output bytes, record visual acceptance, then package.
riposte publications ROOT BATCH_ID
riposte image ROOT --batch BATCH_ID --item ITEM_ID --open
riposte review ROOT BATCH_ID --item ITEM_ID --visual-accepted --acknowledge-unverified
riposte package ROOT BATCH_ID

# Resume unfinished work with matching local models; retain committed outputs.
riposte resume ROOT BATCH_ID --vae "D:\Models\Encoder"
```

`ROOT`, `IMAGE_ID`, `BATCH_ID`, and `ITEM_ID` are placeholders; use the path and IDs returned by the application. Repeat `--image`, `--vae`, `--edge` and `--item` where appropriate. Explicit IDs and `--all` are mutually exclusive; date/size filters qualify `--all`. Up to 200 images, four encoders and three distinct publishing edges are accepted. No upscale; duplicate effective output sizes are avoided. `protect` is a typed alias of `publish`.

The reviewed ZIP is written under `.riposte/exports/BATCH_ID/RIPOSTE.zip`. Only accepted date-only PNGs enter it, with exact candidate bytes and the requested year/month/size organization. Model paths, reports, clean comparison images and raw metadata do not enter it. Rejection excludes an output from future packs, not from already downloaded copies.

## Automation is not an animated transcript

```powershell
riposte --json list ROOT
riposte --json --events publish ROOT --all --vae "D:\Models\Encoder" --edge 1024
```

Global presentation flags precede the command. Direct output automatically becomes JSON when stdout is redirected; `--human` forces readable Rich output. `--json` emits one result document on stdout. `--events` sends code-defined progress JSON Lines separately to stderr. Errors return sanitized codes rather than raw exceptions, local paths or metadata. No animation enters machine output.

Exit statuses: **0** completed command, **2** invalid input/operation failure/incomplete checkpoint or blocked output, **130** cooperative model cancellation, **143** handled SIGTERM. A publishing queue reaching its end is not silently converted into success when items are blocked. A non-cancellable source commit returns its actual outcome after Ctrl+C rather than abandoning a half-commit.

## Existing privacy and image contracts

The calendar roots remain `2026`, `2025`, `2024`, `EVERYTHING_ELSE`; English month directories and SML/MED/LRG/XTL appear only when needed. Bins are pixel area below 1M, 4M, 16M and 16M or more. Images are not sorted by file extension.

Sanitation still decodes supported input, applies orientation, converts supported colour profiles, rebuilds pixels, clears fully transparent hidden RGB, and writes fresh PNG with only its date. Applying organization removes successfully replaced originals, without raw backup or Trash copies. Unsupported and failed inputs remain blockers. This is not forensic erasure of operating-system caches or data encoded into visible artwork.

The protection engines are unchanged in this CLI release and remain **experimental**. Generating a candidate, passing a numerical visual limit, or accepting its appearance does not establish AI resistance. No new efficacy or pretrained-model result is claimed here. There is no watermark, audience login, licensing gate, artwork upload or noise-only fallback.

## Optional helpers and reference

All inherited helper paths remain accessible, including standalone guard, external comparison, encoder qualification, five-arm generation, legacy paired benchmark, trial export and exact-file handoff. The `generation` and `frame` commands expose complete saved reports and audited frames. They are below the main product actions, not prerequisites for normal publishing.

- [Complete CLI and linear-menu reference](docs/CLI.md)
- [Terminal visual and interaction specification](docs/TERMINAL-DESIGN.spec.md)
- [Publishing contracts](docs/PUBLISHING.md)
- [Image-engine mathematics](docs/ENGINE-v03.md)
- [Development record and next grouped implementation](docs/WAVE-04.md)
- [Terminal revision and selective merge](docs/PATCH-v05-MERGE.md)
- [Executed internal validation and provenance](docs/VALIDATION.md)

The previous CLI, README, validation and evidence are retained under `history/v0.3.0/`. The original 0.4.0 and supplied 0.5.0 snapshots remain in `packages/`. The merge preserves image-engine, sanitation, organization, publication, storage and browser files. Historical screenshots, wheels and test claims in those ZIPs are not validation of this checkout; current checks are recorded in the merge record. No user artwork was used in development captures; previews show original synthetic geometric fixtures.
