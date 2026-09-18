# RIPOSTE / terminal and command reference

## Command inventory

Every listed command is a real Typer command; use `riposte COMMAND --help` for parameter types, defaults, bounds and repeatable options.

| Command | Direct target | Effect |
|---|---|---|
| `ui [ROOT]` | Optional workspace | Native Rich menu; `--linear` explicitly permits scripted stdin |
| `organize ROOT` | Whole maintained workspace | Read-only plan; `--apply` explicitly replaces successfully reconstructed sources |
| `sort ROOT` | Whole maintained workspace | Alias of `organize`; incremental sorting without protection |
| `categories ROOT` | Filename stems under ROOT | Read-only term discovery and session category review; no media, catalog or rules writes |
| `undo-sort ROOT` | Last recorded sort in this workspace | Read-only recovery preview; `--apply` restores originals if conflict checks pass; optional `--sort-id` binds confirmation to an exact preview |
| `riposte ROOT` | Repeated `--input` files/folders, or catalog selection | Protect independently; raw originals stay unchanged; `--plan` writes nothing |
| `sort-riposte ROOT` | Whole workspace, then catalog selection | Preview by default; `--apply` authorizes sorting followed by protection |
| `audit ROOT` | Whole workspace | Inspect clean PNGs, artifacts, catalog and calendar/size rules |
| `list ROOT` | Filterable clean catalog | Inspect; `--year`, `--month`, `--size`, `--search`, `--offset`, `--limit` |
| `inspect ROOT IMAGE_ID` | Clean master | Verify exact bytes and print complete technical metadata audit |
| `publish ROOT` | Repeated `--input`, or `--image` repeated, or `--all` with filters | Generate final-size candidates; `--plan` is read-only |
| `protect ROOT` | Same as publish | Typed alias, not a separate engine |
| `publications ROOT [BATCH_ID]` | All batches or one | Inspect complete output/review states |
| `resume ROOT BATCH_ID` | Unfinished batch | Reload matching models; keep committed outputs byte-identical |
| `review ROOT BATCH_ID` | Repeat `--item` | Record visual acceptance plus status acknowledgement, or reject |
| `package ROOT BATCH_ID` | Accepted batch outputs | Write an exact-byte, PNG-only publishing ZIP |
| `image ROOT` | `--image`, `--batch` plus `--item`, or `--trial` | Inspect verified PNG; `--open` is an explicit local viewer handoff |
| `doctor` | Optional repeated `--vae` | Inspect runtime; `--execute` runs a numerical input-gradient probe |
| `upgrade ROOT` | Legacy `.shroud` application state | Explicit state rename; no images rewrite |
| `serve ROOT` | Local workspace | Existing loopback browser alternative; optional `--no-browser`, `--port` |
| `guard ROOT IMAGE_ID` | One master | Expert standalone experimental candidate |
| `compare ROOT IMAGE_ID CANDIDATE` | External candidate | Sanitize, compare and commit an expert trial |
| `qualify ROOT TRIAL_ID` | Repeated evaluation `--vae` | Save controlled encoder comparisons |
| `challenge ROOT TRIAL_ID` | `--model`, `--task`, repeated `--seed`/`--view` | Five-arm reference generation |
| `benchmark ROOT TRIAL_ID` | `--model`, `--task` | Inherited two-arm compatibility runner |
| `export ROOT TRIAL_ID` | Expert trial | Explicitly acknowledged unverified export, not an approved-image pack |
| `trials ROOT [TRIAL_ID]` | All trials or one | Inspect saved trial reports |
| `evaluations ROOT TRIAL_ID` | Trial | Inspect saved encoder evaluation records |
| `generations ROOT TRIAL_ID` | Trial | Inspect saved generation runs |
| `generation ROOT RUN_ID` | One generation run | Inspect full report, including allowlisted frame names |
| `frame ROOT RUN_ID RELATIVE` | Exact report-listed frame | Inspect or `--open` audited frame; no arbitrary file access |
| `workshop ROOT [BATCH_ID ITEM_ID]` | Helper menu or exact output | Open optional menu, or create/reuse an exact-pixel trial handoff |

Presentation flags and Typer's completion options are not additional application commands.

## Filename category discovery

`riposte categories ROOT` discovers recurring words and contiguous phrases in
image/video filename stems. Each term counts once per file, wherever it appears.
Use `--min-count 1` to include one-off terms, `--max-words 1` for words only,
`--ignore TERM` to hide a suggestion, and `--fillers ""` to disable filler words.

```powershell
riposte categories ROOT --category "Hockey=hockey;goalie;goaltender"
riposte categories ROOT --category "Sports=hockey" --category "Practice=practice"
```

Each explicit group selects or renames a category and merges its supplied terms.
Repeated groups show overlaps for review without assigning a winner. In the menu,
open Sort and press `c`; edit Category groups and run again to review them.
Separate groups with commas in the form. The report shows matching-file counts
and title examples; Details retains the complete bounded report.

This milestone writes no media, catalog entries or saved rules. It does not
decode media or infer titles for numbered SML/MED/LRG/XTL files. Persistent rules,
original-title recovery and `Year/Month/img-or-vid/Category/Size` destinations remain
planned work under PAC-027B; current sorting keeps its existing layout.

## Publishing configuration

`publish` accepts repeated `--image`, repeated `--vae` (up to four), repeated `--edge` (up to three), `--all`, `--year`, `--month`, `--size`, `--plan`, `--epsilon`, `--steps`, `--restarts`, `--seed`, `--device`, `--inpaint`, `--video`, `--preserve-white/--no-preserve-white`, `--delta-e76-p95`, `--rms-fraction`.

A model-dependent action with no usable model stops with a code; it does not add a cosmetic effect instead. Local paths are reselected on a later session because RIPOSTE does not save a model-path history. Four local encoders are not a promise that four large models fit available memory.

`--all` means all matching catalog images. For unorganized inputs, use repeated `--input PATH` with `riposte`, `publish`, or `protect`; a path can be a file or a recursively scanned directory. Relative paths use the current working directory. At most 200 distinct files are selected; overlapping paths are deduplicated. Non-image files are left untouched, corrupt image inputs stop intake, links/junctions are rejected, and internal `.riposte`/`.shroud` directories are excluded. Raw paths and metadata are not saved in batch records. `--date-mode download|modified|embedded` chooses the snapshot date basis. Originals stay where they are.

Use exactly one selection style: `--input`, `--image`, or `--all`. Date and resolution filters qualify `--all`; they cannot be combined with raw inputs or explicit IDs. Selected catalog sources are verified individually, so unrelated additions do not force sorting before a protection run.

```powershell
# Repeat only sorting when new images arrives.
riposte sort ROOT
riposte sort ROOT --apply

# Inspect recovery before explicitly restoring the last recorded sort.
riposte undo-sort ROOT
riposte undo-sort ROOT --apply

# Protect selected originals without restructuring their directory.
riposte riposte ROOT --input "D:\Images\drawing.png" --input "D:\Images\New" --plan
riposte riposte ROOT --input "D:\Images\drawing.png" --input "D:\Images\New" --vae MODEL

# Preview both operations, then explicitly authorize source replacement.
riposte sort-riposte ROOT --all --vae MODEL
riposte sort-riposte ROOT --all --vae MODEL --apply
```

The combined command sorts the whole `ROOT`; it does not accept `--input`. Its protection selection is `--all` (optionally filtered) or existing `--image` IDs. `--discard-sidecars` is separate consent to delete metadata sidecars during sorting. Model preflight occurs before source replacement. An incomplete sort stops the pipeline; a later protection failure keeps the sorting receipt and supports a separate RIPOSTE retry. A created batch uses the existing `resume`, exact-pixel `review`, and `package` commands. Neither workflow approves images automatically.

Sort destinations are `Year/Month/img/Size` and `Year/Month/vid/Size`. Video
inspection requires ffprobe on PATH. Video files retain their bytes and metadata
and never enter the image protection catalog. Original files and explicitly
discarded sidecars are retained privately for undo, including their original
metadata and names. This uses extra disk space. Undo requires these recovery
copies and refuses conflicts; it cannot recover sorts made before history was
introduced. `Undo last sort` is a main-menu action and the Sort form's `u` key.
Its preview must be followed by the exact `UNDO` word. Protection results remain
in place. Interrupted recovery must be completed before another sort.

The workshop guard retains `--engine coupled|encoder`; the primary publish route calls the inherited release-v1 algorithm. A workshop pipeline is selected with `--pipeline`; primary publishing uses `--inpaint` and `--video`.

## Presentation and terminal capabilities

```text
riposte --json COMMAND ...
riposte --human COMMAND ...
riposte --plain COMMAND ...
riposte --events --json COMMAND ...
riposte --no-animation ui ROOT
riposte --theme goks ui ROOT
riposte --theme light ui ROOT
riposte --theme mono --fps 12 ui ROOT
riposte --no-color ui ROOT
```

These are global flags: put them before the command. stdout redirection automatically selects JSON for direct commands. Diagnostic/operation events are on stderr. `--plain` suppresses ANSI and selects the linear interface on an interactive entry. `TERM=dumb` also uses linear menus. `NO_COLOR` suppresses colours without deleting keyboard functionality. `RIPOSTE_NO_ANIMATION=1` freezes authored motion; actual time and callback counts remain live. ASCII glyph output does not require a special terminal font. Local Unicode path input is retained, while the ASCII display uses a replacement glyph for non-ASCII characters.

The terminal uses Rich Live's alternate screen. On ordinary exit, Ctrl+C, handled errors, or handled SIGTERM it restores terminal mode, bracketed-paste state and cursor visibility and joins the owned worker. SIGKILL, kernel failure and power loss cannot run cleanup. A particular model forward call cannot be forcibly interrupted safely; cancellation waits for a backend checkpoint. Source replacement, review and package commits are not abandoned on an interactive interrupt.

## Result display and contextual controls (0.5)

Normal results are semantic reports, shared by the interactive and direct human CLI. `t` cycles Overview, complete Details and syntax-coloured JSON. Only explicit machine output retains raw JSON as its primary representation. Backgrounds always belong to the host terminal.

Enter toggles an image selection; `i` inspects the focused image. Space remains a compatibility alias, not the required selection key. `f` expands the publishing form's advanced settings without discarding any values. F1 explains the exact current screen and focused field.

## Interactive actions

Numbered actions and arrow/Enter navigation are always visible. The home screen exposes RIPOSTE, Sort, and Sort + RIPOSTE and keeps the workshop last. `Esc` or `0` returns without changing a field; `q` exits outside a text field. Bracketed paste is consumed as field/search data, not as queued Enter or menu shortcuts. Input and rendering never evaluate arbitrary shell text. RIPOSTE first browses selected files/folders, then asks where to save results. The input selection is not limited to four paths. `f` reveals advanced protection settings without discarding the selection. Both Sort forms always preview first and require the exact word `REPLACE` before source replacement; protection-only forms never sort.

The image library supports search, multi-selection and selection-preserving inspection. Its `p` shortcut carries that selection into protection settings. Model directories entered in Local models remain available in the current process's publishing and helper forms. `F4` shows the configured command; in a publishing form it shows the default read-only preview invocation. After an operation it shows that actual operation. Copying/executing it is the user's separate action; RIPOSTE performs no clipboard write or shell evaluation.

The source-migration preview shows the actual current plan, then `a` opens the explicit **REPLACE** boundary. The apply operation re-inspects the workspace rather than trusting a stale path list. Output acceptance has its own **ACCEPT** boundary and both underlying acknowledgements; a local viewer launch is not an acceptance event. The panel's numerical output checks are not an AI protection percentage.

## Linear interface

`riposte ui ROOT --linear` uses the same controller and service without raw key capture or animated updates. Useful typed instructions:

```text
2                         choose Image library from the home menu
select 1,3                toggle visible row numbers in the library
p                         configure publishing for the selection
edit 1 1024,1536           set the first form field
focus 3                   focus a visible list row
enter                     activate the focused action; select a library image
inspect                   inspect the focused library image
advanced                  expand/collapse protection settings
details                   cycle result report views
plan                      run a read-only preview in the appropriate form
run                       explicit operation in the appropriate form/result
apply                     open the source-replacement confirmation from its plan
REPLACE                   exact confirmation text, only while that boundary is open
back                      return without executing
search September          filter the current collection/action list
command                   show the direct-command lens
help                      key reference
q                         leave menus
/cancel                   discard a field or confirmation instead of entering data
```

Typed text in a field replaces that field; it is not interpreted as a command. No stdin script is accepted as an implicit interactive session: select `--linear` explicitly. A source migration in a script must still provide the explicit confirmation or use direct `organize --apply`.

## Images and exact frames

The terminal's thumbnail is a composition aid. `image --open` hands verified PNG bytes to the local OS viewer. Transformed publication/trial previews are newly audited date-only PNGs cached under `.riposte/terminal-previews/`; raw image metadata, source paths and view reports are not copied into those PNGs. These cache images participate in the existing artifact audit. Canonical masters support identity inspection only; unsupported master-view combinations are rejected rather than silently ignored.

`frame` requires an exact allowlisted report-relative name, such as `V00-S00-clean/F000.png`. Absolute paths, parent traversal, an unlisted frame, a changed hash or a changed date cannot pass the existing generation-frame reader.

## Exit and compatibility

Direct results preserve the existing JSON payloads and positional ROOT/ID conventions. Exit status 2 also reflects incomplete checkpoints or blocked publishing items; it is not solely a parser error. Sensitive argument values and underlying exceptions are not echoed. Use the command help to correct invalid inputs.

Old SHROUD state stays readable until explicitly upgraded. v0.2/v0.3 workspaces need no catalog rewrite to use this terminal. The prior argparse source is retained as history, not a second executable command implementation. The browser and image engines remain unchanged.

## Menu-first startup

Run `riposte`, `riposte ui`, `START.ps1`, or `START.cmd` without a folder to
open the interactive main menu. Choose an action with arrows and Enter or a
visible number. It explains the input/output scope before opening its location
browser. Space selects files/folders for RIPOSTE; Enter opens folders; Backspace
goes up; `l` lists drives; `g` optionally accepts a pasted location. Esc returns
without processing. Sort and combined processing retain the preview and exact
`REPLACE` confirmation. Direct command syntax remains unchanged.

`INSTALL.ps1` / `INSTALL.sh` perform setup only. START never installs packages.
The optional `-ImageFolder` (`-ArtworkFolder` alias) or shell positional folder
preselects a location without skipping the menu. `-Lab` / `--lab` belongs to INSTALL.
