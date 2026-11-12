# RIPOSTE / terminal and command reference

This is the shipping CLI reference. See the [current contract](CURRENT-CONTRACT.md)
for consent, generated-image metadata and private-state scope; older command/menu
counts are historical. The inventory below includes every registered command.

`ROOT` must be an existing, unlinked directory separate from the loaded RIPOSTE
application. The source checkout's project root, or an installed wheel's `riposte`
package directory, cannot equal, contain or be contained by `ROOT`. CLI, terminal
and API share this check for previews and execution; rejection creates no state.
Independent sibling image/results folders are allowed. `--input` remains a
separate read-only source selection for standalone protection. See the
[application-root evidence](../evidence/application-roots/README.md) for layout
and compatibility details.

## Quick terminal sorting

Open **Riposte Sorter** (the default main-menu action): **1. Sort**, **2. Dry Run**,
**3. Enter Path**. Enter a folder once per session using `3` or `g`; both Sort and
Dry Run ask for it directly if none is selected. No configuration screens precede
the preview. The preset uses download dates, saved rules and supported local
filename patterns, separate img/vid
folders and existing size bins. Missing, tied or unavailable title matches use
the ordinary date/media/size route; no category setup is required. Sidecars are preserved
unless separately authorized there. Sort reviews a fresh exact plan and requires
REPLACE; Dry Run has no apply action. `b` optionally browses folders and `u`
previews undo. Direct equivalent: `riposte sort ROOT --categories`.

**Full Sort Workshop** (main-menu `8`) retains all earlier settings, discovery,
saved rules, assignments and undo. `g` changes its folder without losing settings.
Folder browsers keep `g` available at every depth, Enter opens the highlighted
directory and `s` uses it directly. Protection's multi-input browser retains Space
to select files/folders and `s` to select the current folder.

## Private library search

In the clean terminal library, press **s** for private search. Enter a title term,
an optional exact category folder, title availability, year/month or size. Run
the search, then use **[ / ]** for result pages, **s** or **/** to edit filters,
and **r** to restart from the current first page. **Enter** selects an image;
**i** inspects it; **p** opens the normal protection form. **a** selects only the
current page. No sorting, processing or publishing consent is implied.

The browser's **Private library search** navigation opens the same lookup, with
50 results per page. Filters update after a short typing pause; Enter searches
immediately. Clear search clears the title query. Other filters stay in effect.
Closing clears private text and results; nothing is placed in URLs or browser
storage. Inspect image passes only the canonical image ID to the existing viewer.

```powershell
riposte library-search "D:\Artwork" --search "moonlight"
riposte library-search "D:\Artwork" --category portrait --year 2025 --month March
riposte --json library-search "D:\Artwork" --title-state unknown --limit 50
```

Search uses literal Unicode NFKC/casefold matching across the original filename,
category, canonical path, date and ID. The category filter matches an exact saved
folder slug without case; all supplied filters combine with AND. Title state is
`all`, `known` or `unknown`. Results are images in the clean library; videos and
unsorted files are outside this lookup. Private titles must match catalog ID,
image type and stored hash. Missing, invalid or mismatched provenance is unknown;
numbered filenames never become guessed original titles. A matched record may
still have no original title. Current image bytes are audited when opened, not
hashed across the whole library during search.

The command returns at most `--limit` rows (default 50, maximum 500), ordered by
day descending, canonical path and ID. JSON includes `total`, `offset`,
`next_offset` and `revision`. Use the returned next offset with the same filters,
limit and `--expected-revision` for consistent paging. A changed catalog or
provenance rejects that revision; restart at offset 0. An offset beyond the end
returns an empty page. Each request scans the metadata snapshot once; it does
not create a persistent search index or modify the workspace.

**This command's output contains private filenames. Keep it local.** Ordinary
`list`, default API state, generated PNG metadata and publishing packs never
receive these private fields. Authenticated clients use `POST /api/library-search`
with filters in the JSON body; responses are not cached or retained as jobs.

## Duplicate Finder

Main menu **d** opens one scan-settings screen. Paste a folder with **g**, then
press **r** to scan. In the finding list, **1–4** selects All / DUPLICATE / MAYBE
DUPLICATE / CLOSELY RELATED; **/** searches every member path, **x** clears the
search, **Enter** opens evidence, **t** shows coverage, **e** exports a new report,
and **r** rescans. **g** changes the folder while preserving the prior report.
Arrows, Page Up/Down and Home/End navigate findings; Esc returns. There is no
source-removal action. Float folders are included independently of sorting.

```powershell
riposte duplicates "D:\Artwork"
riposte duplicates "D:\Artwork" --report "D:\Reports\duplicates.json"
riposte --json duplicates "D:\Artwork" --no-videos --no-include-float
riposte duplicates "D:\Artwork" --no-visual --report "D:\Reports\exact.csv"
```

JSON contains all recorded sources, groups, relationships, options, issues and
hashes. CSV contains all finding summaries and representative paths; use JSON
for every group member. Exports require an existing parent and a new `.json` or
`.csv` filename. Existing reports are not overwritten. Without `--report`, the
scan writes no application state. Human CLI output shows the first 100 findings;
`--json`, export, terminal navigation and browser paging retain the recorded set.

Limits default to 100,000 files, 10,000 distinct media fingerprints after byte
collapse, 100,000 visual pairs, 20,000 findings and 4 GiB per file. Override with
`--max-files`, `--max-visual`, `--max-pairs`, `--max-findings`, `--max-file-bytes`.
Hitting a limit reports incomplete coverage and retains available findings;
the direct command returns the shared incomplete-result exit code (2).

In `riposte serve ROOT`, open **Duplicate Finder** for filters, paired previews,
paged members, measured evidence and downloads. The browser uses the server's
folder and authenticated session, retaining the latest two scan reports in
memory. Standalone CLI/terminal scans skip private state without requiring a
valid sorted catalog; the browser server retains its normal workspace checks.
See [DUPLICATES.md](DUPLICATES.md) for the confidence policy and media boundaries.

## Storage and recovery inspection

Run `riposte health ROOT`, or open **Terminal & workspace > Storage & recovery**.
The browser has **Storage & recovery** in workspace navigation. Inspection is
optional; it does not add a sorting step or create private state.

```powershell
riposte health "D:\Artwork"
riposte --json health "D:\Artwork" --max-entries 200000
```

The report separates total logical bytes, private state, recovery within private
state, and `_float_` / `__float__` storage. Available volume capacity is separate.
The backup envelope counts observed media/sidecar suffixes outside private/float
storage, including already-sorted files. It is not a required-free-space or peak
estimate: extensionless images, decode expansion, temporary outputs and journals
remain unknown. Use a dry run for actual sort selection; enough reported free
space never guarantees a sort will fit.

Inspection defaults to 100,000 entries (maximum 200,000), a cooperative 30-second
budget, 128 nested open directories and 4 MiB per journal. Slow OS reads can
outlast that budget or delay cancellation. Links/reparse paths and other volumes
are skipped; inaccessible, changing or limited scans report INCOMPLETE and retain
partial totals. Logical bytes count hard-linked entries separately and differ
from allocated storage. Reads can update filesystem access times.

Windows volume flags report advertised hard-link support and read-only status;
POSIX statvfs reports read-only status with hard-link support unknown. Neither
runs a write, commit, lock or durability test. Unknown results stay unknown.
Recovery headers/entry shapes report APPLIED, APPLYING, UNDOING, UNDONE or
UNVERIFIED. They do not verify backups or undo conflicts. Preview undo performs
the existing recovery checks before any explicit restore.

Operation markers are observed without acquiring/reclaiming a lease. A marker
cannot establish whether its owner is alive or abandoned. Inspection never
prunes history or removes locks. Keep recovery copies private and together;
they retain original filenames, metadata and full video bytes.

## Command inventory

Every listed command is a real Typer command; use `riposte COMMAND --help` for parameter types, defaults, bounds and repeatable options.

| Command | Direct target | Effect |
|---|---|---|
| `ui [ROOT]` | Optional workspace | Native Rich menu; `--linear` explicitly permits scripted stdin |
| `organize ROOT` | Whole maintained workspace | Read-only plan; `--apply --plan-id PLAN_ID` replaces sources from the unchanged reviewed plan |
| `sort ROOT` | Whole maintained workspace | Alias of `organize`; incremental sorting without protection |
| `health ROOT` | Workspace storage and recovery | Inspect only; no writes, pruning or lock reclamation |
| `library-search ROOT` | Opt-in private title/category search; bounded result pages. No writes. |
| `duplicates ROOT` | Recursive files, independently of sorting | Read-only exact/visual comparison; optional explicit JSON/CSV export |
| `categories ROOT` | Filename stems under ROOT | Read-only term discovery and session category review; no media, catalog or rules writes |
| `category-rules ROOT` | Private rules and optional filename review | Read-only preview; `--save --expected-revision REVISION` explicitly saves rules; never moves media |
| `undo-sort ROOT` | Last recorded sort in this workspace | Read-only recovery preview; `--apply` restores originals if conflict checks pass; optional `--sort-id` binds confirmation to an exact preview |
| `riposte ROOT` | Repeated `--input` files/folders, or catalog selection | Protect independently; raw originals stay unchanged; `--plan` writes nothing |
| `sort-riposte ROOT` | Whole workspace, then catalog selection | Preview by default; `--apply --plan-id PLAN_ID` authorizes the reviewed sorting and protection choices |
| `audit ROOT` | Whole workspace | Inspect clean PNGs, artifacts, catalog and calendar/size rules |
| `list ROOT` | Filterable clean catalog | Inspect; `--year`, `--month`, `--size`, `--search`, `--offset`, `--limit` |
| `inspect ROOT IMAGE_ID` | Clean master | Verify exact bytes and print complete technical metadata audit |
| `publish ROOT` | Repeated `--input`, or `--image` repeated, or `--all` with filters | Generate final-size candidates; `--plan` is read-only |
| `recipes ROOT [NAME]` | Inspect/list; `--preview` drafts; `--save --expected-revision REVISION` saves | Reusable publishing settings only; no processing or approvals |
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
| `experiment ROOT [RUN_ID]` | All experiments or one | Inspect committed protocols, reviews and descriptive outcomes |
| `experiment-packet ROOT RUN_ID` | One experiment | Explicitly export concealed-label review material |
| `experiment-review ROOT RUN_ID` | One experiment | Record primary endpoint ratings against the committed run |
| `cohort-challenge ROOT` | Repeated `--trial`, `--model`, `--sample-size` | Commit a prospective cohort and attempt selected members |
| `cohort ROOT [COHORT_ID]` | All cohorts or one | Inspect membership, retained missing outcomes and finite-sample bounds |
| `panel-create ROOT` | Repeated `--run`, `--reviewers`, optional `--rubric` | Commit a fixed reviewer-calibration panel |
| `panel ROOT [PANEL_ID]` | All panels or one | Inspect protocol, packets, responses and descriptive agreement |
| `panel-packet ROOT PANEL_ID REVIEWER_ID` | One assigned reviewer slot | Explicitly export its concealed-label packet |
| `panel-review ROOT PANEL_ID` | `--ratings` JSON file | Record one final response for a reviewer slot |
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
open Full Sort Workshop and press `c`; edit Category groups and run again to review them.
Separate groups with commas in the form. The report shows matching-file counts
and title examples; Details retains the complete bounded report.

Discovery writes no media, catalog entries or saved rules. It does not
decode media or infer titles for numbered SML/MED/LRG/XTL files. Saved rules use
the separate command below. Exact destinations and private title provenance are available through the
separate opt-in sorting mode described below.

## Saved category rules

```powershell
# Preview a complete replacement ruleset and its filename matches. Writes nothing.
riposte category-rules ROOT --category "Hockey=hockey;goalie;goaltender" --exclude "Hockey=table hockey;toy" --priority "Hockey=10" --review

# First save: use the same selection and the revision from the preview.
riposte category-rules ROOT --category "Hockey=hockey;goalie;goaltender" --exclude "Hockey=table hockey;toy" --priority "Hockey=10" --save --expected-revision missing

# Reload the saved rules and review their matches without changing files.
riposte category-rules ROOT --review
```

Subsequent saves require the full revision printed by a fresh preview; a changed
ruleset stops the save. Saving replaces the **complete** category selection, so
repeat `--category` for every group to retain. `--clear` previews an empty ruleset;
combine it with `--save --expected-revision REVISION` to clear saved rules.

Aliases and phrases match complete normalized words wherever they occur in the
filename stem. Exclusions apply to that category alone. Higher priority wins;
equal highest priorities stay ambiguous without choosing an arbitrary category.
Unmatched and unknown titles still sort by date/media/size. Filename-only
discovery does not guess original titles from generated numbered names.

Folder slugs default to normalized category labels joined with hyphens. Use
`--slug "New label=existing-slug"` to retain a folder identity when renaming a
label. Duplicate slugs, Windows device names and unsafe path characters are
rejected; `uncategorized` remains a reserved explicit assignment for compatibility.
It is no longer inserted automatically for unmatched files. Unicode letters are
supported. Rules allow up to 32 categories, 32 included/excluded phrases each,
and priorities from -1,000,000 to 1,000,000. Phrases have one to three words.

Only the rules are persisted, in private `.riposte/category-rules.json` (or the
existing legacy `.shroud` namespace). Filename samples and review assignments
are not saved by this command. In the terminal Sort form press `s` to review
and save rules with a separate `SAVE` confirmation. The browser sorting dialog
also offers discovery, rule editing, review and explicit save.

## Exact category sorting

```powershell
# Inspect every destination. Does not create state or move media.
riposte --json sort ROOT --categories --date-mode modified

# Copy plan_id from that unchanged preview; repeat the same options.
riposte sort ROOT --categories --date-mode modified --apply --plan-id PLAN_ID

# Optionally assign a category to a tie or an old numbered file.
riposte sort ROOT --categories --assign "2025/March/img/SML/SML01.png=hockey"

# Preview and apply recovery separately.
riposte undo-sort ROOT
riposte undo-sort ROOT --apply --sort-id SORT_ID
```

The layout is `Year/Month/img-or-vid/[Category if found]/Size`, for example
`2025/March/img/hockey/SML/SML01.png`. A category plan shows source path, original
filename (unknown for old untracked files), matched terms, category and exact
numbered destination. Minimum discovery counts do not limit saved-rule matches.
Rules apply to words anywhere in the original title, including CamelCase boundaries.
Manual choices and saved rules take precedence. Otherwise supported local filename
patterns can propose categories in this same preview. Equal-priority rule ties,
weak patterns and unknown titles use the ordinary route without a category.
An existing category is preserved when no new saved-rule match is available;
confirmed folder labels guide later proposals without automatic renaming.
No rules or manual assignments are required, even with `--categories` enabled.

The actual calendar year and English month remain the outer folders. Existing
`EVERYTHING_ELSE` catalogs stay readable; sorting previews relocation using their
stored dates, with the usual consent and Undo. `--year` accepts any valid
four-digit calendar year, or `EVERYTHING_ELSE` for legacy entries.

Local analysis uses normalized filename families, supported phrases and observed
term associations. It needs at least six distinct families and three supporting
families per proposed anchor. Coverage/margin are heuristic scores, not probabilities.
Analysis is bounded at 50,000 families, 100,000 terms, 200,000 observed pairs,
48 terms per title and 32 groups; reaching a bound discards automatic proposals
and retains ordinary sorting and saved-rule matching. There is no automatic
rules save. `categories ROOT` additionally exposes these groups for optional
rule editing, using current filenames only; sorting also uses available private
original titles. See [the research review](research/sorting/RIPOSTE-REVIEW.md).

`--assign` repeats for multiple files. It uses a source-relative path and a saved
slug, or `uncategorized`. A manual choice persists across later sorts; `=auto`
clears it and tries the original title again. Repeat manual overrides when applying
the reviewed plan. The terminal accepts a JSON list for this field, preserving
commas inside filenames; the browser accepts one assignment per line.

`--plan-id` binds policy, rules, source identities/content, media catalog, private
assignments, versioned corpus evidence and exact destination allocation. Changed inputs require inspection
again. Late changes during an operation stop it with an incomplete checkpoint;
private undo history retains recorded work for recovery. Existing files are never
overwritten or assigned a different destination after approval.

New sorts retain trustworthy original basenames privately, including normal sorts
performed before enabling categories. Media IDs survive moves and identical bytes
in different files keep separate identities. Existing catalogs remain readable;
older numbered files without a trustworthy record sort without inventing titles
or requiring manual assignment. Removing a saved rule does not remove an existing
manual category choice. Image
metadata remains date-only; videos keep their bytes and metadata. Undo restores
the private provenance/assignments and both catalogs in one transaction. Rule
edits themselves are separate operations and are not undone with a sort.

`sort-riposte ROOT --all --categories` previews both stages. Its apply command
requires `--apply --plan-id PLAN_ID` from the **top-level combined preview**, not `sorting.plan_id`; model preflight still precedes sorting.
Protection consumes images only and its visual acceptance remains separate.

The local API exposes `POST /api/categories`, `GET/POST /api/category-rules`,
`POST /api/organize` and `POST /api/undo-sort`, all under the existing session
boundary. Organize accepts `categories`, `assignments` and `plan_id`; apply also
requires `acknowledge_source_removal`. Undo apply requires the reviewed `sort_id`
and `acknowledge_restore`. Browser controls use those same boundaries.

## Publishing configuration

`publish` accepts repeated `--image`, repeated `--vae` (up to four), repeated `--edge` (up to three), `--all`, `--year`, `--month`, `--size`, `--plan`, `--epsilon`, `--steps`, `--restarts`, `--seed`, `--device`, `--inpaint`, `--video`, `--preserve-white/--no-preserve-white`, `--delta-e76-p95`, `--rms-fraction`.

A model-dependent action with no usable model stops with a code; it does not add a cosmetic effect instead. Local paths are reselected on a later session because RIPOSTE does not save a model-path history. Four local encoders are not a promise that four large models fit available memory.

`--all` means all matching catalog images. For unorganized inputs, use repeated `--input PATH` with `riposte`, `publish`, or `protect`; a path can be a file or a recursively scanned directory. Relative paths use the current working directory. At most 200 distinct files are selected; overlapping paths are deduplicated. Non-image files are left untouched, corrupt image inputs stop intake, links/junctions are rejected, and internal `.riposte`/`.shroud` directories are excluded. Raw paths and metadata are not saved in batch records. `--date-mode download|modified|embedded` chooses the snapshot date basis. Originals stay where they are.

Use exactly one selection style: `--input`, `--image`, or `--all`. Date and resolution filters qualify `--all`; they cannot be combined with raw inputs or explicit IDs. Selected catalog sources are verified individually, so unrelated additions do not force sorting before a protection run.

```powershell
# Repeat only sorting when new images arrives.
riposte sort ROOT
riposte sort ROOT --apply --plan-id PLAN_ID

# Inspect recovery before explicitly restoring the last recorded sort.
riposte undo-sort ROOT
riposte undo-sort ROOT --apply --sort-id SORT_ID

# Protect selected originals without restructuring their directory.
riposte riposte ROOT --input "D:\Images\drawing.png" --input "D:\Images\New" --plan
riposte riposte ROOT --input "D:\Images\drawing.png" --input "D:\Images\New" --vae MODEL

# Preview both operations, then explicitly authorize source replacement.
riposte sort-riposte ROOT --all --vae MODEL
riposte sort-riposte ROOT --all --vae MODEL --apply --plan-id COMBINED_PLAN_ID
```

Copy `plan_id` from the preceding preview and repeat its options. Ordinary apply without an ID returns `SORT_PREVIEW_REQUIRED`; changed files, destinations, private state or policy return `SORT_PREVIEW_CHANGED`. Combined apply requires its top-level ID and also checks selection, recipe, device and model paths before model loading. Preview IDs are content receipts, not stored approvals or a live-directory mode.

Sorting checks catalog revisions throughout execution without reloading every
row for every input. External catalog changes produce `SORT_PREVIEW_CHANGED`
(or `CATEGORY_PREVIEW_CHANGED` in category mode); inspect incomplete work and
obtain a fresh preview before continuing. Existing journal-backed undo remains
available subject to its conflict checks. A catalog change during an audit
produces `CATALOG_CHANGED`; rerun the audit after the other writer has finished.
An individual image lookup uses its indexed ID and still validates that image's
path and bytes. A whole-workspace audit checks the complete collection.

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
riposte --json sort ROOT
riposte --human sort ROOT
riposte --plain sort ROOT
riposte --events --json sort ROOT
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

The source-migration preview shows the actual current plan, then `a` opens the explicit **REPLACE** boundary. Apply re-inspects the workspace and rejects a changed receipt before state initialization. Execution uses only the reviewed files and destinations. Later additions are retained and reported as incomplete; collisions never choose an unreviewed replacement destination. Ordinary sorting can still apply valid files from an unchanged plan with blockers, retaining undo for recorded changes. Category and combined sorting require a ready plan. Output acceptance has its own **ACCEPT** boundary and both underlying acknowledgements; a local viewer launch is not an acceptance event. The panel's numerical output checks are not an AI protection percentage.

## Linear interface

`riposte ui ROOT --linear` uses the same controller and service without raw key capture or animated updates. Useful typed instructions:

```text
4                         choose Image library from the home menu
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

Typed text in a field replaces that field; it is not interpreted as a command. No stdin script is accepted as an implicit interactive session: select `--linear` explicitly. A source migration in a script must still provide the explicit confirmation or use direct `organize --apply --plan-id PLAN_ID`.

## Images and exact frames

### Committed generation experiments

New `challenge` runs save a local protocol before the first generation call. It
fixes artifacts, model identity, conditions, seeds, views, controls, review
endpoints and analysis rules. This is local precommitment, not independently
timestamped preregistration.

```powershell
riposte challenge ROOT TRIAL_ID --model LOCAL_MODEL --task edit --seed 7 --view identity
riposte experiment ROOT
riposte experiment ROOT RUN_ID
riposte experiment-packet ROOT RUN_ID
riposte experiment-review ROOT RUN_ID --ratings COMPLETED_RATINGS_JSON
```

`experiment` lists completed, failed, cancelled and interrupted/open attempts.
With a run ID it verifies artifacts and shows the private protocol and all reviews.
`experiment-packet` explicitly writes
`.riposte/experiments/RUN_ID/review-packet.zip`, refusing to overwrite an existing
packet. Extract it outside the managed artwork folder. Read the instructions,
compare every frame of every sample to `reference.png`, and fill `ratings.json`
with `true`, `false` or `null` for task success, source preservation and usability.
Keep the protocol hash and every sample/endpoint key. Submit the completed file
with `experiment-review`; each submission creates a separate retained receipt.

Labels conceal conditions, but pixels may reveal them and the workspace owner
can unblind through the protocol. All three endpoints must succeed for joint
task success. Any null rating suppresses the aggregate contrast. Reported-filter
and clean-failed groups are excluded and counted. Other complete groups contribute
the mean of three control successes minus candidate success. The result remains
`ai_protection: UNVERIFIED`; one artwork's seeds/views are not independent artworks.
Unreported filtering is not proof of no filtering. Revisions are not pooled.

Legacy reports stay readable without retroactive protocols. The existing local
CUDA requirement remains; no models are downloaded. See
[PCUC-002 evidence and limitations](../evidence/pcuc-experiments/README.md).

### Local Kontext editing

Select a local Diffusers `FluxKontextPipeline` directory through the existing
editing commands:

```powershell
riposte challenge ROOT TRIAL_ID --model LOCAL_KONTEXT --task edit --seed 7 --view identity --steps 25
riposte cohort-challenge ROOT --trial TRIAL_A --trial TRIAL_B --sample-size 2 --model LOCAL_KONTEXT --task edit
```

The directory must contain the fixed transformer/VAE/CLIP/T5/tokenizer/scheduler
components and local safetensors. The VAE must have four levels and 16 latent
channels, and the transformer must accept 64 packed channels with guidance
embeddings. Linked/nested component directories, alternate executable weight
formats, custom component classes and optional IP adapters are not admitted.
Native CUDA bfloat16 is required; this backend has no CPU, quantized or offload
mode. Insufficient GPU memory is a load/execution failure, not permission to
silently change precision. The application does not acquire models or dependencies.

Each publication-transformed arm is resized explicitly to the closest aspect
ratio among 17 Kontext resolutions. Input-fidelity measurements describe these
prepared pixels. The recorded group includes `prepared_input_size`. The backend
disables additional automatic input resizing and matches output dimensions to the
prepared image. This may upscale small inputs or distort extreme aspect ratios;
the selected geometry is part of the measured task, not evidence of robustness
at arbitrary resolutions.

Kontext uses embedded guidance 2.5, true CFG scale 1 and a 512-token maximum;
it does not use the SD strength setting. The protocol, generation report, cohort
and review packet retain those settings. Every arm uses the same per-group seed.
Complete named model assets, including binary tokenizer data, are hashed before
and after loading. Only digests/counts and fixed technical fields leave that
inspection; arbitrary asset names and configuration text are not reported.

The model kind identifies the selected architecture path, not the origin/training
of its weights or an independently held-out family. No content-filter response is
reported by this path. Ordinary experiment/panel review and explicit UNVERIFIED
efficacy boundaries still apply. CPU tests with a tiny randomly initialized real
pipeline verify numerical plumbing; pretrained CUDA execution and useful editing
remain unqualified. See [PCUC-005 evidence](../evidence/pcuc-kontext/README.md).

### Committed artwork cohorts

Use a cohort to fix a sampling pool and analysis before running multiple artworks.
Each trial must represent a distinct source artwork; repeated source IDs and exact
clean rasters are rejected. Known completed generation on a pool source also blocks
intake. Use the existing `compare`, `guard` or `workshop` handoff to prepare trials.

```powershell
riposte cohort-challenge ROOT --trial TRIAL_A --trial TRIAL_B --trial TRIAL_C --sample-size 2 --model LOCAL_MODEL --task edit --seed 7 --view identity --steps 25
riposte cohort ROOT
riposte cohort ROOT COHORT_ID
```

The command selects without replacement from the explicit pool, records the draw
and all planned run IDs before generation, then uses one loaded local CUDA model
for every selected artwork. `--seed` controls generation; the sampling seed is
generated and retained separately. No selected member is silently replaced on
failure. There is no automatic retry within a cohort; a new command is separate
history and can be rejected if its sources already have generation outcomes.

Inspect a cohort to obtain member run IDs. Use `experiment-packet` and
`experiment-review` on those IDs as described above. The first complete review by
append sequence is primary. Incomplete drafts remain visible; later complete
revisions cannot replace the primary cohort result. Legacy reviews without an
append sequence retain their individual scope and cannot supply cohort ordering.

For each artwork, the cohort divides its paired contrast numerator by ALL planned
groups. Clean-failed and reported-filtered groups contribute zero and remain
counted. This availability-weighted score differs from the individual experiment's
conditional contrast over eligible groups. Selected artworks receive equal weight.
Failed, unattempted, unreviewed and incompletely reviewed members stay unknown in
[-1,1]; the report gives the corresponding possible range and suppresses a point
mean until every selected artwork is scored. These bounds are not confidence
intervals. Distinct rasters, local sampling and different model hashes establish
neither statistical independence nor held-out model-family coverage.

`cohort ROOT` lists committed protocol IDs; supply an ID for full artifact/review
verification and current missingness bounds. Local history is not independent
preregistration. See [PCUC-003 derivation and evidence](../evidence/pcuc-cohorts/README.md).

### Reviewer calibration panels

Calibration measures whether a task rubric produces consistent decisions on the
selected generated outputs. Choose completed experiment run IDs of one task:

```powershell
riposte --json panel-create ROOT --run RUN_ID --reviewers 3
riposte --json panel ROOT PANEL_ID
riposte panel-packet ROOT PANEL_ID REVIEWER_ID
riposte panel-review ROOT PANEL_ID --ratings completed-ratings.json
riposte --json panel ROOT PANEL_ID
riposte panel ROOT
```

Repeat `--run` to include more experiments. The panel accepts 2-8 reviewer slots,
up to 32 runs and at most 320 output sequences; repeated runs from one artwork
remain repeated observations. Creation returns a committed protocol containing
the panel ID and reviewer IDs. Each reviewer gets a separately ordered ZIP at
the returned local path. Its `instructions.json` contains the frozen rubric,
and `ratings.json` is the response form. Each item has its own reference PNG,
task settings and all output frames. Work through each complete sequence.

Assign each slot to a separate person yourself. The software neither distributes
packets nor authenticates people or actual viewing. Share only that reviewer's
packet; the private panel protocol contains the label mappings. Pixel content may
still reveal conditions. Fill every endpoint with `true`, `false`, or `null` for
uncertainty, and submit only once finished. Each slot records one final response,
including null decisions. `PANEL_REVIEW_EXISTS` prevents replacement; use a new
panel for corrections and retain the original calibration result.

Built-in edit, inpaint and video rubrics have explicit yes/no/uncertain anchors
and are **unvalidated candidates**. To revise wording, save the `protocol.rubric`
object from a panel as a JSON file, edit its name/instructions/endpoint anchors,
then create a new panel with `--rubric rubric.json`. The schema, task, three
endpoint keys and `UNVALIDATED_CANDIDATE` marker must remain intact. Custom text
is included in packets; inspect it before sharing. Existing panels retain their
original rubric even if the external JSON changes.

Inspect by ID to verify the bound trial, generation, packet and response bytes.
List mode checks protocols only. Missing packets/receipts or changed artifacts
fail validation; an interrupted export leaves the committed panel visible and
cleans its temporary ZIP. An orphan final ZIP without its receipt is reported as
`PANEL_PACKET_INCOMPLETE`; preserve it and create a new panel.

The report retains all planned items and slots. Null/unsubmitted ratings keep
point agreement incomplete and produce exact binary-completion bounds. Per-pair
Cohen kappa is withheld when that pair has missing decisions; constant identical
marginals are explicitly undefined. Raw contingency counts and disagreement item
IDs remain available. Pair indices map to `analysis.reviewer_order`; item indices
map to `analysis.item_order`. No threshold automatically validates a rubric.
There are no confidence intervals, population reliability claims or efficacy
verdicts. Panel responses do not replace experiment/cohort primary reviews.
See [PCUC-004 derivation and evidence](../evidence/pcuc-review-panels/README.md).

### Viewing exact pixels

The terminal's thumbnail is a composition aid. `image --open` hands verified PNG bytes to the local OS viewer. Transformed publication/trial previews are newly audited date-only PNGs cached under `.riposte/terminal-previews/`; raw image metadata, source paths and view reports are not copied into those PNGs. These cache images participate in the existing artifact audit. Canonical masters support identity inspection only; unsupported master-view combinations are rejected rather than silently ignored.

`frame` requires an exact allowlisted report-relative name, such as `V00-S00-clean/F000.png`. Absolute paths, parent traversal, an unlisted frame, a changed hash or a changed date cannot pass the existing generation-frame reader.

## Exit and compatibility

Direct results preserve the existing JSON payloads and positional ROOT/ID conventions. Exit status 2 also reflects incomplete checkpoints or blocked publishing items; it is not solely a parser error. Sensitive argument values and underlying exceptions are not echoed. Use the command help to correct invalid inputs.

Old SHROUD state stays readable until explicitly upgraded. v0.2/v0.3 workspaces need no catalog rewrite to use this terminal. The prior argparse source is retained as history, not a second executable command implementation. Later browser and engine changes are recorded with their own evidence in [project status](PROJECT-STATUS.md).

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

### Preview receipt API contract

`POST /api/organize` without `apply` returns a read-only job result containing
`plan_id` and per-file destinations for ordinary and category sorting. Submit
the same options with `apply: true`, `acknowledge_source_removal: true`, and
that `plan_id`. A missing or stale ordinary ID becomes a job error with
`SORT_PREVIEW_REQUIRED` or `SORT_PREVIEW_CHANGED`. Inspect again after changes;
acknowledgement alone does not permit a new directory scan to expand the work.

## Named publishing recipes

The same library is available from the terminal and browser publishing forms.
See [publishing recipes](PUBLISHING.md#reusable-publishing-recipes) for scope.

```powershell
riposte recipes ROOT
riposte recipes ROOT "Web art" --preview --edge 1536 --seed 19
riposte recipes ROOT "Web art" --save --edge 1536 --seed 19 --expected-revision missing
riposte recipes ROOT "Web art"
riposte riposte ROOT --input ART --recipe "Web art" --plan
riposte publish ROOT --all --recipe "Web art" --edge 1024 --seed 7 --plan
```

`missing` is valid only for the first library save. For later saves, supply the
current `revision` returned by preview. Repeat the reviewed settings when saving
from the CLI. Saving a matching name replaces that entry, preserving others.
All eight settings flags are supported on `recipes`; unsupported/private fields
are rejected. Inspection and preview do not create a workspace or load models.

On `publish`, `protect`, `riposte` and `sort-riposte`, explicit flags override
saved settings; omitted flags keep the recipe's values. `--recipe-revision` can
pin the selected entry's `recipe_revision` returned by inspection. Browser and
terminal loads pin it automatically. An edited saved recipe then requires a fresh
load/preview; unrelated saved recipes do not invalidate that entry.

### Optional artist budgets

Publishing aliases (`publish`, `protect`, `riposte`, `sort-riposte`) accept
`--budget-mask PATH` for exactly one selected source or `--budget-map PATH` for
source-bound masks exported by browser publishing. Both remain optional.
`--plan` includes final-size budget summaries, cap PNGs, overlays and a
`budget_revision`. `--view-budget N` with an ordinary or standalone `--plan`
explicitly opens that numbered overlay in the local viewer and writes a private
date-only preview cache. Combined sorting retains its existing plan/consent flow.
`--budget-revision HASH` rejects changed masks, sizes or limits before processing.
See [artist masks](PUBLISHING.md#artist-masks) for format and privacy details.

Raster previews return at most three at a time. Browser Previous/Next previews and
terminal `[ / ]` retain the full batch selection. CLI `--budget-offset N --plan`
selects a preview page; `--view-budget N` opens an absolute numbered preview.
Processing skips preview rendering, so pagination never limits batch size.
