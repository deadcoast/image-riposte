# PAC-029 / crash-abandoned workspace lease

2026-09-18. **Bounded repair accepted in the Markdown audit.** Version remains
0.5.0. All four PACER CSVs remain byte-identical; the whole audit and release
milestone remain open. The active user instruction was "CONTINUE THE NEXT STAGE
IN PLANNED DEVELOPMENT" against the PAC-029 checkpoint. Source findings below
are OBSERVED; the implementation choice is INFERRED engineering scope.

A killed sort/undo worker previously stranded `operation.lock`, preventing a
valid explicit undo. `before.txt` retains seven failures and one pass from the
new process-death regression before repair.

## Implementation and compatibility

`locking.py` holds a nonblocking native exclusive lease on the persistent empty
root file `.riposte-operation.lease`. Windows uses `LockFileEx`; POSIX uses
`flock`. Ownership is tied to an open handle/descriptor, with no PID or elapsed
time inference. The root location survives `.shroud` to `.riposte` upgrades.
`workspace_lock` acquires the lease before state mutation, atomically publishes a
fully written marker, and releases only its own marker. A marker binds the root
identity, lease identity and random ownership token. Matching abandoned markers
can be reclaimed only while holding the same OS lease.

Live current owners cannot be displaced. Legacy O_EXCL writers still contend on
`operation.lock`; an unknown, empty or malformed old marker stays blocked because
it cannot prove its owner is dead. This repairs crashes from the new implementation,
not every unidentified historical lock. Do not delete the persistent lease file.
Hardlinked, nonempty, linked or invalid lease paths fail closed. Filesystems without
the required locking/hardlink behavior are not qualified. This is process-death
recovery, not a power-loss or hostile concurrent-filesystem-mutation guarantee.
Old versions may show the new root file as unsupported input. Current previews
exclude that exact validated file and do not create it.

Explicit operation consent and preview-bound undo remain required. Recovery still
checks journals, original backups, destination identity and conflicts. The tests
exercise exact original bytes, names, mtime and catalog cleanup after interruption,
including interruption during undo. Private journals, PNG metadata rules and
experimental model/visual qualification boundaries are unchanged.

Native API references: [Microsoft LockFileEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex),
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
[Python msvcrt](https://docs.python.org/3/library/msvcrt.html),
and [Linux flock](https://man7.org/linux/man-pages/man2/flock.2.html).

## Retained results

| Record | Result and scope |
| --- | --- |
| `before.txt` | 7 failed, 1 passed: reproduced pre-fix process-death failures |
| `first.txt` | 2 failed, 35 passed: initial in-state-directory lease blocked Windows legacy rename |
| `second.txt` | 37 passed after moving the persistent lease to the workspace root |
| `extended.txt` | 24 passed: death during prepare/removal/undo/publication, live owner, six-process contention, PID/age independence, replaced lease/marker, legacy winner and invalid paths |
| `full.txt`, `full.xml` | 3 failed, 1,083 passed, 8 skipped: two browser navigation timeouts inside sandbox and exact root inventory needing the new lease entry |
| `browser-native.txt` | 79 passed, 1 skipped outside sandbox; browser failures did not reproduce there |
| `full-native.txt`, `full-native.xml` | 1,086 passed, 8 skipped, 2 dependency deprecation warnings on Windows Python 3.14.3 outside sandbox |
| `final.txt`, `final.xml` | 53 lock/recovery/migration checks passed on final source after the platform-dispatch typing adjustment |
| `posix.json` | Native low-level lease passed on existing Ubuntu WSL Python 3.12.3; not full Linux/macOS application qualification |
| `contracts-final.txt`, `typing/evidence/verification.json` | All external stages passed; 393 signatures, 47 leaf modules, 52 declaration/consumer files, 57 application files |
| `raw-source-first.txt.gz` | Initial 1,109 errors in 38 files: new platform-dispatch typing errors retained |
| `raw-source.txt` | Final 1,102 errors in 37 files, 50 checked; no diagnostics in new locking module; source-wide typing remains failing |
| `build.txt`, `install.txt`, `package.json` | Offline build, no-dependency isolated target install; 57-file source/sdist/wheel/target equality and installed CLI hard-exit/undo/legacy upgrade passed |
| `pacer-validation.json` | Structurally valid; ten stale evidence records, deliberately not refreshed under freeze |
| `deferred-inventory.json`, `deferred-operations.json` | Unapplied source/symbol reconciliation proposal; inventory FAIL is expected until the freeze is lifted |

The full-suite run preceded replacing `os.name` dispatch with `sys.platform` and
explicit Windows guards. The final 53-test run, POSIX probe, full contracts,
source-body audit and fresh package checks cover that final revision. This is not
a claim that the entire suite ran again after that adjustment. The eight skips
are four Windows symlink-privilege cases and four POSIX terminal cases.

`before-typing/` preserves the preceding 1,103-diagnostic audit and contract
records. `package-before-platform-typing.json` and the corresponding build/install
logs retain the initial package result. `posix-first.txt` retains the failed probe
that tried moving the directory containing the open lease on the mounted Windows
filesystem; the production root lease does not move during state upgrades. A
package-verifier invocation initially hit the denied global uv cache; rerunning
with `.tmp/uv-cache` succeeded. No third-party dependencies or new runtimes were installed.

## Reproduction and checkpoint

Use existing environments from the repository root:

```powershell
uv run --no-sync --locked --cache-dir .tmp/uv-cache pytest -q tests/test_workspace_lease.py tests/test_sort_recovery.py tests/test_v02_migration.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv build --offline --no-build-isolation --cache-dir .tmp/uv-cache --out-dir .tmp/workspace-lease/dist
uv pip install --python .venv/Scripts/python.exe --reinstall --no-deps --target .tmp/workspace-lease/installed --offline --cache-dir .tmp/uv-cache .tmp/workspace-lease/dist/riposte_studio-0.5.0-py3-none-any.whl
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/workspace-lease/verify_package.py
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/workspace-lease/verify.py
```

The source audit intentionally exits nonzero while those diagnostics remain.
`verify.py` checks recorded evidence identity, frozen registers and current source;
it does not rerun runtime tests. The historical milestone-review verifier's
default mode binds the pre-repair source and is no longer current acceptance.
Its manifest generator still describes the current explicit development scope.

The source review admits only `locking.py`, `store.py`, and `organizer.py`, plus
their external declarations and validation inputs. Existing OVR-035/OVR-529/OVR-530
cover store, upgrade and workspace_lock; OVR-021 covers organizer. The new module
and helper symbols need registration. OGM-012/OGM-018 remain incomplete in frozen
CSV state. No old acceptance or approval was rewritten.

Next: PAC-030 shared application-root separation, then PAC-031 ordinary preview
binding. Regenerate and review the deferred operations with fresh guarded context
at the unified milestone; their provisional IDs are not an approval or reservation.
