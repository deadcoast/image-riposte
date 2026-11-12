# Interactive entry and image workflow contract

Recovery owner: `recovery.py`, `static/recovery.js` and the shared packaged
`static/recovery-catalog.json`. Direct errors, job failures and blocked sort/undo
previews use the same code and action. Unknown codes keep their sanitized machine
identity and get an operation-specific safe fallback. Missing catalog data leaves
the original safe code visible and asks the user to inspect status before retrying.

Browser errors are persistent dismissible notices (or inline sorting errors),
visible within the active modal. Success notifications remain temporary toasts.
Dismissal does not retry, reset input or discard a draft. Failed network responses
do not imply that a write stopped. Locks are never deleted by guidance; interrupted
sorts lead to an undo preview and integrity blockers stay in force. Category ties,
unmatched names and missing original titles are informational: the normal
Year/Month/media/size route remains available, retaining any existing category.

Owner: `terminal/controller.py` for navigation and operation consent;
`terminal/paths.py` for read-only browsing; `terminal/interaction.py` for shared
controls/help; `terminal/service.py` for the operation boundary shared with CLI.

Duplicate Finder business source: the user's 2026-09-20 request preserved in
`todo-audit.PACER.md`; its implemented comparison/coverage contract is
`docs/DUPLICATES.md`. It is an independent read-only operation. Scan consent is
the Scan/Run action, with separate explicit report export. There is no automatic
keeper choice, removal, sorting or upload. Float exclusions remain sorting-only.

Duplicate flow: folder/settings → cancellable scan → filterable findings →
evidence/members/paired browser thumbnails → optional JSON/CSV export. Failed or
cancelled rescans retain a clearly labelled previous report; incomplete coverage
does not hide successful findings. Source changes require rescanning. Browser
reports are session-memory records (latest two); expiration offers rescan, not
an empty-success claim. DuplicateReview owns filters, pagination and export;
the terminal and browser share those meanings. Exact groups and similarity pairs
are never conflated through transitive grouping.

The duplicate screen uses native labelled selects, checkboxes and number inputs.
`duplicates.js` owns inline form validation, result/detail request revisions,
per-container member request ownership and explicit downloads. No floating layer
or new focus trap is introduced. Global / stays in duplicate search. Existing
scrollbars, buttons, feedback and token owners remain canonical; the main view
and selected relationship are labelled regions with keyboard-operable actions.

- `START.ps1`, `START.cmd`, `START.sh`, and a no-command `riposte` launch open the
  main menu. A folder argument is optional. START never installs packages or
  requests a path before the menu. INSTALL handles explicit setup and returns.
- Arrows move focus; Enter opens the highlighted action; visible menu numbers
  are equivalent shortcuts. Esc returns and restores the previous focus.
  Each isolated press, including the first reversal, must update focus without
  a later key to release it. Windows extended-key prefixes consume their cached
  scan code immediately; a second keyboard-availability poll is not appropriate.
- Riposte Sorter is the default first action, exposing exactly Sort, Dry Run and
  Enter Path. The session retains the selected root. Its preset uses download
  dates, saved rules and supported filename patterns with Year/Month/img-or-vid/[Category if found]/Size.
  Missing or tied matches use the ordinary route. It never infers rules or sidecar
  deletion. Full Sort Workshop owns the existing configurable flow.
- Sort explains its recursive folder scope before selection. It previews
  sanitation/organization and requires the exact `REPLACE` confirmation before
  replacing verified sources. Confirmation carries the displayed `plan_id`.
  File, destination, private-state or policy drift requires a new preview.
  Sidecar deletion has its own explicit option.
- Dry Run exposes no apply action; Enter returns to the sorter. Sort uses the
  existing result and exact confirmation owners. After apply or rejection of a
  stale plan, returning goes directly to the sorter without reusable consent.
- `g` pastes into an empty field in the sorter, workshop and every picker level.
  Invalid input retains the old root. Picker `s` directly accepts the highlighted
  folder for a single-folder choice. Location rows survive ignored input; arrows
  and Enter consume a stable displayed list. Directory-entry attributes avoid
  repeated filesystem probes when listing folders. Input bursts drain before
  redraw; static screens repaint only on input or resize. Queued input is bounded
  per drain without dropping events or turning partial escapes into shortcuts.
- Sort previews show separate `img` and `vid` routes inside dated folders.
  Videos retain their bytes and metadata and never enter protection selection.
  Consent explains that private original copies are retained for recovery.
- Undo last sort is visible in the main menu and on the Sort form (`u`). Its
  read-only preview precedes an exact `UNDO` confirmation bound to that sort ID.
  Conflicts stop restoration; returning from either screen changes no files.
  Older sorts without recovery records explain why undo is unavailable.
- RIPOSTE browses independently selected files/folders, then asks where to save
  its clean snapshots, candidates, and review records. Inputs stay in place.
  Space toggles selections, Enter opens folders, `s` selects the current folder,
  Backspace goes to its parent, and `l` opens home/drive locations. `g` optionally
  accepts a pasted folder path. Selection itself performs no image writes.
- Sort + RIPOSTE previews both operations and requires `REPLACE`. Model preflight
  occurs before sorting; the top-level combined receipt binds both the nested
  sort plan and the selected protection configuration. A failed sort blocks protection. Protection may be
  retried separately after sorting.
- Empty selections remain in the browser with a useful message. Unreadable
  folders retain parent/location navigation. Invalid pasted locations retain
  input for correction. Cancel never starts an operation. Application folders
  and image/results folders must not overlap. Linked locations are rejected.
- Choosing another input selection preserves configured protection settings.
  Local model directories can be browsed without first choosing an image root.
- Candidate creation, visual acceptance, and experimental protection efficacy
  remain separate. Packaging includes only explicitly accepted exact outputs.
  Native viewer/browser handoff remains explicit. Background jobs retain safe
  stop/join behavior before exit.

The browser web application keeps its existing capabilities. Current copy uses
image terminology; this terminal entry change does not introduce the new file
picker into the web interface. Direct command names remain available. PAC-031 requires `--plan-id` for every
sort apply, including ordinary sorting and the combined command; JSON previews
add the receipt and exact per-file destinations. `-ArtworkFolder` remains a PowerShell alias for
`-ImageFolder` so existing invocations keep working.


## Category sorting (PAC-027BB)

The PAC-027 plan in `todo.PACER.csv` authorizes optional
Year/Month/img-or-vid/Category/Size sorting. `category_rules.py` owns rule
validation; `category_sort.py` owns the frozen read-only destination plan;
`organizer.py` and `sort_history.py` own consent checks, replacement and undo.
The public image/video catalog keeps its existing schema. Original titles and
assignments live in its separate private `sort_titles` table and private undo
journals; they are never PNG metadata or publishing pack contents.

- Direct commands and Full Sort Workshop default to the existing layout;
  Riposte Sorter enables saved rules and local corpus proposals. Enabling categories requires a fresh
  exact plan. Every file shows its source, original title (or unknown), matched
  terms, category and destination. A changed setting, rule revision, catalog,
  source or occupied destination invalidates apply consent.
- Category matching enriches the route and is never a prerequisite for sorting.
  Missing rules never block sorting. Weak patterns, ties and unavailable original titles use
  the ordinary date/media/size route. Keep existing category folders when there
  is no new match; stored manual choices survive rule removal. Explicit `=auto`
  clears a manual choice and uses current matches or the ordinary route. Preserve
  truthful unknown titles. This user correction supersedes earlier mandatory-
  assignment interpretations; see `evidence/optional-categories/`.
- Corpus proposals appear inside the existing preview, with matched evidence,
  IDF coverage and margin explicitly identified as heuristic. Manual choices and
  saved rules win; automatic rediscovery never renames existing categories.
  Uncertainty and analysis limits use ordinary sorting. Discovery can fill an
  optional rule draft from a group; review and explicit SAVE remain separate.
  Actual calendar years appear in the browser tree and year filter, including
  readable legacy EVERYTHING_ELSE entries. No added setup screen or UI token.
  See `evidence/sorting-research/` for bounded runtime and native evidence.
- Full Sort Workshop exposes `s` for saved rules, `c` for discovery, `u` for
  undo, a category toggle and manual assignments. Rule replacement requires
  `SAVE`; file replacement requires `REPLACE` with the plan ID from the result.
  Sort + RIPOSTE binds that nested sorting plan in its top-level receipt and
  rechecks it after the separate model preflight.
- The browser sorting dialog uses the existing native modal, form controls,
  buttons and palette. Native select popup geometry is deliberately platform
  owned. Escape closes the dialog and returns focus; drafts remain in memory.
  Rules have separate discovery, draft review and explicit save. Saving never
  starts a sort. A saved-rule revision conflict preserves the draft for review.
- Manual assignments use source-relative paths and saved category slugs (or
  `uncategorized`). `auto` clears a manual override. Old numbered names without
  trustworthy provenance cannot be treated as descriptive titles.
- Browser requests disable duplicate writes synchronously. A late inspection
  cannot restore apply after settings change. Ordinary and category plans both
  require a receipt before acknowledgement enables Apply. Ordinary destination
  rows show source, action and exact destination without category-only warnings. Errors stay in the dialog with
  corrective text; failure keeps the draft and requires a refreshed preview.
  Undo has its own preview, acknowledgement and exact sort ID.
- The dialog owns vertical scrolling; all actions remain reachable on narrow
  screens. Destination lists wrap full filenames rather than truncate them.
  This English-language workflow accepts Unicode titles/categories; it does
  not claim translated UI or cross-platform assistive technology certification.

### Terminal polish and reserved user storage / 2026-09-20

- Folder paging matches the visible row count. Both Backspace and the parent
  row restore the child folder's focus. Failed navigation retains the current
  selection. Invalid pasted paths retain input and show actionable correction.
- Blocked sorter previews show BLOCKED and Return, with `w` opening Full Sort
  Workshop using the reviewed settings. Empty/already-sorted previews show
  NO CHANGES and cannot open unnecessary REPLACE confirmation. Dry Run cannot
  apply. Read-only sort/undo previews do not reload unrelated publishing history.
- Confirmation displays the bound root, complete replacement/undo warning, and
  working F1/F4 help/command views. A submitted confirmation and consumed preview
  leave the back stack on success or failure; cancellation before submission
  still returns to the preview. Failed sorter results retain `g` path recovery.
- `policy.FLOAT_DIRECTORIES` and `sort_excluded` own the exact case-insensitive
  `_float_` / `__float__` directory rule. The organizer prunes these subtrees
  before reading media; ordinary/category planners, discovery and organization
  audit use the same scope. A selected sort root inside either is refused before
  workspace initialization. Similarly named files and directories are included.
- The exclusion applies to menu, CLI, API and combined sorting through the shared
  engine. It does not apply to `intake.input_files`: standalone RIPOSTE can process
  float storage, even using it as its results workspace. Existing explicit undo
  follows its recorded journal; the rule does not rewrite historical recovery.
- No optional model or protection efficacy is qualified by synthetic CPU tests.
  PACER reconciliation resumed on 2026-09-20; clean-install qualification remains shelved.

### Browser scan jobs / PAC-035 / 2026-09-20

- Category discovery, rule review, ordinary/category previews and undo inspection
  return authenticated job IDs. Clients poll `/api/state`; read-only scans support
  `/api/jobs/{job_id}/cancel` at the next scan checkpoint. Loading saved rules remains
  a direct bounded request. Saving rules is a non-cancellable write job.
- The active phase, available counts and Cancel appear inside the sorting dialog.
  Cancellation requested and cancelled are separate states. No usable preview or
  review result is published after cancellation, even at the completion boundary.
- Discovery, rules and sort settings carry separate revision checks. Old replies
  cannot overwrite newer input or authorize replacement. Closing invalidates
  receipts and acknowledgements; input text remains available on reopening.
- Shutdown rejects new jobs and signals cancellable work. Already accepted sort,
  undo and rule-save commits may finish; cancelling a scan grants no write consent.
- Actual Chromium and server evidence is in `evidence/pacer-resumption/`.

### Canonical UI Map

PAC-037 replaces browser syntax textareas with structured rule fieldsets and
native per-file selects; CLI and terminal expert syntax remain compatible.
Field errors retain input, associate correction text with the input, and focus
the first invalid field on Review. Loaded slugs survive label-only renames.
Saved rules load automatically on first category use unless the user has already
edited a draft. Reloading an edited draft needs the inline discard choice.
Closing keeps inputs and choices while invalidating review/preview receipts.
Review is read-only; Save binds the reviewed revision and never starts sorting.

File choices use saved categories, not draft rows or inferred corpus labels.
Keep current choice omits an override; Automatic explicitly clears a manual
override; Uncategorized explicitly selects that folder. A choice invalidates
the exact preview and acknowledgement. Paging retains choices, with 50 rendered
file controls per page. Reset pending file choices also recovers a removed file
or category. Failed loading exposes Reload category choices while ordinary
inspection stays available. Transient private drafts, paths and paging stay in
memory, with no URL/localStorage persistence. Browser keyboard and real-server
save/conflict/sort/undo evidence: `evidence/guided-category-editing/`.

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Form | `static/index.html`, `static/category-sort.js`; terminal field schema | PAC-027 consent and shared server rule parser | Structured browser fieldsets, phrase lists and inline errors; terminal expert syntax | CLI/API/controller tests, Chromium state matrix and real-server save/sort/undo |
| Select/Listbox | Native HTML select; terminal choice field | Date policy enum in `policy.py` | Platform popup geometry accepted | Browser keyboard and narrow viewport checks |
| Date | `Policy`, `extract_day` | Date-only output policy in README | Existing download/modified/embedded enum; no calendar widget | Organizer regression tests |
| Scrollbar | `static/style.css` | Existing runtime palette tokens | Dialog/list geometry, forced-colors system baseline | Chromium viewport assertions and screenshots |
| Toast | Shared `app.js` toast | Existing live status region | Persistent sorting errors also appear inline | Error/retry browser checks |
| CRUD | Rules service and sorting/undo service | PAC-027 and `category_rules.py`/`sort_history.py` | Review then replace complete rules; clear explicitly; no autosave | Stale revision and exact recovery tests |
| Table Selection | Existing publication/library owners | Independent image selection policy | Category destination rows are read-only, with no row selection | Existing browser/publication regression suite |
| Terminal menu and folder selection | `terminal/controller.py`, `paths.py`, `render.py`, `keyboard.py`, `app.py` | Three-action user request and existing operation consent | Riposte Sorter preset; Full Sort Workshop configuration; multi-input protection | `tests/test_sorter_menu.py`, `tests/test_terminal_polish.py`; final Windows ConPTY checks in `evidence/terminal-polish/` |
| Sorting exclusion | `policy.FLOAT_DIRECTORIES`, `sort_excluded`, shared sort planners/walker | User's `_float_` / `__float__` storage rule | Exact case-insensitive directory names at any depth; protection intake remains available | `tests/test_float_sort.py`, synthetic protection/combined tests in `tests/test_workflows.py` |
| Optional categories | Shared `category_sort.category_plan` and saved-rule matcher | User correction: categories apply if found | Ordinary route for absent/tied/unknown matches; retained existing categories; optional manual choices | `tests/test_optional_categories.py`, CLI/API/video/combined checks and actual launcher sort/undo in `evidence/optional-categories/` |

## Named recipe boundary / PAC-040

Recipes are optional publishing configuration, never processing consent. CLI,
terminal and browser share the same bounded, versioned workspace library and
validation. List/inspect/preview are read-only; an explicit save checks the
reviewed library revision and atomically replaces one named entry. Corrupt,
linked or unsupported state is preserved for recovery. Loading a saved entry
fills all eight supported fields, including custom sizes and seed, and pins that
entry's revision. Later edits remain editable but must pass current engine checks.
A changed saved entry must be reloaded; a combined sort still needs a fresh exact
preview and explicit replacement consent. Saved recipes cannot provide model
paths, identities, source selection or visual/export approval.

The browser uses existing authenticated API/error helpers and a native recipe
selector. No automatic save or retry; pending/empty/error/conflict states are
visible. Keyboard selection and a 390px viewport are regression checks, not
independent assistive-technology or human usability certification.

## Storage and recovery inspection / PAC-041

`health.py` owns read-only observations; CLI and terminal share the service and
semantic report. Terminal workspace settings open the report directly. Browser
workspace navigation opens a native modal using the shared dialog styles, button
classes, runtime tokens, global scrollbars and authenticated `app.js` job owner.
The action remains visible at narrow widths. `health.js` owns only this report's
layout and job identity; it reuses shared recovery text. Close/Escape returns
focus to the opener, retains an in-flight inspection, and late completion never
reopens the dialog. Re-inspection hides stale totals; errors remain inline with
a retry action. Partial results, unknown capabilities and unverified histories
are explicit. Cancellation discards the report without touching files. No new
fonts, theme tokens, native select or stored browser data are introduced.


## Private library search / PAC-042

The English local desktop workbench keeps its current tokens, typography,
buttons, native selects, dialog and global scrollbars. `library_search.py` owns
literal Unicode matching, catalog-bound provenance, unknown states and paging.
The terminal shares its worker, action form and library selection. `library-search.js`
owns the browser dialog's transient query and rows; `app.js` owns authenticated
requests, existing canonical selection and shared errors. `publish.css` owns the
new list geometry only. Native select popup geometry remains platform owned.

Opt-in navigation opens a 50-row private result list. Private values never enter
the normal gallery state, URLs, localStorage, ordinary catalogs or retained jobs.
Closing aborts pending fetches, clears text/results and restores opener focus.
Remote input waits 300ms and respects IME composition; explicit submit/clear does
not wait. Input changes immediately discard old rows, disable paging and revoke
older responses. One revision binds pages; stale data requires restart without
changing selected image IDs. Inline errors retain filters; date errors open their
collapsed disclosure and focus the offending field. No mutation confirmation is
added. The dialog owns outer scrolling; long titles/paths wrap and filters stack
below 600px. Read-only search and existing image operations remain separate.

Artist-budget business source: [publishing mask contract](PUBLISHING.md#artist-masks),
implemented by `spatial.py`, `quality.py`, `publication.py` and `release_guard.py`.
The optional disclosure uses existing selection, native controls, authenticated
API, errors and page scrolling. Upload validates before attachment; failed replacement
retains the prior mask. Cancellation/generation checks reject stale replies and
changed settings discard previews. Remove has no extra confirmation. Explicit
export downloads a private map; general recipe saves exclude masks. Keyboard mask
previews in terminal use the existing local viewer and cannot record approval.
Numeric quality, overlay inspection and exact output approval remain separate.
