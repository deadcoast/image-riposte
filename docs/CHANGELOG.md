# 0.5.0 / current development checkout

PCUC-005 integrates a fixed local FLUX Kontext editing backend with existing
experiment, cohort and reviewer-panel workflows. Explicit preferred-resolution
preparation, model-specific conditioning and named component/tokenizer asset
hashes prevent hidden resizing and incomplete model identity. Same-seed CPU
execution with tiny random real-library components verifies numerical plumbing;
pretrained CUDA/bfloat16 editing and efficacy remain unqualified. See
[Kontext evidence](../evidence/pcuc-kontext/README.md).

PCUC-004 adds committed reviewer calibration panels, task-specific rubric anchors,
separate opaque packet assignments and one retained final response per reviewer
slot. Exact agreement bounds include missing ratings; pairwise contingency tables
and Cohen kappa expose disagreement, prevalence and undefined cases. Calibration
does not change experiment/cohort scores or qualify rubric validity, reviewer
independence or efficacy. See [panel evidence](../evidence/pcuc-review-panels/README.md).

PCUC-003 adds prospective local artwork cohorts: a fixed sampling pool, one model
load, one attempt per selected artwork, retained failures, ordered primary reviews
and equal-artwork missingness bounds. Source aliases and exact-raster duplicates
are rejected; per-member whole-run scans are avoided. Bounds are exact for the
finite selected sample under boundedness, not confidence intervals or efficacy
proof. See [cohort evidence](../evidence/pcuc-cohorts/README.md).

PCUC-002 commits local experiment protocols before generation, retains failed
attempts and adds concealed-label review packets with append-only endpoint ratings.
Exact trial/report/frame identity gates review; missing ratings suppress aggregate
contrasts and filter/clean failures remain counted. Local generation now checks
configuration and weight drift across loading. This qualifies operational tooling
using synthetic outputs, not real-model efficacy or independent preregistration.
See [experiment evidence](../evidence/pcuc-experiments/README.md).

PCUC-001 factors publication gradients through shared views, reducing repeated
codec/resize work while retaining sequential model graphs, quality backtracking
and best-feasible selection. The claim is supported by a chain-rule derivation,
independent gradient checks and paired CPU benchmarks; real-model/GPU speed and
protection efficacy remain unqualified. PAC-034 is shelved for later development.
See [PCUC evidence](../evidence/pcuc-shared-views/README.md).

PAC-033 adds source-owned request, media and inspection records and annotates
shared service, worker and controller boundaries. The strict raw-source audit
falls from 1,100 to 876 diagnostics, with no increased module/error-class count.
Existing validation, preview consent, mutation ordering and recovery checks are
retained. This is a bounded reduction; the source tree is still not type-clean.
See [typing evidence and remaining debt](../evidence/source-typing/README.md).

PAC-032 replaces repeated full-catalog reads with indexed image lookup and
operation-local title maps. Sorting retains file integrity checks and detects
external SQLite commits through an operation-local revision guard; changed
catalogs require another preview. Journal ordering and exact undo remain intact.
Measured returned rows scale with collection size in the tested audit, lookup
and sorting cases. See [measurements and limits](../evidence/catalog-scaling/README.md).

PAC-031 requires exact preview receipts for ordinary and combined sorting.
Ordinary plans now include source identities/hashes and per-file destinations;
combined receipts also bind protection settings and selection. Terminal/browser
confirmation carries the displayed receipt. CLI apply requires `--plan-id`;
combined apply uses the top-level ID. Stale consent is rejected before state,
late files never join execution, collisions retain the reviewed destination,
and partial-sort undo remains available.

PAC-030 centralizes application-folder separation in the shared root check used
by CLI, API and terminal operations, including previews. Source checkouts protect
their project root; installed wheels protect the loaded package directory.
Canonical overlap checks follow existing link rejection and precede workspace
state/lease access. Independent sibling folders remain usable. See the
[root-safeguard evidence](../evidence/application-roots/README.md).

PAC-029 adds OS-owned workspace leases and atomic compatibility markers. Killed
workers from this implementation no longer strand otherwise valid sort undo;
live owners remain exclusive, including during legacy workspace upgrades.
Unknown legacy locks remain blocked. The scoped Windows, POSIX lease, typing and
packaged-install evidence is in [workspace-lease](../evidence/workspace-lease/README.md).
The Markdown item is complete; CSV reconciliation and the overall milestone remain open.

The version remains 0.5.0. Later work in this checkout includes independent
Sort / RIPOSTE / Sort + RIPOSTE workflows, explicit INSTALL and menu-first START,
recorded undo, byte-preserving video sorting, filename discovery, saved category
rules, exact category destinations and private original-title/assignment recovery.
Publication/backend repairs and source-derived external typing contracts also
postdate the original terminal patch. These changes have scoped evidence linked
from [PROJECT-STATUS.md](PROJECT-STATUS.md).

The 2026-09-18 review identified 16 open items. The Markdown audit is the working
checkpoint and CSV TODO is frozen until the completion milestone. This status
correction is not a new release or a claim that the open items are implemented.

# 0.5.0 / historical terminal revision reconstruction

See [REVISION-v05.md](REVISION-v05.md) for source provenance, transparent backgrounds, goks, semantic reports and interaction changes. Backends and image pixels are unchanged.

# 0.4.0 / Native Typer + Rich ASCII

- Replaced argparse with 27 native Typer command names and preserved direct payload/positional compatibility.
- Added a real foreground-owned Rich terminal, ASCII geometry, image previews, task-specific layouts and a same-controller linear alternative.
- Connected all primary clean/protect/publish/review/package actions and retained every expert helper; added exact generation report/frame targets.
- Added date/size catalog targeting, repeatable model and output parameters, explicit JSON/events channels and code-only failures.
- Added bounded key/paste parsing, pause/palettes, resize boundaries, source-replacement confirmation, exact review enforcement and terminal/signal cleanup.
- Changed launchers to native terminal by default, with explicit browser alternative and a local Windows command wrapper.
- No change to backend protection algorithms or any pretrained efficacy status in this interface wave.

# 0.3.0 — Main publishing product and temporal pathway

Independent per-size batch protection; model reuse and execution probing; best-feasible quantized search with restarts; spatial/local-colour quality gates; interrupted-item resume; exact-byte reviewed PNG packs; optional SVD first-step temporal-energy objective; primary publishing UI and optional exact-output workshop handoff. No pretrained or CUDA efficacy claim. See ENGINE-v03.md and WAVE-03-HANDOFF.md.

# Change log

## 0.2.0 — RIPOSTE / Wave 02

Built from the delivered SHROUD 0.1.0 ZIP. Renamed the installed project, package, command, browser interface, API session header, launchers and state identity. Added explicit legacy-state upgrade without rewriting artwork or renumbering assets. Original sanitizer/organizer behavior and inherited regression logic are retained.

Implemented the selected reference's hierarchy in the local workbench: live collection tree, connected stages, zoom/pan/native fit, transport preview, adjacent model controls, scoped challenge results and five-arm generation review. Added responsive and keyboard interaction checks.

Added fixed local encoder/early-inpainting adapters, runtime/file preflight, actual-codec-forward masked optimization, frequency-weighted directions, sequential two-pass branch aggregation, integer budgets, cooperative cancellation and code-only failures. Retained the original encoder baseline.

Added exact-magnitude sign controls, 24-context encoder qualification, explicit optimization-protocol scope and safe model-weight relation labels. External unknown protocols cannot be silently called held out.

Added controlled SD img2img, nine-channel inpainting and SVD reference-generation paths. New reports bind date-only output frames, record predetermined conditioning and pipeline filtering flags, and expose same-seed five-arm review without claiming protection.

Hardened report commits, candidate hash checks, evaluation ordering, read-only legacy catalog handling and rollback of failed report publication. Launchers recognize package version changes. Updated research, implementation contracts, handoff and executable checks.

Pretrained/CUDA/native Windows efficacy qualification remains outstanding. This release does not include pretrained model weights, bundled named-paper defenses or a temporal/text-guided-video defense objective.

## 0.1.0 — SHROUD / retained foundation

Original delivered sanitation, organization, public-raster laboratory, EOT-VAE experiment, external-candidate import, transport tests, paired baseline runner and local interface. The original archive's 194 tests were run before development; inherited test logic is preserved under the new identity. Provenance is recorded in `evidence/`.
