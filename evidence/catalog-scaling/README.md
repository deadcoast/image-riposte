# PAC-032 — quadratic catalog reads

The Markdown audit accepts this bounded repair. Version remains 0.5.0; the
overall audit and release milestone remain open. All four PACER CSVs are frozen.
PACER context and OVR source/symbol references were used to trace implemented
lookup, audit, sorting, title provenance and recovery behavior before editing.

## Implementation and integrity boundary

`find_image` now queries the existing image primary-key index and validates the
selected path and PNG bytes. Missing catalogs are not created by lookup.
Whole-workspace audit still validates the complete collection; it loads private
titles once. Sorting takes a bounded number of initial snapshots and maintains
operation-local media/title maps. `SortHistory` also indexes its initial titles
and updated IDs while preserving the journal format and persistence order.

`CatalogGuard` holds one SQLite connection for the operation. Its database-path
identity and revision are checked after snapshots, around owned writes, before
source removal and before reporting success. Writers can borrow that connection;
existing callers still own and close their connections. `BEGIN IMMEDIATE` protects
the start of a write, and an expected affected-row count rejects additional
trigger effects. External database changes, including schema-only changes, stop
apply with its existing preview-change code; audit reports `CATALOG_CHANGED`.
File/hash/path, rules, source identity, collision and recovery checks remain active.

The design follows SQLite's same-connection comparison contract for
[`PRAGMA data_version`](https://www.sqlite.org/pragma.html#pragma_data_version)
and connection-local accounting in
[`total_changes`](https://www.sqlite.org/c3ref/total_changes.html). Revisions are
not persisted approvals. A SQL update that does not change the database may not
advance its revision; the first package fixture incorrectly expected that, and
was corrected to change a value and restore it through another connection.
The guard is not a cryptographic monitor of arbitrary in-place database byte
tampering. As before, a change after the last check can race file removal;
operations do not lock out every uncoordinated filesystem writer.

Changes detected before workspace acquisition create no initial state. Later
changes may leave an incomplete, journal-backed operation with its source and
verified output retained. Undo remains subject to catalog/output conflict checks.
Videos remain byte-preserved and sort-only; title/recovery data stays private.

## Measured scaling

`measure-before.json` and `measure-after.json` retain all observations and their
application source hashes. Fixtures are real SQLite catalogs with 32x24 PNGs and
private category titles. Apply uses a current category receipt. The new-input
case adds as many raw images as already exist. Initial preview creation is outside
the timed section; apply's internal revalidation is included.

Returned rows, before → after:

| Operation | 16 cataloged images | 32 | 64 |
| --- | ---: | ---: | ---: |
| Audit | 272 → 32 | 1,056 → 64 | 4,160 → 128 |
| Lookup every ID | 256 → 16 | 1,024 → 32 | 4,096 → 64 |
| Apply unchanged collection | 640 → 128 | 2,304 → 256 | 8,704 → 512 |
| Apply with equally many new images | 2,688 → 128 | 10,496 → 256 | 41,472 → 512 |

Other measurements at 64 cataloged images, before → after:

| Operation | Logical returned bytes | Seconds | Python peak bytes |
| --- | ---: | ---: | ---: |
| Audit | 1,637,824 → 37,750 | 0.3933 → 0.0698 | 226,188 → 290,182 |
| Lookup every ID | 790,528 → 12,352 | 0.4153 → 0.2974 | 202,692 → 163,488 |
| Apply unchanged | 2,567,000 → 151,000 | 1.5546 → 1.2507 | 1,702,786 → 1,706,931 |
| Apply with 64 new images | 12,296,620 → 151,000 | 10.4016 → 7.4707 | 2,787,747 → 2,848,226 |

The meter counts rows returned by media/title SELECTs and their JSON-serialized
bytes. It does not measure disk reads or SQLite page-cache traffic. Time and
`tracemalloc` include instrumentation; the first 16-image audit includes a cold
instrumentation import peak. These are single synthetic samples on this Windows
runtime, not user latency or total process RSS. Maps trade some memory for fewer
reads. Durable journal persistence and image work remain separate costs; no
whole-sort linear-time guarantee is made. Browser state still returns a complete
catalog per poll; pagination and private-title search are separate work.

## Executed evidence

| Evidence | Result and scope |
| --- | --- |
| `before.xml`, `before.txt` | 8 failed, 10 passed before repair: six row-budget failures and two missed schema-only changes |
| `first.xml`, `first.txt` | 82 passed, 2 failed; existing interruption adapters needed to forward the optional borrowed connection; original failure points retained |
| `focused.xml`, `focused.txt` | 179 passed, 1 skip; actual SQLite read budgets/index plan, external changes before and after owned commits, trigger effects, lookup tamper/missing/path checks, interrupted connection cleanup, sorting/collision/recovery/video regressions |
| `full-native.xml`, `full-native.txt` | 1,180 passed, 9 platform skips on final application source; native Windows runtime including Chromium checks |
| `contracts-before-review.txt` | Correctly rejected changed source identity and the unrevised video-writer stub parameter |
| `contracts-final.txt` | Seven external stages pass: 402 signatures, 49 leaf modules, 59 application hashes |
| `raw-source.txt` | 1,100 diagnostics in 37 files, 52 checked; remains failing; new guard has no diagnostics |
| `measure-before.json`, `measure-after.json` | Rows, logical bytes, elapsed seconds and Python allocation peaks at 16/32/64 images |
| `package-first.txt` | Retained no-op SQL fixture assertion failure; corrected to perform an actual change |
| `build.txt`, `install.txt`, `package.json` | Fresh source/sdist/wheel/isolated-target equality across 59 application files; real lookup, revision, audit, CLI/API/service, preview/apply and exact undo checks |
| `entries.json`, `start-transcript.txt` | Actual Windows wrapper/version and START linear menu/q-exit |
| `pacer-validation.json` | Structurally valid; stale evidence and new source registrations deferred |

The nine full-suite skips are five unavailable Windows symlink privileges and
four POSIX terminal cases. Junctions are tested. Two dependency warnings and a
pytest cache warning did not affect assertions. Prior source/contract evidence
is retained in `before-typing/`. The application source is unchanged between
the focused/full suites, after measurement, contracts, raw audit and packages.
No new dependencies, model weights, schema migration or release version were added.
No clean bootstrap, native Linux/macOS application or real-model efficacy
qualification is established by these checks.

Run `uv run --no-sync --locked --cache-dir .tmp/uv-cache python
evidence/catalog-scaling/verify.py` for retained evidence/source identity.
`--inventory` emits deferred register/symbol operations and intentionally reports
missing/stale registration under the freeze; it never edits CSVs. The verifier
does not rerun tests or complete the overall milestone. Next: PAC-033 source typing.
