# RIPOSTE / terminal and command reference

## Command inventory

Every listed command is a real Typer command; use `riposte COMMAND --help` for parameter types, defaults, bounds and repeatable options.

| Command | Direct target | Effect |
|---|---|---|
| `ui [ROOT]` | Optional workspace | Native Rich menu; `--linear` explicitly permits scripted stdin |
| `organize ROOT` | Whole maintained workspace | Read-only plan; `--apply` explicitly replaces successfully reconstructed sources |
| `audit ROOT` | Whole workspace | Inspect clean PNGs, artifacts, catalog and calendar/size rules |
| `list ROOT` | Filterable clean catalog | Inspect; `--year`, `--month`, `--size`, `--search`, `--offset`, `--limit` |
| `inspect ROOT IMAGE_ID` | Clean master | Verify exact bytes and print complete technical metadata audit |
| `publish ROOT` | `--image` repeated, or `--all` with filters | Generate final-size candidates; `--plan` is read-only |
| `protect ROOT` | Same as publish | Typed alias, not a separate engine |
| `publications ROOT [BATCH_ID]` | All batches or one | Inspect complete output/review states |
| `resume ROOT BATCH_ID` | Unfinished batch | Reload matching models; keep committed outputs byte-identical |
| `review ROOT BATCH_ID` | Repeat `--item` | Record visual acceptance plus status acknowledgement, or reject |
| `package ROOT BATCH_ID` | Accepted batch outputs | Write an exact-byte, PNG-only publishing ZIP |
| `image ROOT` | `--image`, `--batch` plus `--item`, or `--trial` | Inspect verified PNG; `--open` is an explicit local viewer handoff |
| `doctor` | Optional repeated `--vae` | Inspect runtime; `--execute` runs a numerical input-gradient probe |
| `upgrade ROOT` | Legacy `.shroud` application state | Explicit state rename; no artwork rewrite |
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

There are **27 command names**, including the `protect` alias. Presentation flags and Typer's completion options are not additional application commands.

## Publishing configuration

`publish` accepts repeated `--image`, repeated `--vae` (up to four), repeated `--edge` (up to three), `--all`, `--year`, `--month`, `--size`, `--plan`, `--epsilon`, `--steps`, `--restarts`, `--seed`, `--device`, `--inpaint`, `--video`, `--preserve-white/--no-preserve-white`, `--delta-e76-p95`, `--rms-fraction`.

A model-dependent action with no usable model stops with a code; it does not add a cosmetic effect instead. Local paths are reselected on a later session because RIPOSTE does not save a model-path history. Four local encoders are not a promise that four large models fit available memory.

`--all` means all matching catalog images, not every raw file on disk. Organize raw inputs first through its explicit source-replacement boundary. Date and resolution filters qualify `--all`; combining filters with explicit IDs is rejected instead of ambiguously intersecting or ignoring them.

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

Numbered actions and arrow/Enter navigation are always visible. The home screen keeps publishing first and the workshop last. `Esc` or `0` returns without changing a field; `q` exits outside a text field. Bracketed paste is consumed as field/search data, not as queued Enter or menu shortcuts. Input and rendering never evaluate arbitrary shell text.

The artwork library supports search, multi-selection and selection-preserving inspection. Its `p` shortcut carries that selection into protection settings. Model directories entered in Local models remain available in the current process's publishing and helper forms. `F4` shows the configured command; in a publishing form it shows the default read-only preview invocation. After an operation it shows that actual operation. Copying/executing it is the user's separate action; RIPOSTE performs no clipboard write or shell evaluation.

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
