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
  replacing verified sources. Sidecar deletion has its own explicit option.
- RIPOSTE browses independently selected files/folders, then asks where to save
  its clean snapshots, candidates, and review records. Inputs stay in place.
  Space toggles selections, Enter opens folders, `s` selects the current folder,
  Backspace goes to its parent, and `l` opens home/drive locations. `g` optionally
  accepts a pasted folder path. Selection itself performs no image writes.
- Sort + RIPOSTE previews both operations and requires `REPLACE`. Model preflight
  occurs before sorting; a failed sort blocks protection. Protection may be
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
picker into the web interface. Existing direct command names/options and JSON
record keys remain compatible. `-ArtworkFolder` remains a PowerShell alias for
`-ImageFolder` so existing invocations keep working.
