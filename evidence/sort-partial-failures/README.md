# Core sorting partial-failure recovery - PAC-025

User request: "CONTINUE working on the core sorting logic".

Only `src/riposte/organizer.py` and `src/riposte/sort_history.py` changed among
the 51 application files in the preceding reviewed snapshot. Other ongoing
development remains intact. The external allocation-helper declaration and
typing proof inputs were updated for these inspected changes.

## Reproduced and repaired

- A failed image or video output left a recovery record whose destination could
  be reused by the next input. Undo then associated two originals with one output.
  Sequence numbers are now reserved for the duration of the sort, even when the
  output fails. The eight-case regression set checks original-byte recovery.
- Editing, replacing or removing a source immediately after its backup completed
  left an unregistered backup occupying the next input's slot. Completed backups
  now receive a journal entry before source validation. Later inputs can proceed;
  undo retains intervening source edits and restores missing original files.
- Number allocation previously rescanned the entire destination for each input
  and raised ValueError on a filename such as `SML².png`. Only canonical ASCII
  sequence suffixes contribute to the initial maximum. Each destination folder
  is scanned once per sort, with occupied candidate names checked individually.
  A late external file is preserved and the next free name used.

These checks cover the reproduced per-file failure intervals. They do not make
filesystem check-and-write or check-and-unlink sequences atomic against arbitrary
external writers. The new backup ordering does not claim power-loss recovery
before the completed backup's journal entry is persisted.

## Executed evidence

| Check | Result |
| --- | --- |
| `before.txt/xml` | Seven failures on the retained `organizer.before.py` and `sort_history.before.py` |
| `focused.txt/xml` | 102 passed, one Windows symlink skip; new failures, late collision, previous commit/recovery, real ffmpeg video and organizer regressions |
| `suite.txt/xml` | 930 passed, seven platform skips, one separately run native-browser case |
| `browser-native.txt/xml` | One native headless browser case passed outside the sandbox; a pytest cache warning did not affect execution |
| `contracts.txt` | All external checks passed: 356 signatures, 42 importable leaf modules and 51 application files |
| `source-mypy.txt` | Separate source-body audit still fails: 1,057 errors in 37 files, 45 source files checked |
| `package.json`, `distribution.txt` | All 51 application files equal fresh sdist, wheel and isolated install; installed preview/sort/undo, actual Windows linear launcher and command wrapper passed |
| `inventory-before.txt` | Expected failure for the two newly admitted proof inputs before registration |
| `inventory-final.txt` | 275 admitted files, 484 application symbols and 1,953 symbol dependency edges reconcile with no issues |

Total distinct application regressions: **931 passed, 7 skipped**. The skips are
Windows symlink privileges and POSIX PTY contracts. No new interactive ConPTY
visual acceptance, pretrained-model execution or protection efficacy is claimed.
Date-only image outputs, unchanged video bytes and explicit operation consent
remain covered by the existing regression suite. Earlier evidence is historical.

Commands executed from the repository root (logs redirect to this directory):

```powershell
.venv/Scripts/python.exe -m pytest tests/test_sort_partial_failures.py -q --basetemp=typing/.cache/sort-partial/before --junitxml=evidence/sort-partial-failures/before.xml
.venv/Scripts/python.exe -m pytest tests/test_sort_partial_failures.py tests/test_sort_commit_safety.py tests/test_sort_recovery.py tests/test_video_sort.py tests/test_organizer.py tests/test_development_repairs.py -q --basetemp=typing/.cache/sort-partial/focused --junitxml=evidence/sort-partial-failures/focused.xml
.venv/Scripts/python.exe -m pytest tests -q -k 'not native_browser' --basetemp=typing/.cache/sort-partial/suite --junitxml=evidence/sort-partial-failures/suite.xml
.venv/Scripts/python.exe -m pytest tests/test_browser_review.py -q -k native_browser --basetemp=typing/.cache/sort-partial/browser-native --junitxml=evidence/sort-partial-failures/browser-native.xml
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv --cache-dir typing/.cache/uv build --offline --no-build-isolation --out-dir typing/.cache/sort-partial/dist
uv --cache-dir typing/.cache/uv pip install --offline --no-deps --python .venv/Scripts/python.exe --target typing/.cache/sort-partial/installed typing/.cache/sort-partial/dist/riposte_studio-0.5.0-py3-none-any.whl
.venv/Scripts/python.exe evidence/sort-partial-failures/verify_distribution.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py --plan typing/.cache/sort-partial/inventory-plan.json
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

The first command ran against pre-fix source with seven cases. The eighth case
was added after the repair to check late destination collision preservation.
The distribution probe uses repository-local TEMP/TMP and the existing reviewed
probe with fresh output/install paths. It does not rewrite historical reports.
The broad audit and real-model proposal remain separate, unfinished work.
