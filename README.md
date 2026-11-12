# RIPOSTE 0.5.0

**Find original titles:** `riposte library-search ROOT --search "moonlight"`, **s** in the terminal library, or **Private library search** in the browser. This opt-in lookup searches private original filenames and category assignments. See [private search](docs/CLI.md#private-library-search).

**Storage & recovery:** `riposte health ROOT`, the terminal workspace settings, and browser workspace navigation show read-only space and recovery observations. See [inspection details](docs/CLI.md#storage-and-recovery-inspection).

**Local image protection and organization. Interactive terminal menu and direct commands.**

Use the [documentation map](docs/README.md) and [current workflow/data contract](docs/CURRENT-CONTRACT.md) for public export, private recovery and historical-document boundaries.

Current development status, version/configuration identity and validation limits
are in [PROJECT-STATUS.md](docs/PROJECT-STATUS.md). The
[development audit and checkpoints](todo-audit.PACER.md) records the implementation
history. Guarded PACER updates resumed on 2026-09-20: PAC-044 reconciles that history,
PAC-036 reviews acceptance, PAC-035 adds cancellable browser scans, and PAC-037
adds guided browser category editing. PAC-038 shares recovery guidance across the
terminal and browser: errors retain a sanitized code and a concrete next action.
Browser messages stay until dismissed; small terminal windows can scroll the full
guidance. See [recovery guidance evidence](evidence/recovery-guidance/README.md). Version
0.5.0 identifies this checkout, not completion of the open audit or model qualification.

Development follows [Provable Claims and Use Cases](docs/PCUC.md). The publishing
engine now shares transform work across model contexts; the
[derivation and CPU measurements](evidence/pcuc-shared-views/README.md) distinguish
verified computational improvements from unverified protection efficacy.

New five-arm generation runs commit their protocol before generation and support
concealed-label review packets plus retained task-outcome ratings. The
[experiment workflow](docs/CLI.md#committed-generation-experiments) reports a
descriptive matched-control contrast, with protection efficacy still unverified.

The [cohort workflow](docs/CLI.md#committed-artwork-cohorts) commits a sampling pool
and selected artworks before generation, retains missing outcomes and reports
equal-artwork scores with exact missingness bounds. These are descriptive results,
not confidence intervals or proof of protection.

The [reviewer-panel workflow](docs/CLI.md#reviewer-calibration-panels) freezes a
task rubric and separate reviewer assignments for exact generated outputs. It
reports agreement, disagreement and missing-rating bounds; rubric validity and
reviewer independence still require empirical qualification.

`challenge` and `cohort-challenge` also accept an explicitly selected local
[FLUX Kontext editing bundle](docs/CLI.md#local-kontext-editing). Its preparation,
conditioning and model assets are bound to the experiment. Pretrained editing
quality and protection efficacy remain unqualified.

Catalog lookup and sorting now avoid repeated full-catalog reads while retaining
file checks and rejection of catalog changes during apply. See the
[catalog-scaling evidence](evidence/catalog-scaling/README.md) for measured scope.

RIPOSTE lets you protect selected images, sort a folder, or explicitly do both. Sorting separates images and videos, rebuilds images with date-only metadata, and retains original files privately for undo. Protection uses selected local models; exact reviewed outputs can be packaged for sharing. Direct commands and the interactive terminal share the same operations. The browser remains available; the workshop remains optional.


Named publishing settings are shared by CLI, terminal and browser. Use `riposte recipes ROOT` or the publishing form's **Recipes** controls. See [reusable publishing recipes](docs/PUBLISHING.md#reusable-publishing-recipes). Loading and saving settings never starts processing.

## Terminal revision 0.5

**Duplicate Finder** is an independent tool: main-menu **d**, or
`riposte duplicates "D:\Artwork"`. It lists **DUPLICATE**, **MAYBE DUPLICATE** and
**CLOSELY RELATED** findings with confidence and matching evidence. It compares
file contents, normalized image pixels, visual variants/crops and sampled video
frames without sorting or removing anything. Terminal search/detail/export and
the local browser's paired review share the same report. See the
[Duplicate Finder guide](docs/DUPLICATES.md) for controls and comparison limits.

Foreground-only `goks` is now the default. The host owns the background in every scene. Interactive results offer Overview / Details / JSON with `t`. Enter selects images, `i` inspects, `p` configures protection, and F1 explains the current screen. `f` expands advanced protection settings without resetting them.

The shelved revision was selectively integrated against the 0.4.0 archive while retaining this checkout's dependency and typing work. See the [merge record](docs/PATCH-v05-MERGE.md), [supplied design record](docs/REVISION-v05.md), and [build guide](docs/REBUILD.md). No workspace migration is needed.

## Install, then open the menu

Keep the application separate from image and model folders. Python 3.11+ is required.
Workspace selection, previews and execution reject the application folder, its
parents and its subfolders across the CLI, terminal and API. A source checkout
protects the RIPOSTE project root; a wheel installation protects the loaded
`riposte` package directory. Independent sibling image/results folders are allowed.
Linked folders and junctions remain rejected. If a library was previously placed
inside the application, move the whole library, including its private `.riposte`
or `.shroud` state and `.riposte-operation.lease`, to a separate folder on the
same filesystem while no operation is running, then preview it there. See the
[safeguard evidence and layout boundary](evidence/application-roots/README.md).

Install once, then launch without a path:

```powershell
.\INSTALL.ps1
.\START.ps1
```

You can also double-click `START.cmd`. **START opens the interactive main menu.**
**Riposte Sorter** is the first, default action. Open it for **1. Sort**,
**2. Dry Run**, or **3. Enter Path**. Paste your folder once, then choose Sort or
Dry Run without configuring a series of menus. `g` also enters a path; quotes
are accepted and a paste replaces the empty field. The folder stays selected
for the session. **Full Sort Workshop** retains the configurable workflow.

Riposte Sorter uses download dates (creation/birth time with modified-time
fallback), saved filename-category rules and supported local filename patterns, and
`Year/Month/img-or-vid/[Category if found]/Size`. Categories are optional per file:
weak patterns, tied matches or unknown original titles use the
ordinary date/media/size route. Manual choices and saved rules take precedence;
existing categories are retained when no new
match is available. No category setup or manual assignment is required to sort.
Images become date-only PNGs, videos keep their bytes, and originals remain
privately recoverable. Sidecar deletion requires explicit workshop consent.
**Sort** displays the exact preview, then requires `REPLACE`. **Dry Run** only
displays the preview; its result cannot apply. Direct `sort` defaults are unchanged;
`riposte sort ROOT --categories` previews the same preset.

**Keep personal storage out of sorting:** name a folder `_float_` or `__float__`.
Both names are case-insensitive and apply at any depth. Sorting skips the whole
folder, including nested images, videos, sidecars and other files, without
inspecting or changing its contents. Selecting that folder or one of its
descendants directly for sorting is refused. This applies to Riposte Sorter,
Full Sort Workshop, direct sort commands, and the sorting stage of Sort + RIPOSTE.
**Image RIPOSTE can still process these folders** while preserving their originals;
its file/folder intake includes them. The combined workflow protects the eligible
sorted images; use standalone RIPOSTE for float storage.

Blocked previews offer `w` to open Full Sort Workshop with the current settings.
Empty or already-sorted previews return without asking for unnecessary consent.
Confirmation shows the folder bound to the preview; submitting it consumes that
confirmation so completed operations cannot return to a filled confirmation.

**RIPOSTE** and **Sort + RIPOSTE** remain independent main-menu choices.
In the optional folder browser (`b`), Enter opens the highlighted folder and `s`
uses it directly; Backspace goes up and `l` lists drives and home locations.
Returning to a parent restores the child highlight. Page Up/Down moves by the
number of rows actually visible. Invalid paths keep your input and explain the error.
For protection inputs, Space selects files or folders and `s` selects the current
folder. `g` accepts a pasted path at every folder level and in Full Sort Workshop.
Esc cancels and returns to the previous screen.

INSTALL sets up the project-local `.venv` in editable mode and returns without
opening the application. With uv available it uses the existing lockfile and
preserves installed optional dependencies. The Python/pip fallback is also
editable. START never installs or downloads dependencies; a missing or stale
installation tells you to run INSTALL explicitly.

```powershell
.\INSTALL.ps1 -Lab                 # Optional processing dependencies; no model weights
.\START.ps1 -NoAnimation
.\START.ps1 -Theme light
.\START.ps1 -ImageFolder "D:\Images" # Optional initial folder; menu still opens first
```

`-ArtworkFolder` remains an alias for compatibility. `-Lab` has moved to INSTALL.
`-Browser -ImageFolder "D:\Images"` explicitly opens the existing browser interface.
`-Linear` selects the numbered line-input alternative for terminals without raw
keyboard support. Neither startup nor location selection modifies images.

The supplied local wrapper keeps every direct command available:

```powershell
.\riposte.cmd
.\riposte.cmd sort "D:\Images"
.\riposte.cmd riposte "D:\Results" --input "D:\Images\sample.png" --vae "D:\Models\encoder" --plan
.\riposte.cmd --help
```

For manual setup when script execution is restricted:

```powershell
uv sync --frozen --inexact
.\.venv\Scripts\riposte.exe
```

Alternatively, with Python 3.11+ and no uv, create `.venv` with `py -3 -m venv .venv`,
then run `.\.venv\Scripts\python.exe -m pip install --editable .`.

On macOS/Linux:

```sh
bash INSTALL.sh       # Add --lab for optional processing dependencies
bash START.sh         # Opens the menu; no folder required
# Optional launch flags: --no-animation --linear --theme light
```

## Two complete entry paths, one operation boundary

With the installed entry available:

```text
riposte                                # Interactive main action menu
riposte --root ROOT                     # Main menu with an initial folder
riposte ui ROOT                         # Explicit interactive entry
riposte ui ROOT --linear                # Numbered, line-input alternative
riposte --help                          # Complete typed command reference
riposte publish --help                  # All publishing controls
```

Direct commands and interactive forms call the same operation service. The interface does not simulate an engine, shell out to a pretend CLI, or execute the text displayed in the command lens.

The main action deck includes **Riposte Sorter / RIPOSTE / Sort + RIPOSTE / Image library / Publishing batches / Local models / Terminal & workspace / Full Sort Workshop / Undo last sort**, plus **Workshop** (`w`) for expert protection helpers.

| Workflow | Interactive terminal | Direct command |
| --- | --- | --- |
| Riposte Sorter | **Sort / Dry Run / Enter Path** with the category preset | `riposte sort ROOT --categories`; add `--apply --plan-id PLAN_ID` from that preview to replace sources |
| Full Sort Workshop | Configure dates, sidecars, categories and assignments; preview before `REPLACE` | `riposte sort ROOT` plus the corresponding options |
| Undo last sort | **Undo last sort** previews recovery, then requires `UNDO`; also available with `u` in the Sort form | `riposte undo-sort ROOT`; restore the reviewed ID with `--apply --sort-id SORT_ID` |
| RIPOSTE | **RIPOSTE** accepts a file or directory; library `p` protects selected catalog images | `riposte riposte ROOT --input PATH --vae MODEL`; repeat `--input` for more files/folders; add `--plan` for a read-only preview |
| Sort + RIPOSTE | **Sort + RIPOSTE** previews sorting and protection, then requires `REPLACE` | `riposte sort-riposte ROOT --all --vae MODEL`; add `--apply --plan-id PLAN_ID` from the combined preview to run both |

Standalone RIPOSTE preserves original files and folders. `ROOT` holds its application state and reviewed exports; inputs may be elsewhere. It creates date-only clean snapshots for resumable protection without reorganizing the input library. Directory inputs are recursive; the terminal browser accepts multiple selected files and folders. For existing catalog images use `--image ID` or `--all` with filters instead of `--input`. Unrelated additions no longer block publishing, reviewing or packaging selected catalog images.

**Every sort apply requires a reviewed preview ID.** Ordinary previews now show exact per-file destinations and bind source identity, content, date/sidecar policy, catalogs and private title records. Reinspect after adding, removing or changing inputs or settings. Combined sorting uses its **top-level** `plan_id`, which also binds the protection recipe, selection, device and model paths; the nested sorting ID cannot authorize both operations. Terminal and browser confirmation carry the displayed ID automatically. Direct callers must pass it explicitly. Pre-existing stale or missing consent is rejected before creating workspace state.

Sort retains the established reconstruction and source-replacement behavior, including explicit sidecar consent. Repeating it processes new additions and leaves verified clean masters alone. The combined workflow sorts `ROOT` and protects matching catalog images, including newly sorted additions. Model preflight happens before replacement; an incomplete sort stops protection. After successful sorting, protection can be retried separately. Existing `organize`, `publish`, `protect`, and expert commands remain available. Candidate creation never grants visual approval or verified protection efficacy.

Sorting uses `Year/Month/img/Size/NAME.png` for images and
`Year/Month/vid/Size/NAME.ext` for videos. The existing year/month rules and
`SML`, `MED`, `LRG`, `XTL` resolution bins remain. Videos keep their container,
extension, bytes and embedded metadata; sorting does not transcode or protect
them. Video inspection needs **ffprobe from FFmpeg on PATH**. INSTALL reports
whether it is available; it does not install FFmpeg. Image-only sorting and
protection do not need ffprobe. Common video extensions include MP4, MOV, MKV,
WEBM, AVI, M4V, WMV, MPG/MPEG, MTS/M2TS, 3GP and OGV; the installed ffprobe must
be able to read the actual stream. Unreadable videos remain in place as blockers.

**Filename category discovery is read-only.** In Full Sort Workshop, press `c` for
Categories, then run discovery to see recurring words and short phrases with
matching-file counts and examples. Return to the form to select or rename a group
with `Hockey=hockey`, or merge explicit terms with `Hockey=hockey;goalie;goaltender`.
Separate groups with commas in the terminal form. Minimum count, filler words and
ignored suggestions are editable; manual groups can match below the threshold.
The direct equivalent is `riposte categories ROOT --category "Hockey=hockey;goalie"`.
Groups in this screen are session drafts; they are not saved and cannot move files. Overlapping
groups are shown for review. Discovery reads filename stems by media extension,
without validating image/video contents. Generated numbered names are excluded
because generated names do not establish meaningful category keywords. They still
sort normally without categories. Opt-in category sorting uses the
`Year/Month/img-or-vid/Category/Size` layout below.

**Reusable rules can be saved through the CLI, terminal and browser.** Preview with
`riposte category-rules ROOT --category "Hockey=hockey;goalie" --review`.
Repeat that command with `--save --expected-revision missing` for the first save;
later saves require the revision shown by the current preview. `--exclude`,
`--priority`, and `--slug` customize exclusions, match priority and folder names.
`riposte category-rules ROOT --review` reloads saved rules and shows filename
matches. Rules are private workspace state; saving them does not enable category
sorting in the workshop or direct CLI. Riposte Sorter's preset uses saved rules
and supported local filename patterns.
In Full Sort Workshop, press `s` for saved rules. In the browser,
enable Sort by filename category and open Discover and save category rules.
The browser loads saved categories into labeled rows: name, stable folder name,
matching phrases, exclusions and priority. Enter one phrase per line. Renaming
the display name keeps its folder name. Inline errors identify invalid fields;
**Review rule changes** checks a draft, and **Save reviewed rules** explicitly
replaces the saved rules. Unsaved edits never change sorting. Reloading protects
an unsaved draft with **Keep draft / Discard draft and load**.

After **Inspect without changes**, choose a saved category beside any file,
**Automatic** to clear a manual choice, or **Uncategorized** for that explicit
folder. **Keep current choice** preserves the current saved choice. File lists
show 50 entries per page; choices persist across pages. Inspect again after any
change, review the exact destinations, then acknowledge and apply. These controls
are optional; missing categories never prevent ordinary date/month sorting.
See [guided editor verification](evidence/guided-category-editing/README.md).
See [the command reference](docs/CLI.md#saved-category-rules).

**Category sorting is the Riposte Sorter preset and optional in other entries.** Run `riposte sort ROOT --categories` for a
read-only plan containing every source, trusted original title, matching term,
category and exact destination. Apply with `--categories --apply --plan-id ID`
using the ID from that preview. Changed files, rules, assignments, catalogs or
destinations require a refreshed preview. Weak, conflicting and unknown titles
sort normally without a category; an existing category is retained. Optional
`--assign "relative/path=slug"` lets you choose a category explicitly.
Sorts from this version retain original titles and assignments in the private
`sort_titles` table, separate from the public media catalog. Undo restores these
records together with the image/video catalog; output PNG metadata remains date
only. Normal sorting preserves existing category folders without enabling
categories for new files. Browser undo has its own preview and confirmation.

**Preview is read-only.** It shows destination folders, image/video counts and
blockers without creating application state. **Undo applies to sorts recorded
by this version**, including partially completed sorts. Earlier sorts that
discarded originals have no recovery record. Each new sort retains original
bytes, names and modified times under `.riposte/sort-history` (or legacy
`.shroud/sort-history`). This private history includes original metadata and
uses additional disk space, including full video copies. Keep it with the
library; deleting it removes the ability to undo. It never enters publishing
packs. Repeated undo walks backward through recorded sorts; a no-change sort
does not replace the last recovery record.

Undo checks the complete operation before restoring files. Occupied original
paths, changed sorted files, damaged backups and changed catalogs block it;
files added elsewhere remain untouched. Protection outputs and reviews remain
in place, although a removed catalog image must be sorted again before a batch
that depends on that image can resume. Already created publishing packs remain
unchanged. Legacy image paths remain readable; the next explicit sort moves
them into `img` while preserving image IDs, dates and bytes.

Workspace operations now hold an OS lease on the empty root file
`.riposte-operation.lease`. Keep that file in place. If a current-version worker
is killed, the next explicit operation can reclaim its matching abandoned marker
after acquiring the lease; undo still requires its preview and integrity checks.
Recovery never guesses from a PID or a lock's age. Unidentified legacy/empty lock
markers remain blocked, and unsupported locking or atomic publication fails
closed. Older versions may report the new root file as an unsupported input.
See the [PAC-029 evidence and compatibility limits](evidence/workspace-lease/README.md).

## The ASCII experience

COUNTERSTROKE is an authored depth-resolved lamellar image-plane material with moving hinges, travelling light and a reflected stroke. It is drawn from ordinary ASCII cells by Rich, not from terminal bitmaps, web views, a font pack or a pre-rendered movie. The entrance is immediately interactive: no artificial loading countdown or minimum animation duration.

Working screens have different compositions: selected images, editable protection fields, real batch outputs, explicit source-replacement confirmation, operation activity and full result inspection. Colour ASCII previews help identify an image; **they are not substitutes for full-resolution visual review**. Press `v` in an image inspector to hand audited PNG bytes to a local image viewer. The handoff does not approve the image.

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
riposte --json organize ROOT --date-mode modified --discard-sidecars

# Review the destinations and copy plan_id; repeat the same options.
riposte organize ROOT --apply --plan-id PLAN_ID --date-mode modified --discard-sidecars
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

Calendar roots use the file's actual year, followed by its English month;
SML/MED/LRG/XTL directories appear only when needed. Legacy `EVERYTHING_ELSE`
catalogs remain readable; sorting previews their relocation into actual years,
and Undo restores their prior paths. Bins are pixel area below 1M, 4M, 16M and
16M or more. Images are not sorted by file extension.

Local category proposals recognize CamelCase, repeated words and phrases while
discounting export/version noise and duplicate filename variants. Their scores
describe filename evidence, not image content or measured accuracy. Small,
ambiguous or resource-limited collections still sort normally. No extra setup
screen or model download is required. See the [critical research review](docs/research/sorting/RIPOSTE-REVIEW.md)
and [executed evidence](evidence/sorting-research/README.md).

Sanitation still decodes supported input, applies orientation, converts supported colour profiles, rebuilds pixels, clears fully transparent hidden RGB, and writes fresh PNG with only its date. Applying organization saves private original copies for undo before removing source paths. Video bytes and private recovery copies retain original metadata; date-only sanitation applies to generated images. Unsupported and failed inputs remain blockers. This is not forensic erasure of operating-system caches or data encoded into visible images.

The protection engines remain **experimental**; current research integrations and their limits are recorded in [PCUC](docs/PCUC.md). Generating a candidate, passing a numerical visual limit, or accepting its appearance does not establish AI resistance. No new efficacy or pretrained-model result is claimed here. There is no watermark, audience login, licensing gate, images upload or noise-only fallback.

## Optional helpers and reference

All inherited helper paths remain accessible, including standalone guard, external comparison, encoder qualification, five-arm generation, legacy paired benchmark, trial export and exact-file handoff. The `generation` and `frame` commands expose complete saved reports and audited frames. They are below the main product actions, not prerequisites for normal publishing.

- [Complete CLI and linear-menu reference](docs/CLI.md)
- [Current terminal/browser interaction contract](docs/UX-CONTRACT.md)
- [Historical terminal design specification](docs/TERMINAL-DESIGN.spec.md)
- [Publishing contracts](docs/PUBLISHING.md)
- [Historical 0.3 image-engine mathematics](docs/ENGINE-v03.md)
- [Historical Wave 04 delivery record](docs/WAVE-04.md)
- [Historical terminal revision and selective merge](docs/PATCH-v05-MERGE.md)
- [Current project status and validation](docs/PROJECT-STATUS.md)
- [Historical 0.4 validation and provenance](docs/VALIDATION.md)

The previous CLI, README, validation and evidence are retained under `history/v0.3.0/`. The original 0.4.0 and supplied 0.5.0 snapshots remain in `packages/`. The selective merge record describes that historical integration; later application changes and checks are linked from [current project status](docs/PROJECT-STATUS.md). Historical screenshots, wheels and test claims in those ZIPs are not validation of this checkout. Development captures use original synthetic geometric fixtures.

Artist-directed budgets are optional in publishing: attach a grayscale PNG under
**Artist masks**, or use `--budget-mask` for one image and `--budget-map` for a
private exported map. Black keeps pixels exact; white retains automatic limits.
See [mask format and final-size previews](docs/PUBLISHING.md#artist-masks).
