# TODO, PACE AND NODULE AUDIT

## CORRECTION / working authority, 2026-09-18

USER (original wording):

> review the repo, see todo-audit.PACER.md CORRECTION for your latest fix, THE CURRENT PACER SPEC TODO IS FROZEN UNTILL IT IS CAUGHT UP WITH WHAT IS IN THE MARKDOWN. WHEN THE MARKDOWN TODO AUDIT IS COMPLETED; THE PACER SPEC todo.PACER.csv WILL BE UPDATED CORRECTLY WITH THE REST OF THE SPEC; AS A MILESTONE STEP. EVERYTHING MUST BE UPDATED TO PROJECT STATUS, VER, CONFIGS, INSTALLS, STARTS, REPO MUST BE MILESTONED AND UNITED.

The preceding chat ended with the PAC-028 identification audit reproduced below.
**The audit findings remain open.** PAC-028 completion is not repair completion.
This file holds the working status and checkpoint while TODO is frozen.
INFERRED: keep all four connected CSVs byte-identical during catch-up, so reciprocal
links cannot advance TODO indirectly. Reconcile them together through guarded
PACER commands only at the completion milestone.

### Repository review checkpoint

OBSERVED: source, project metadata, root lockfile and installed editable package
identify **0.5.0**. No new product version or completed release is declared here.
The prior root manifest identified 0.4.0 and was stale; its original bytes are
preserved under `history/v0.4.0/RELEASE-MANIFEST.json`. The root manifest now
describes the explicit current development scope and marks this audit open.
See [project status](docs/PROJECT-STATUS.md) for current contracts and release gates.

- Fresh install/start/menu regression run: **29 passed** on Windows Python 3.14.3.
  Install and launch subprocesses use adapters; this is not clean bootstrap
  or native macOS/Linux qualification.
- All five original audit probes reproduced again. Crash recovery remains blocked,
  CLI application overlap remains accepted, ordinary preview/apply can drift,
  catalog reads remain quadratic, and browser preview cancellation is unsupported.
  A successful probe confirms these defects; it is not application acceptance.
- Current source/stub parameter parity: **387 signatures, 46 leaf modules**, no
  discrepancies; **56 application files** match the reviewed source snapshot.
- The retained raw-source audit still matches current source: **1,103 diagnostics
  in 37 of 49 Python files**. External contracts do not clear these findings.
- Read-only PACER onboarding/validation passed; TODO has 31 DONE and 16 TODO rows.
  Frozen register hashes are in the [review evidence](evidence/milestone-reconciliation-2026-09-18/review.json).
- An offline locked install dry-run resolved successfully and proposed refreshing
  only the editable application package. It did not install anything.
- Real Windows wrapper/version, START linear-menu open/exit and sort/rules help
  checks exited 0. After the documentation edits, structural PACER validation is
  still valid, with OGM-009/010/011/019 evidence now stale. Those records remain
  unchanged under the freeze and require review at milestone reconciliation.

### Working checklist

| Item | Current audit status | Required next evidence |
| --- | --- | --- |
| PAC-029 | OPEN; hard-exit defect reproduced | Safe lease recovery, live-owner exclusion, concurrent claims and exact undo |
| PAC-030 | OPEN; shared guard missing | CLI/API/terminal application-root separation, including installed layouts |
| PAC-031 | OPEN; ordinary preview drift reproduced | Bound normal/combined plans and rejection of changed input/policy |
| PAC-032 | OPEN; quadratic reads reproduced | Indexed lookups/maps with integrity and scaling measurements |
| PAC-033 | OPEN; source typing audit failing | Scoped diagnostic reduction without weakening behavior/checks |
| PAC-015 | OPEN; qualification incomplete | Real local models/native platforms; separate visual and efficacy evidence |
| PAC-034 | OPEN; launcher adapter checks pass | Clean/upgrade installation across the Python/platform matrix |
| PAC-035 | OPEN; preview cancellation unsupported | Cancellable read-only browser jobs, progress and stale-result checks |
| PAC-036 | OPEN; legacy evidence needs review | Fresh proof for each exact requirement, preserving history |
| PAC-037 | OPEN; guided controls unbuilt | Structured rules/assignments, validation, keyboard access and consent |
| PAC-038 | OPEN; guidance differs by interface | Shared safe recovery guidance with sanitized codes |
| PAC-039 | IN PROGRESS; current status/supersession corrected | Complete document/command audit against shipping source |
| PAC-040 | OPEN; recipe library unbuilt | Versioned path-free recipes without saved approval/execution |
| PAC-041 | OPEN; health inspection unbuilt | Read-only storage/capability/history inspection |
| PAC-042 | OPEN; private title search unbuilt | Opt-in private search, bounded paging and export exclusion |
| PAC-043 | OPEN; artist-directed budgets unbuilt | Regional budgets, quality/resume identity, separate efficacy proof |

### Milestone completion gate

1. Finish the Markdown work against each retained acceptance criterion.
   Unavailable qualification remains OPEN; it cannot silently become PASS.
2. Reconcile all four PACER registers, inventory scope, source/symbol references,
   approval provenance, requirement acceptance and nodule state through guarded
   commands. Preserve this request and all earlier failures/history.
3. Align the selected release version across source, project, lockfile, installed
   metadata, documentation and manifest. Build current distributions and verify
   their contents and installed behavior, recording exact hashes.
4. Verify configuration, explicit INSTALL, non-installing START, direct wrapper,
   supported runtime/platform matrix and existing-workspace compatibility.
5. Validate the complete register graph and current evidence before declaring the
   milestone complete. A review checkpoint or passing subset does not close it.

**Checkpoint:** repository review/status correction is recorded; implementation
is incomplete. **Next action:** PAC-029 crash-lock recovery, retaining the fresh
pre-fix reproduction and live-owner/concurrency/recovery acceptance.
No CSV status, release tag, new version, or audit-complete claim is issued here.

## Original PAC-028 handoff / historical identification result

• Completed PAC-028: reviewed eight application areas and recorded 16 prioritized items in todo.PACER.csv. Each has source references and acceptance
  criteria in the detailed review (evidence/development-review-2026-09-18/review.json).

  1. Source weaknesses

- PAC-029 — High: A terminated process leaves an abandoned workspace lock that blocks built-in undo. Recovery needs safe ownership detection.
- PAC-030 — High: The CLI can sort inside the application checkout even though the terminal picker rejects that folder. Enforce the safeguard in shared
    operations.

- PAC-031 — High: Ordinary sorting can include files added after preview. Bind execution to the confirmed plan.
- PAC-032 — Medium: Repeated full-catalog reads produce quadratic work. The probe measured 256 rows read for 16 files and 1,024 for 32.
- PAC-033 — Medium: The existing raw-source typing audit reports 1,103 diagnostics across 37 files; its source hashes still match. These are typing
    findings, not 1,103 demonstrated runtime defects.

  1. Further development required

- PAC-015 — High, existing: Complete real-model and native-platform qualification; preserve the distinction between stub tests and actual protection
    evidence.

- PAC-034 — Medium: Verify clean installation across declared Python versions and operating systems.
- PAC-035 — Medium: Add cancellation and progress to browser discovery and read-only previews. API preview cancellation currently returns unsupported.
- PAC-036 — Medium: Review and refresh five stale legacy acceptance records without discarding historical evidence.

  1. Additions and polish

- PAC-037 — Medium: Guided category-rule editing and per-file assignment controls, with inline validation.
- PAC-038 — Medium: Consistent, actionable error and recovery guidance across browser and terminal.
- PAC-039 — Low: Clarify current documentation and link superseded contracts to their replacements.

  1. Beneficial new modules or features

- PAC-040 — Medium: Saved, reusable publishing recipes that exclude machine-specific paths and operation approvals.
- PAC-041 — Medium: Workspace health inspection covering available space, filesystem capabilities, and recovery-history storage.
- PAC-042 — Medium: Private original-title and category search with filtering and pagination.
- PAC-043 — Low: Artist-defined regional protection budgets, with validation and quality checks before efficacy claims.

  Five synthetic probes reproduced the key observations. PACER validation and the audit’s source-bound acceptance passed. Application source remained
  unchanged; implementation proposals remain pending. I also marked interrupted-sort recovery requirements incomplete while preserving their earlier,
  narrower passing evidence.

  The next implementation priority is PAC-029, followed by PAC-030 and PAC-031.

  Worked for 25m 25s · done 2:42 PM

─ Conversation recap ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

  PAC-028 is complete: the PACER source-code review covered eight application areas and compiled 16 prioritized findings in todo.PACER.csv.
