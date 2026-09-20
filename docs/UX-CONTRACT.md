# Interactive entry and image workflow contract

Owner: `terminal/controller.py` for navigation and operation consent;
`terminal/paths.py` for read-only browsing; `terminal/interaction.py` for shared
controls/help; `terminal/service.py` for the operation boundary shared with CLI.

- `START.ps1`, `START.cmd`, `START.sh`, and a no-command `riposte` launch open the
  main menu. A folder argument is optional. START never installs packages or
  requests a path before the menu. INSTALL handles explicit setup and returns.
- Arrows move focus; Enter opens the highlighted action; visible menu numbers
  are equivalent shortcuts. Esc returns and restores the previous focus.
- Sort explains its recursive folder scope before selection. It previews
  sanitation/organization and requires the exact `REPLACE` confirmation before
  replacing verified sources. Confirmation carries the displayed `plan_id`.
  File, destination, private-state or policy drift requires a new preview.
  Sidecar deletion has its own explicit option.
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

- Sort defaults to the existing layout. Enabling categories requires a fresh
  exact plan. Every file shows its source, original title (or unknown), matched
  terms, category and destination. A changed setting, rule revision, catalog,
  source or occupied destination invalidates apply consent.
- The terminal Sort form exposes `s` for saved rules, `c` for discovery, `u` for
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

### Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
| --- | --- | --- | --- | --- |
| Form | `static/index.html`, `static/category-sort.js`; terminal field schema | PAC-027 consent and rule grammar | Native inputs and textareas; terminal JSON assignment list | CLI/API/controller tests and real Chromium state matrix |
| Select/Listbox | Native HTML select; terminal choice field | Date policy enum in `policy.py` | Platform popup geometry accepted | Browser keyboard and narrow viewport checks |
| Date | `Policy`, `extract_day` | Date-only output policy in README | Existing download/modified/embedded enum; no calendar widget | Organizer regression tests |
| Scrollbar | `static/style.css` | Existing runtime palette tokens | Dialog/list geometry, forced-colors system baseline | Chromium viewport assertions and screenshots |
| Toast | Shared `app.js` toast | Existing live status region | Persistent sorting errors also appear inline | Error/retry browser checks |
| CRUD | Rules service and sorting/undo service | PAC-027 and `category_rules.py`/`sort_history.py` | Review then replace complete rules; clear explicitly; no autosave | Stale revision and exact recovery tests |
| Table Selection | Existing publication/library owners | Independent image selection policy | Category destination rows are read-only, with no row selection | Existing browser/publication regression suite |
