# TODO, PACE AND NODULE AUDIT

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
