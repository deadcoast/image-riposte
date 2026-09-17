# Selective 0.5 terminal integration

PAC-004 compares `packages/RIPOSTE_v0.4.0.zip`, the pre-merge checkout, and the
supplied `RIPOSTE_v0.5.0.zip`. The supplied file is a complete release snapshot.
Only reviewed missing changes were integrated; it was not extracted over the repository.

## Decisions

- Integrated the terminal palette, semantic reports, contextual help, Enter/i
  selection controls and advanced publishing settings, plus their CLI, launcher,
  capture-script and 49-test revision dependencies. Existing affected source
  files matched the archived 0.4 base after newline normalization.
- Merged README changes while retaining its current formatting. Updated the
  existing detailed terminal specification instead of accepting the archive's
  much shorter replacement. Kept the historical validation record and explicitly
  separated it from current evidence.
- Advanced the package version to 0.5.0. Preserved the user-added mypy dependency,
  all other dependency constraints, and every third-party lockfile version.
- Retained all pre-existing backend/browser files and tests byte-for-byte. The
  existing Git index was left untouched, including previously staged typing work.
- Added source-derived declarations for the three new modules and updated
  changed signatures/re-exports. The original `typing/evidence/source-before.json`
  remains intact; `source-reviewed-v050.json` records the newly reviewed source.
- Kept archive wheels, manifests, screenshots and historical test reports inside
  the original ZIP. They are not installed over, or credited as proof of, this checkout.

The per-entry decisions and pre-merge hashes are in
[`evidence/patch-v050/`](../evidence/patch-v050/). The archive was moved to
[`packages/RIPOSTE_v0.5.0.zip`](../packages/RIPOSTE_v0.5.0.zip) unchanged:

```text
SHA256 97541fba8ce1fd9095080140eef596b0ec80d4c46f590a2adb1f78826fe8547b
```

The request also mentioned 0.5.9. No such ZIP exists in this checkout; both the
supplied filename and internal version identify 0.5.0, so its original name is retained.

## Current verification

Application checks used the existing Windows Python 3.14.3 environment, with
locked test dependencies installed through uv. No optional model stack was installed.

| Check | Result |
| --- | --- |
| Supplied revision tests | All 49 passed in both the terminal and full runs |
| Terminal core, CLI and revision tests | 248 passed; one inherited organizer/checkpoint failure |
| Full pre-merge suite | 405 passed, 10 failed, 12 setup errors, 30 skipped |
| Full merged suite | 455 passed, 9 failed, 14 setup errors, 28 skipped |
| External type contracts | Passed: 43 files, 313 signatures, 38 leaf modules |
| Contract fixtures and tooling | Nine runtime fixtures, six tooling tests, all 13 expected negative diagnostics passed |
| Root `mypy` and `mypy .` | Identical output: 962 diagnostics in 36 of 41 files; no duplicate discovery |

The full suite is **not green**. The existing Windows `fstat`/`Path.stat` identity
mismatch causes intermittent organization failures and downstream fixture errors;
which tests hit that failure varies between runs. Other inherited failures concern
a mocked timestamp, default text decoding, Windows path separators and symlink
privileges. Optional Torch and POSIX terminal cases are skipped. These backend and
test files were not modified by this interface merge. The matching failure causes
and preserved source support continuity; the counts alone do not prove it.

The previous 817 mypy diagnostics described the 38-module source baseline. The
revision adds three modules and untyped implementation paths, producing 962 under
the same strict audit. External declarations pass independently and do not hide
those implementation diagnostics. This merge does not claim to resolve them.

Commands and raw output are retained with before/after JUnit XML under
`evidence/patch-v050/`. `python scripts/verify_v05_merge.py` rechecks
archive bytes, protected source, inherited test coverage, dependencies, the
unchanged Git index and retained reports against this merge's fixed snapshots.
It is expected to become stale after subsequent development. The type suite runs with:

```powershell
uv run --project typing --frozen --offline --cache-dir typing/.cache/uv python typing/check.py
```

The tests exercise controllers, render cells, output contracts and synthetic
records. They do not establish native console visual acceptance, model efficacy,
GPU behavior or correctness of the archive's historical wheel. The POSIX capture
scripts remain platform-specific developer tools and were not executed on Windows.
