# Filename discovery and session review / PAC-027A

This is the first milestone of PAC-027, resumed by the user on 2026-09-18.
It reads filename stems and returns recurring terms, bounded examples and explicit
category-group matches. It does not validate media contents, persist rules,
assign physical folders, recover original titles from journals, or move files.
Those remaining stages are tracked by PAC-027B; the parent remains incomplete.

Run `riposte categories ROOT` or choose Sort and press `c`. Return from the
report to edit the group field. `Hockey=hockey` selects/renames a term;
`Hockey=hockey;goalie;goaltender` merges terms only because the user supplied them.
Separate groups with commas in the form; repeat `--category` in direct commands.
Clear a group to remove it, or use Ignore suggestions to hide candidate terms.
Manual groups are independent of discovery thresholds and fillers. Overlaps are
reported without choosing a winning category. An unmatched `Uncategorized` label
is a proposal only. No session selection authorizes source replacement.

Validation logs are retained here, including the first focused run's test-harness
case mismatch (the renderer intentionally uppercases report titles). The corrected
assertion still checks the rendered report heading and bounded widths.

- `baseline.txt`: pre-edit sorting/recovery/terminal regressions, 188 passed and
  one unavailable symlink test skipped.
- `focused.txt`: filename counting, Unicode, phrase adjacency, explicit groups,
  no media opens/state writes, generated-name exclusion, link pruning, incomplete
  scans, cancellation, limits, CLI/form parity and synthetic terminal rendering.
- `large-folder.json`: measured discovery over 10,000 actual directory entries
  with synthetic media names; the empty files are not decodable image fixtures.
- `suite.txt` and `contracts-first.txt`: broad runtime and external typing checks.
- `source-review.json`: seven admitted application files; the other 45 match the
  previous reviewed snapshot. Prior snapshots and prior evidence remain historical.

Resource bounds: at most 100,000 distinct terms, 500 returned candidates, 0-10
examples per term (3 by default), 32 draft groups and 32 matchers per group.
The vocabulary cap fails visibly rather than returning biased partial suggestions.
The walker still holds the names of one directory while enumerating that directory.
Pure numeric tokens and fillers break phrase adjacency. Names are NFKC/casefold
normalized; no stemming, synonym inference, metadata or model analysis occurs.
All `.riposte`/`.shroud` directories are pruned before descent. Numbered
SML/MED/LRG/XTL stems are conservatively excluded even outside canonical folders;
their titles are not guessed from private recovery history in this milestone.

Reports intentionally expose local relative filenames to the person reviewing them;
progress events contain counts and code-defined phases only. These reports are not
publication artifacts. No live model, image quality, efficacy, new native console,
or browser category-workflow acceptance is claimed.

Checks before the final incomplete-scan repair (preserved as historical):

- `suite-accepted.txt/xml`: 974 passed, 7 platform skips (3 unavailable Windows
  symlink tests and 4 POSIX PTY tests). The earlier sandbox run retained in
  `suite.txt` had 972 passes and a native-browser Page.navigate timeout; the
  isolated browser rerun and the final suite passed with local browser access.
- `focused-final.txt/xml`: 28 focused cases passed, including actual Windows
  command-wrapper argument handling. The first `|` alias syntax was interpreted
  as a command pipe; `launcher.json` preserves that error and `launcher-first`
  preserves the failing regression for the replacement `;` syntax. Semicolons
  now separate explicit aliases in both the form and direct commands.
- `contracts-accepted.txt`: all external contract stages pass, with 363 source
  signatures, 43 importable leaf modules and 13/13 exact negative diagnostics.
  `typing-accepted.json` preserves the verification record from this run.
- `raw-source-accepted.txt`: the separate strict source audit still fails with
  1,073 diagnostics in 37 files (46 checked). The new filename module has none.
  The earlier 1,080-diagnostic run is retained; its new-module annotations and
  reused loop-variable issue were corrected without suppressing diagnostics.
- `build.txt`, `install.txt`, `distribution.txt`, `package.json` and
  `installed-categories.json`: fresh sdist/wheel/application bytes match, an
  isolated installed wheel exposes the filename command and merged aliases,
  and inherited synthetic sort/undo and linear-launcher checks pass. The existing
  uv environment supplies dependencies; no new virtual environment was created.
- `launcher-final.json`: the real PowerShell-to-riposte.cmd path reviews two
  overlapping category groups across the 10,000-entry synthetic folder.

Reproduction commands (repository root; local browser access is required for
the full runtime suite):

```powershell
uv run --no-sync --frozen --cache-dir typing/.cache/uv python -m pytest -q -o cache_dir=.tmp/title-discovery/pytest-cache --basetemp .tmp/title-discovery/suite-accepted
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv build --offline --cache-dir typing/.cache/uv --out-dir .tmp/title-discovery/dist
uv pip install --offline --no-deps --cache-dir typing/.cache/uv --python .venv/Scripts/python.exe --target typing/.cache/title-discovery/installed .tmp/title-discovery/dist/riposte_studio-0.5.0-py3-none-any.whl
uv run --no-sync --frozen --cache-dir typing/.cache/uv python evidence/title-discovery/verify_distribution.py
```

Fresh acceptance reports preserve the existing workflow, packaging, menu,
recovery and commit-check requirement boundaries (OGM-009 through OGM-013).
Their previous reports remain historical. Older stale requirements outside this
milestone are not upgraded by these results. PAC-027B retains saved keyword/
phrase/alias/exclusion rules, priorities, destination previews, private original
title provenance, category routing and exact undo of category assignments.

Final source review reproduced two incomplete-scan failures: the shared
fail-closed link helper also returns true on stat errors. Discovery now inspects
file metadata once, distinguishes unreadable entries from links/reparse points,
and reports INCOMPLETE for unreadable files or directories. It still prunes links
and private state before descent. `unreadable-first.txt/xml` preserves both failed
cases; `readiness-final.txt/xml` passes all 31 discovery tests, including simulated
symlink and junction attributes. Only the new module changed after the earlier
acceptance; the other 51 application files match that snapshot.

The current evidence is `suite-readiness.txt/xml` (977 passed, 7 platform skips),
`contracts-readiness.txt` and `typing-readiness.json` (all external stages pass),
`raw-source-readiness.txt` (1,073 diagnostics in 37 files; none in the new module),
and `build-readiness.txt`, `install-readiness.txt`, `distribution-readiness.txt`,
`package.json` and `installed-categories.json` (fresh package/install checks pass).
`large-folder-readiness.json` measures the current implementation on 10,000 real
synthetic entries: 1.68 seconds and 891,468 peak Python-traced bytes. The original
media content is not decoded. Earlier package reports and source maps are kept
in files with `before-incomplete-scan` in their names.

`acceptance-final.json` and `OGM-009-final.json` through `OGM-013-final.json` are
the current source-bound acceptance reports. The earlier acceptance reports
predate the incomplete-scan fix and must not be treated as current proof.
