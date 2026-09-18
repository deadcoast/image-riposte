# Sort collision polish - PAC-026

User request: "again! polish", continuing the core sorting work.

## Reproduced and repaired

The image writer previously checked for an occupied destination and then used
`os.replace`. A file arriving between that check and the rename was overwritten,
including its timestamp. The repaired default commit publishes the prepared
temporary file with an exclusive hard link. A collision reports
`DESTINATION_EXISTS`; there is no fallback to replacement. The date-only
timestamp is set on the temporary file before publication. Callers explicitly
requesting `replace=True` retain their existing replacement behavior.

Both image and video sorts prepared recovery entries before attempting their
outputs. When a collision rejected the output, undo still claimed that external
path. Different bytes blocked undo; identical bytes caused undo to delete the
external file. Sorting now persists the rejected entry with no output claim,
while retaining its original backup. Later valid inputs can still sort and undo.
Video hard-link collisions now report the same specific destination conflict.

Only `store.py`, `organizer.py` and `sort_history.py` changed among the 51
application files in the preceding snapshot. The source review binds their old
and new hashes and verifies that the other 48 files are unchanged. The new
`SortHistory.reject_output` declaration uses the existing nullable journal fields;
the journal format and existing public writer signatures are unchanged.

## Executed evidence

| Check | Result |
| --- | --- |
| `before-first.txt/xml` | 12 failures, one explicit-replacement control pass on retained pre-fix source |
| `before.txt/xml` | 12 failures, one pass after replacing internal journal assertions with end-to-end recovery checks; confirms deletion of identical-byte external image/video files |
| `focused.txt/xml` | 115 passed, one Windows symlink skip; all 13 new collision/commit checks plus prior sort and recovery regressions |
| `suite.txt/xml` | 943 passed, seven platform skips, one separately run native-browser case |
| `browser-native.txt/xml` | One native headless browser fixture passed outside the sandbox |
| `contracts.txt` | All external checks passed: 357 signatures, 42 importable leaf modules, 51 application files |
| `source-mypy.txt` | Separate source-body audit still fails: 1,057 errors in 37 files, 45 source files checked |
| `package.json`, `distribution.txt` | All 51 source files match fresh sdist, wheel and isolated installation; installed previews, sort/undo, actual Windows linear launcher and wrapper pass |
| `inventory-before.txt` | Expected missing/stale declarations and new inputs before guarded reconciliation |
| `inventory-final.txt` | 277 admitted files, 485 application symbols, 1,955 symbol dependency edges; no issues |

Total distinct application regressions: **944 passed, 7 skipped**. Skips concern
Windows symlink privileges and POSIX PTY contracts. Real ffmpeg fixtures exercise
video sorting without transcoding. No new interactive ConPTY visual acceptance,
pretrained-model execution or protection efficacy is claimed. The broader audit
and existing historical/model acceptance gaps remain separate unfinished work.

The exclusive filesystem commit requires hard-link support and fails safely if
unavailable. Sorting already uses hard links for backups and videos. This change
also affects other default clean-image writes through the shared helper. It does
not claim protection against arbitrary parent-directory replacement or power
loss before a rejected-output journal update is persisted. Historical journals
and earlier failed evidence remain unchanged.

Commands executed from the repository root, with logs redirected here:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_sort_collisions.py -q --basetemp=typing/.cache/sort-collisions/before --junitxml=evidence/sort-collisions/before.xml
.venv/Scripts/python.exe -m pytest tests/test_sort_collisions.py -q --basetemp=typing/.cache/sort-collisions/before-behavior --junitxml=evidence/sort-collisions/before.xml
.venv/Scripts/python.exe -m pytest tests/test_sort_collisions.py tests/test_sort_partial_failures.py tests/test_sort_commit_safety.py tests/test_sort_recovery.py tests/test_video_sort.py tests/test_organizer.py tests/test_development_repairs.py -q --basetemp=typing/.cache/sort-collisions/focused --junitxml=evidence/sort-collisions/focused.xml
.venv/Scripts/python.exe -m pytest tests -q -k 'not native_browser' --basetemp=typing/.cache/sort-collisions/suite --junitxml=evidence/sort-collisions/suite.xml
.venv/Scripts/python.exe -m pytest tests/test_browser_review.py -q -k native_browser -p no:cacheprovider --basetemp=typing/.cache/sort-collisions/browser-native --junitxml=evidence/sort-collisions/browser-native.xml
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv --cache-dir typing/.cache/uv build --offline --no-build-isolation --out-dir typing/.cache/sort-collisions/dist
uv --cache-dir typing/.cache/uv pip install --offline --no-deps --python .venv/Scripts/python.exe --target typing/.cache/sort-collisions/installed typing/.cache/sort-collisions/dist/riposte_studio-0.5.0-py3-none-any.whl
.venv/Scripts/python.exe evidence/sort-collisions/verify_distribution.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py --plan typing/.cache/sort-collisions/inventory-plan.json
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

Both before runs used pre-fix source. The first logs were copied to
`before-first.txt/xml` before the behavioral rerun. Distribution verification
reuses the reviewed probe with fresh install/output paths and repository-local
TEMP/TMP; historical distribution evidence is preserved.
