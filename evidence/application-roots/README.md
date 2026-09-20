# PAC-030 / shared application-root safeguards

The user resumed the named PAC-030 checkpoint on 2026-09-18. This is bounded
implementation acceptance in `todo-audit.PACER.md`. All four PACER CSV registers
remain unchanged, and the overall audit and release milestone remain open.

## Implemented boundary

`store.check_root` now rejects a workspace that equals, contains or is contained
by the loaded application directory. CLI/shared service, terminal selection,
API startup and backend state/path operations use that check. It runs after
existing link/reparse-point rejection and before lease/state inspection or
creation. Previews use the same root policy as execution. Errors expose fixed
codes, with terminal recovery text and no private path echo.

The application directory comes from the loaded store module, independent of
the working directory and Python prefix. For `src/riposte` with a parent
`pyproject.toml` identifying `riposte-studio`, it is the project root. Otherwise
it is the loaded `riposte` package directory. This explicitly covers editable
checkouts, Windows/POSIX site-packages layouts and isolated wheel targets without
assuming a fixed number of parents. Malformed source project configuration fails
closed. Layout discovery is cached by loaded module path for repeated checks.

The wheel boundary is the RIPOSTE package, not a promise to protect every sibling
dependency, distribution metadata directory or Python executable. Independent
sibling image/results folders are accepted. Standalone protection's separate
read-only inputs retain their existing policy. No root bypass option was added.
This is an application operation guard, not protection against hostile local code
or concurrent external filesystem replacement; existing file/journal checks remain.

Previously nested libraries are rejected in place. With no active operation,
moving the complete library to an independent sibling on the same filesystem,
including private history and the lease file, preserves exact undo in the tested
completed-sort case. Do not separate the private state from the library. This
does not qualify copying interrupted work across filesystems or recovering
unidentified legacy lock markers. No user image library was moved by this task.

## Retained evidence

| Record | Observed result and scope |
| --- | --- |
| `before.txt`, `before.xml` | 26 failed, 3 passed; includes one incorrect harness assumption that an async API job response was its completed result |
| `before-corrected.txt`, `.xml` | Corrected pre-fix regression: 25 failed, 4 passed |
| `first.txt`, `.xml` | 3 failed, 102 passed; implementation rejected roots, but CLI assertions read stdout instead of the existing stderr error envelope |
| `focused.txt`, `.xml` | 4 failed, 107 passed, 1 skipped; corrected stream but wrong JSON key; mixed junction/dot-dot case expected a linked-path code for a nonexistent Windows path |
| `roots.txt`, `.xml` | 35 passed, 1 symlink-privilege skip after harness corrections; exact error assertions, source bytes/timestamps and no-state checks remain |
| `full.txt`, `.xml` | Sandbox: 1,119 passed, 9 skipped, 2 native-browser Page.navigate timeouts |
| `full-native.txt.gz`, `full-native.xml.gz` | First outside-sandbox attempt: 425 passed, 4 skipped, 701 fixture setup errors accessing the sandbox-owned default pytest temporary parent; losslessly compressed after byte-for-byte decompression verification |
| `full-native-final.txt`, `.xml` | Fresh external temporary base: 1,121 passed, 9 skipped, two dependency warnings and one pytest cache warning; final application source, native browsers included |
| `compatibility.txt`, `.xml` | 36 passed, 1 symlink-privilege skip; includes the nested-library move/undo test added after full-suite collection, with application source unchanged |
| `contracts.txt`, `contracts-first.json` | First external run: declaration/tooling/stubtest stages pass; five runtime fixture errors because the old fixture location was inside the checkout |
| `contracts-final.txt`, `typing/evidence/verification.json` | All seven external stages pass; 395 signatures, 47 importable leaf modules, 57 application files |
| `raw-source.txt` | 1,102 diagnostics in 37 files, 50 checked; source-body typing remains failing |
| `build-final.txt`, `install-final.txt`, `package.json` | Fresh offline distributions and no-dependency isolated target installation; all 57 application files match source/sdist/wheel/target; source and wheel root rejection plus sibling sort/exact undo pass |
| `entries.json`, `wrapper-version.txt`, `start-linear.txt` | Actual existing Windows wrapper version 0.5.0 and PowerShell START linear-menu open/q-exit, exit 0 with no stderr |
| `pacer-validation.json` | Structurally valid; stale evidence remains unrefreshed under the freeze |
| `deferred-inventory.json`, `deferred-operations.json` | Unapplied source/symbol inventory proposal; expected FAIL until coordinated registration is allowed |

The nine full-suite skips are five Windows symlink-privilege cases and four POSIX
terminal cases. A native Windows junction was tested successfully. Simulated
POSIX package path shapes are not a native Linux/macOS application qualification.
The previous PAC-029 WSL lease result remains historical and was not repeated.
No model, GPU, efficacy, clean bootstrap or new runtime qualification is claimed.

The first START check piped text into the PowerShell script's parameter binder,
which reported an input-binding error; its menu exited on EOF. Its stdout is
retained as `start-linear-first.txt`. The corrected check invoked a real child
PowerShell process with `q\n` on stdin and required empty stderr and exit 0.
`before-typing/` preserves PAC-029's previous current contract/source records.
`package-first.json` and initial build/install logs preserve the package check
before the last documentation edits; final artifacts were rebuilt afterwards.
The evidence verifier initially compared the complete admitted inventory with
only application-source paths. It now checks inclusion of all 57 application
files and fresh hashes for every admitted inventory input, including evidence.

## Reproduction and next action

Use the existing environments. Test workspaces must be outside the application
checkout; do not bypass the guard to reuse repository-local image fixtures.

```powershell
uv run --no-sync --locked --cache-dir .tmp/uv-cache pytest -q tests/test_application_roots.py
uv run --no-sync --locked --cache-dir .tmp/uv-cache pytest -q
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv build --offline --no-build-isolation --cache-dir .tmp/uv-cache --out-dir .tmp/application-roots/dist
uv pip install --python .venv/Scripts/python.exe --reinstall --no-deps --target .tmp/application-roots/installed --offline --cache-dir .tmp/uv-cache .tmp/application-roots/dist/riposte_studio-0.5.0-py3-none-any.whl
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/application-roots/verify_package.py
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/application-roots/verify.py
```

The source audit intentionally returns nonzero. `verify.py` checks recorded
evidence identity, current source/manifest and frozen registers; it does not
rerun runtime tests. The earlier milestone/workspace-lease verifiers bind their
historical source snapshots and are not current acceptance for PAC-030.

Deferred references include OVR-035/520 (store/check_root), OVR-875/888/892
(terminal paths), OVR-045/638 (recovery messages), the two new store helpers,
their external declarations, fixture relocation, regression tests and evidence.
OGM-001/011 and affected sorting/recovery rules need fresh guarded reconciliation
at the milestone; no frozen acceptance or approval was rewritten.

Next: PAC-031 ordinary and combined preview binding. Preserve the existing
reproduced drift and exact category-plan behavior when extending ordinary plans.
