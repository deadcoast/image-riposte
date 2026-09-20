# PCUC-003 / committed artwork cohorts and missingness bounds

2026-09-18. USER: "continue decelopment! you have the floor" continues PCUC
development. INFERRED scope: prospective sampling/execution, correct analysis
units, primary review selection and bounded missingness in a working local cohort
workflow. PAC-034 is SHELVED. The four PACER CSVs remain frozen.

## Research -> theory

[ARRIVE's experimental-unit guidance](https://arriveguidelines.org/arrive-guidelines/study-design/1b/explanation)
explains why subsamples/repeated observations must not inflate sample size.
INFERRED application here: seed/view/three-control outcomes belong within an
artwork score. The animal-study guidance does not validate an artwork sampling
frame; it supplies the statistical unit distinction. We report selected artworks,
not a proven count of statistically independent subjects.

[Scharfstein, Manski and Anthony (2004)](https://academic.oup.com/biometrics/article/60/1/154/7289357)
motivate worst-case missing-outcome bounds that do not assume a missingness
mechanism. Their prospective ordinal-outcome analysis is not transplanted as a
population inference algorithm. We derive the simpler exact finite-sample bounds
below. [OSF registration guidance](https://help.osf.io/article/330-welcome-to-registrations)
supports fixing sampling and analysis before seeing outcomes; these local receipts
are not independently registered or timestamped. Python's
[random.sample documentation](https://docs.python.org/3/library/random.html#random.sample)
specifies sampling without replacement. A local RNG, seeded from system entropy,
draws from sorted trial IDs without changing process-global random state. The seed,
runtime and selected IDs are retained; cross-version RNG replay is not promised.

OBSERVED source: PCUC-002 commits single-artwork experiments and captures task
ratings but has no cohort sampling frame, between-artwork aggregation or stable
primary-review order. Naively pooling successful runs or eligible groups would
change the denominator when work fails or an artwork has more usable groups.
The historical PAC-009/PAC-010 PACER context requires incomplete/stale results to
remain visible. Actual source and PCUC-002 identity readback were examined before
development; frozen register freshness does not establish current implementation.

## Formulation -> critical self critique

For selected artwork i and planned seed/view group g, let J be the conjunction of
the three Boolean endpoints. Let E=1 only if the clean arm succeeds and no arm
reports a filter flag. Define the availability-weighted descriptive score:

    d[i] = sum_g E[i,g] * (J[i,g,c1]+J[i,g,c2]+J[i,g,c3]-3*J[i,g,candidate]) / (3*G[i])

G is ALL planned groups, including clean-failed and filtered groups, which
contribute zero. This is deliberately different from PCUC-002's conditional
contrast, whose denominator is eligible groups only. Both remain visible.
Exclusions cannot improve the score by silently shrinking its denominator.
A zero contribution means no credited difference under this rule; it does not
prove the true task effect is zero. Reported and unreported filtering counts stay
visible, and a filtered black frame cannot create positive protection credit.

Each d lies in [-1,1]. A selected cohort has fixed size N and equal artwork weight
1/N. If U artworks have no complete primary review, with observed sum S:

    lower = (S-U)/N; upper = (S+U)/N; width = 2*U/N

Proof: replace each unknown bounded score with -1 for the minimum and +1 for the
maximum. Every coefficient is positive, so these extrema are attained under the
boundedness-only model. No independence or missing-at-random assumption is used.
Exact Fraction arithmetic retains integer numerators/denominators. Resolving one
unknown reduces width by exactly 2/N. When U=0, the interval collapses to the
finite selected-sample mean. Otherwise a point mean is suppressed. For example,
one observed +1 among three selected artworks gives [-1/3,1], not a cohort +1.

These are completion/sensitivity bounds, not confidence intervals, causal effects
or population generalization. They can be wide: broad intervals are information
about unavailable outcomes, not a reason to drop failures. Scores are about fixed
rubrics and a reference generator; changing that scientific target invalidates
comparisons. Artifact hashes cannot validate rubrics, reviewer honesty or model
family independence. The first complete review by append sequence is primary;
incomplete drafts stay retained and later revisions cannot replace that primary.
This prevents automatic best-review selection, not operator manipulation of all
local history. Legacy unsequenced reviews remain usable individually but cannot
be treated as ordered cohort primary evidence.

Pool checks reject repeated trial IDs, repeated catalog source images (including
different render sizes), and identical RGB rasters regardless of date/metadata.
Known completed generation for the same catalog source also rejects intake;
malformed existing committed generation records fail closed. These checks do not
detect near duplicates, shared authors, external outcomes or every alias of a
source imported under a new ID. Distinct rasters do not establish independence.
Selecting a biased pool or repeatedly creating cohorts remains possible and must
be disclosed; all committed cohorts are discoverable. No held-out model-family
claim is inferred from different hashes.

## Planning -> development

`cohort-challenge` audits the workspace, verifies the explicit pool, loads one
local baseline, draws the requested sample, allocates one run ID per selected
artwork and commits the complete cohort before generation. Its receipt fixes
trial hashes, source/raster identity, model/configuration, runtime/engine identity,
conditions, sampling, endpoints, denominators and primary-review policy. Every
child protocol references that parent hash and allocated run ID. Completed children
remain usable if a later member fails; failed/cancelled/unattempted members are
retained in the cohort denominator. Hard termination leaves OPEN history.

There is no automatic retry or replacement within a committed cohort. Starting a
new command creates separate history. A failure before commitment produces no
cohort; a loading failure provides no exact loaded-model identity. Validation
supports cooperative cancellation between pool members; model loading retains the
existing adapter's non-interruptible sections. Standard `experiment-packet` and
`experiment-review` provide the review path. `cohort` verifies all completed
member artifacts and review receipts, rejecting drift rather than dropping it.

Prior generation metadata is scanned once during intake. First-attempt sequence
numbers are supplied to the typed shared generation executor under the same
workspace lock, avoiding a growing whole-run scan for every member. Ordinary
single-artwork generation retains its existing sequence discovery. The indexed
cohort path reads O(P) trial records and O(R) prior generation records, with
O(P log P) canonical ordering and frame I/O proportional to output bytes, apart
from existing whole-workspace auditing; model load happens once. This is a work
count claim, not a GPU timing result. The regression forbids per-member full-run
discovery; no fake generator enters application source.

## Executed evidence and limits

`source-before.zip` retains all 62 PCUC-002 application files. An actual archived
source run of the original 15 new cohort tests failed all 15 (`before.xml`),
including missing command/module support. Initial integrated checks passed 66
tests. Later cases cover source aliases, validation cancellation, fixed planned
denominators, filtered groups, legacy review order, corruption and partial runs.
Final source-bound full-suite evidence is in `full-command.json` and `full-native.xml`.

The first full run had 1,249 passes, nine platform skips and one fixture failure:
the new resolution-alias case requested a 16-pixel render below the existing
64-pixel minimum. Its failure is retained in `full-first-native.txt/xml`. The
fixture now compares valid 128/64-pixel trials without relaxing that source guard.

`prove.py` independently enumerates 216 sample states and 343 extreme completions,
checks exact sharp endpoints and interval width, and binds the result to source
hashes in `proof.json`. Runtime tests execute the real cohort/generation/review
code with explicitly synthetic image-returning model doubles. They prove control
flow, formulas and integrity checks; they do not measure pretrained efficacy.

External declaration rejection before review and the first raw-source audit are
retained. Typed executor/collection boundaries introduce no Any or ignore.
The initial source audit had 773 errors, including one redundant cast in the new
module, subsequently removed. The final audit remains failing; exact final counts
and package/contract scope are in `acceptance.json`. Distribution checks use the
existing Windows dependency environment. Clean install, native Linux/macOS,
actual CUDA generation, qualified rubrics, held-out families and human efficacy
measurements remain unavailable/unqualified. CSV reconciliation stays deferred.

Next research question: qualify task-specific rubric reliability and independently
chosen model families/artworks before interpreting real cohort scores. The fixed
reference tasks are an operational baseline, not modern-generator coverage.
