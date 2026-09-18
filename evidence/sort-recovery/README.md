# Reversible image/video sorting — bounded validation

PAC-023 / NDL-013 implements the user's undo, preview and sort-only video request.
The original request is preserved in PACER. This evidence uses synthetic files;
it does not establish protection efficacy or claim GPU/model execution.

Implemented behavior:

- Direct `sort`/`organize` and the terminal Sort action retain read-only previews.
- New sorts retain original bytes and paths privately before source removal.
  `undo-sort` previews recovery; `--apply` restores it after conflict checks.
  The menu requires `UNDO` and binds that consent to the previewed sort ID.
- History supports multiple successive undos, partial sorts, interrupted undo,
  sidecar restoration and legacy `.shroud` state upgrades. Already completed
  pre-history sorts cannot be recovered. Private copies retain metadata and use
  disk space; they are excluded from publishing inputs and ZIPs.
- Images use `Year/Month/img/Size`; videos use `Year/Month/vid/Size`. Video bytes
  remain unchanged, with a separate video catalog and no protection selection.
  Existing image IDs survive migration from the previous folder layout.
- `ffprobe` is an optional external requirement for video inspection. INSTALL
  reports availability. No Python dependencies or lockfile changes were needed.

Executed checks:

| Check | Actual result |
| --- | --- |
| Initial regressions (`before.txt/xml`) | Two expected failures: missing undo and missing img layer |
| First backend run | 22 passed, 1 skip, 2 old-contract failures; original no-backup assertions revised to preserve the private recovery exception |
| Expanded backend/workflow checks | 105 passed, 1 platform skip |
| Initial complete suite (`full-first.txt/xml`) | 906 passed, 7 platform skips, native-browser navigation timeout in sandbox |
| Browser suite outside sandbox (`browser.txt/xml`) | 21 passed, including native Chromium DOM review |
| Final suite excluding separately verified browser tests (`suite-final.txt/xml`) | 892 passed, 7 platform skips |
| Final recovery/video tests (`recovery-final.txt/xml`) | 29 passed; real MP4, MOV, MKV, WEBM and AVI fixtures |
| Final source/stub suite (`contracts-final.txt`) | 356 signatures, 42 importable leaf modules; strict external consumers, stubtest, 9 runtime fixtures, tooling checks and 13 expected negative diagnostics pass |
| Source-body mypy (`source-mypy-current.txt`) | Still fails: 1057 errors in 37 files, 45 source files checked. External contracts do not make the implementation type-clean |
| Actual Windows ConPTY (`native-console-*.json/txt`) | START.ps1 and START.cmd open the keyboard menu; arrows/Enter, independent actions and Undo selection work; exit restores cursor |
| Source distribution/wheel/isolated target (`package.json`) | Exact package bytes equal checkout; 31 commands; three workflow previews; real synthetic image sort and undo; actual Windows launcher/wrapper smoke checks |

Total distinct current application tests: **913 passed, 7 skipped**. The seven
skips concern unavailable Windows symlink privileges and POSIX-only PTY tests.
The browser timeout and earlier failures remain preserved.

`home-small.png`, `home-wide.png` and `browser-small.png` are images of production
renderer cells, not native screenshots. The 72×24 main menu was visually checked;
all nine actions and keyboard hints are visible. ConPTY is separate native proof.

Recovery limits: original file bytes, names and modified timestamps are restored;
this is not a filesystem/ACL snapshot or forensic erasure. Concurrent external
editing is not coordinated by the application lock. A hard process kill or power
loss can leave `operation.lock`; verify the process has stopped before removing
a stale lock and previewing recovery. Conflicting files, damaged backups and
invalid journals fail closed. The recovery store must remain with the library.
Protection outputs, review records and existing packs remain in place; resuming
a batch whose catalog source was undone requires restoring that source first.
