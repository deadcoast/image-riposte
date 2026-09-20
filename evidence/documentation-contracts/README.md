# PAC-039 / current documentation and historical contracts

Authority: "CONTINUE development utilizing the NEXT PAC", following PAC-038's
named PAC-039 handoff. NDL-025 admits this documentation stage; OGM-026 records
its bounded requirement. The exact working checkpoint is
[todo-audit.PACER.md](../../todo-audit.PACER.md).

## Changes and source review

The [documentation map](../../docs/README.md) points to maintained guides and
preserved history. [CURRENT-CONTRACT.md](../../docs/CURRENT-CONTRACT.md) maps older
claims to precise current sections. The threat model and publishing guide now
consistently describe original-byte undo history, title provenance, videos,
generated PNGs, research/duplicate reports and ownership-checked crash recovery.
The CLI inventory includes all shipping commands; examples use real syntax and
the correct Image library action. Historical result counts in project status
are explicitly tied to their original stages.

| Reviewed claim | Source | Executed regression scope |
| --- | --- | --- |
| Date-only generated PNGs, no universal filesystem/pixel privacy guarantee | `sanitize.py` | `test_sanitize.py` |
| Private originals, titles, modification times and conflict-checked undo | `sort_history.py`, `sort_titles.py`, `organizer.py`, `category_sort.py` | `test_sort_recovery.py`, `test_category_sort.py`, `test_category_rules.py` |
| Videos retain original bytes; both float variants are excluded only from sorting | `video.py`, `policy.py`, `organizer.py`, `intake.py` | `test_video_sort.py`, `test_float_sort.py` |
| Exact preview and consent; selected-input snapshots independent of original paths | `sort_plan.py`, `intake.py`, `publication.py` | `test_sort_preview_binding.py`, `test_workflows.py` |
| Accepted PNG-only packs and exact review bindings | `publication.py` | `test_v03_publication.py`, `test_publication_review_snapshots.py` |
| Live lease exclusion, matching abandoned marker, unknown marker rejection | `store.py`, `locking.py` | `test_workspace_lease.py` |
| Read-only duplicate scans and explicitly exported paths/evidence | `duplicates.py`, `duplicate_review.py` | `test_duplicates.py` |
| Shipping argument syntax and menu number | `cli.py`, `terminal/state.py` | Parser-based examples/inventory check and direct source review; no interactive usability claim |

## Retained evidence

- `before.zip` retains the exact pre-edit Markdown documents and packaging/index
  inputs. `before.json`/`before.txt` retain initial findings, including the old
  contradictory paragraphs, missing inventory commands and wrong menu number.
  Two initial `Exit: 0` findings were checker handling of successful help output,
  not application failures; the final checker recognizes explicit help/version
  exits. Missing planned documents were expected before implementation.
- `documentation.json` records **68** parsed fenced command examples, all **43**
  shipping commands, **167** local links/anchors, ten unchanged archived documents and three
  byte-identical historical bodies beneath revised navigation wrappers.
  Parser checks do not execute source replacement, model loading or export.
- `source-before.json` is the prior reviewed 76-file application snapshot.
  Every application hash must remain identical; external stubs are unchanged.
- `focused.xml`/`focused.txt`: **325 passed, one Windows symlink skip**, two
  dependency deprecation warnings retained. `contracts.txt`: all seven external
  declaration stages passed, 536 signatures and 63 importable leaf modules;
  all 13 negative consumers retained their exact expected diagnostics.
- `build.txt` and `verification.json` record fresh wheel/sdist application byte
  parity, current documentation inclusion and development-manifest equality.
  Documentation links refer to repository records; a distribution is not a
  complete archive of every historical evidence file.
- `inventory-final.txt`, `acceptance-review.json`, `OGM-*.json` and `governance.json`
  retain guarded inventory registration, per-requirement documentation-delta
  review, task closure and NDL-025 absorption. Earlier acceptance is preserved.

Run `.venv/Scripts/python.exe evidence/documentation-contracts/verify.py` for the
documentation checks; add `--packages` to check retained tests/contracts and
distribution parity. `--manifest` updates the declared development manifest.
Never repeat `--capture` over the retained baseline.

## Qualification boundary

This stage changes documentation, its source-distribution inclusion and evidence
tooling. It does not change application behavior. Focused tests use synthetic
media and existing Windows dependencies. There is no new human/native UI, model
efficacy, clean-install or cross-platform qualification. PAC-034 remains shelved.
The full 1,519-test application run and three native Chromium tests are PAC-038
evidence, not rerun here. Its strict source audit still records 825 diagnostics
in 36 of 66 files; application bytes are unchanged, and a passing external
declaration check does not make that source audit pass. The release milestone
remains open.
