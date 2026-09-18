# Sort journal commit safety — PAC-024

The development handoff was PAC-023: independent menu workflows, reversible
sorting, read-only previews and separate image/video folders. Its changes were
already present and uncommitted. This continuation changes only
`SortHistory.remove_source` in application code; the other 50 application files
match the preceding reviewed snapshot.

## Reproduced and repaired

Before the repair, source removal checked the original bytes, persisted the
removal-intent journal, then unlinked the source without revalidation. A writer
could edit or replace the original during journal persistence and lose that
new file. The ten retained failing cases cover image and sidecar sources with
same-size edits restoring mtime, byte-identical replacements, timestamp changes,
external removal and added hard links.

The commit now rechecks pathname state and the content hash after journal
persistence. If either changed, it clears the unexecuted removal intent and
reports `SOURCE_CHANGED_OUTPUT_RETAINED`. The original backup and generated
output remain available. Undo can remove that output while preserving the later
source edit. Missing sources can still be recovered from the original backup.

This bounds the demonstrated journal-write interval. It does not make a portable
filesystem check-and-unlink sequence atomic against arbitrary external writers.
Rehashing adds one streaming read before source removal, including for videos.

## Executed evidence

| Check | Result |
| --- | --- |
| `before.txt/xml` | 10 failed reproductions on the retained `sort_history.before.py` |
| `focused.txt/xml` | 94 passed, one Windows symlink skip; new cases plus existing recovery, real video, organizer and prior mutation regressions |
| `suite.txt/xml` | 922 passed, seven platform skips, one separately run native-browser case |
| `browser.txt/xml` | Native-browser startup timed out inside the sandbox; retained |
| `browser-native.txt/xml` | The same headless native-browser case passed outside the sandbox |
| `contracts.txt` | First run exposed a fixed-length tuple inference error in the inventory tool; retained |
| `contracts-final.txt` | All external checks pass: 356 signatures, 42 importable leaf modules and 51 application files |
| `source-mypy.txt` | Still fails: 1057 errors in 37 files, 45 source files checked |
| `package.json`, `distribution.txt` | All 51 application files match fresh sdist, wheel and isolated installation; installed previews, sort/undo, actual Windows linear launcher and wrapper pass |
| `inventory-final.txt` | 273 admitted files, 484 application symbols and 1,953 symbol dependency edges reconcile with no issues |

Total distinct application regressions: **923 passed, 7 skipped**. Skips concern
Windows symlink privileges and POSIX PTY tests. This run did not repeat native
interactive ConPTY visual checks or execute pretrained models. Protection
efficacy remains unestablished. Earlier evidence stays historical.

The inventory tool now annotates its extensible input tuple as `tuple[str, ...]`.
The reviewed external declarations did not need changes: method parameters,
return behavior and existing journal fields remain compatible. The new snapshot
admits only the inspected method change; `source-review.json` binds both hashes.

Commands, from the repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_sort_commit_safety.py -q --basetemp=typing/.cache/sort-commit/before --junitxml=evidence/sort-commit-safety/before.xml
.venv/Scripts/python.exe -m pytest tests/test_sort_commit_safety.py tests/test_sort_recovery.py tests/test_video_sort.py tests/test_organizer.py tests/test_development_repairs.py -q --basetemp=typing/.cache/sort-commit/focused --junitxml=evidence/sort-commit-safety/focused.xml
.venv/Scripts/python.exe -m pytest tests -q -k 'not native_browser' --basetemp=typing/.cache/sort-commit/suite --junitxml=evidence/sort-commit-safety/suite.xml
.venv/Scripts/python.exe -m pytest tests/test_browser_review.py -q -k native_browser --basetemp=typing/.cache/sort-commit/browser-native --junitxml=evidence/sort-commit-safety/browser-native.xml
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv --cache-dir typing/.cache/uv build --offline --no-build-isolation --out-dir typing/.cache/sort-commit/dist
uv --cache-dir typing/.cache/uv pip install --offline --no-deps --python .venv/Scripts/python.exe --target typing/.cache/sort-commit/installed typing/.cache/sort-commit/dist/riposte_studio-0.5.0-py3-none-any.whl
.venv/Scripts/python.exe evidence/sort-commit-safety/verify_distribution.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

The before command was run before the repair; it passes against repaired source.
The first build attempt used uv's global cache and failed with access denied
(`build.txt`); the repository-local cache build passed (`build-local.txt`).
Distribution verification reused the existing reviewed probe with fresh output
and install locations, preserving its prior reports. Temporary installation
smoke files used the repository-local `typing/.cache/sort-commit` directory.

## Remaining development

The broad audit task remains in review and its real-model qualification proposal
remains pending. Existing historical typing/patch/model acceptance gaps have not
been silently closed. The grouped feature roadmap in `docs/WAVE-04.md` still
begins with reusable publishing recipes and collection targeting, followed by
regional quality controls, engine/model-memory work and long-collection polish.
This repair does not claim those features are implemented.
