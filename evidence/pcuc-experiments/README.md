# PCUC-002 / committed generation experiments

2026-09-18. INFERRED implementation of the user's research -> theorizing ->
formulating -> critical self critique -> planning -> development requirement.
PAC-034 remains SHELVED. CSV registration remains deferred. This is operational
research tooling, not a model qualification or protection result.

## Research and source observation

The [IPV-Bench v3 primary paper](https://arxiv.org/abs/2603.26154v3) motivates
evaluating actual image-to-video outcomes across domains, prompts and preprocessing,
including matched-noise comparisons. Its findings are not RIPOSTE measurements.
It supports stronger evaluation; it does not validate this application's controls,
generators or rubrics. [OSF registration guidance](https://help.osf.io/article/330-welcome-to-registrations)
supports specifying questions, design and analysis before outcomes are known.
RIPOSTE writes a local receipt before generation; it does not contact OSF, publish
artwork or establish an independent timestamp. The [NIST paired binary comparison reference](https://itl.nist.gov/div898/software/dataplot/refman1/auxillar/mcnemar.htm)
motivates retaining pairing. No McNemar test is implemented: repeated seeds/views
from one artwork do not establish independent-artwork sampling or population inference.

OBSERVED source: `generation.py` ran clean, candidate and three sign-scrambled
matched-magnitude controls, recording fidelity, adjacent-frame RMSE and filter
flags after generation. It had no prior protocol, human task-outcome record or
concealed-label packet. Divergence alone has no task-success interpretation.
`LocalGenerator` bound weights before load but omitted configuration identity
and post-load drift checks. Historical PACER PAC-009/generation source context
supports preserving incomplete outcomes; current source defines implementation.

## Theory, formulation and critique

For group g (publication view and generation seed), arm a has three human Boolean
endpoints: task success T, source preservation P and usability U. Joint success
J[g,a] = T[g,a] * P[g,a] * U[g,a]. F[g] indicates any reported filter flag in any
arm. Eligibility E[g] = (1-F[g]) * J[g,clean], provided every endpoint in the entire
planned experiment was rated. A null endpoint makes the review INCOMPLETE and
suppresses its aggregate contrast, including when other groups are fully rated.

For a complete review with K=sum(E)>0:

    numerator   = sum_g E[g] * (J[g,c1] + J[g,c2] + J[g,c3] - 3*J[g,candidate])
    denominator = 3*K
    contrast    = numerator / denominator

This is the average paired control-minus-candidate joint-success difference.
Each summand lies in [-3,3], proving contrast lies in [-1,1]. Exact integer
numerator/denominator accompany the float; negative and zero values are retained.
K=0 is INCONCLUSIVE. Filtered and clean-failed groups remain counted. Unreported
filter status is counted separately; it is not proof that filtering was absent.

The estimand is conditional on clean success and reported filter exclusions, not
an unconditional attack-failure rate. Predetermined exclusions can still limit
generalization or introduce selection effects. Controls share an artwork, seed
and pipeline; they are not independent experiments. Review revisions are retained,
not pooled as independent raters. The fixed qualitative rubric is operational,
not psychometrically validated. Disagreement, ceiling/floor effects and bias remain.

The packet sorts independent opaque IDs chosen before generation, excludes role,
model and group labels, and includes a clean reference plus every full sequence.
This is presentation blinding: the operator owns the role map and pixels may
reveal conditions. The software cannot prove a reviewer inspected every frame
or answered truthfully. Decisions bind to stored outputs, not a viewing-session
attestation. Unknown optimization views remain unknown; different weights are
not promoted to a held-out model-family claim. Prior selection may already have
influenced the operator. This is not independent preregistration.

Local hashes detect drift against retained receipts. An operator able to rewrite
all receipts can rewrite history. Hard termination can leave an OPEN attempt;
loading failures precede model-bound protocol creation. CUDA nondeterminism
remains. Pre/post weight and configuration hashes detect persistent load-time
changes, not adversarial change-and-restore races or frozen model snapshots.
Rehashing weights costs a second complete weight read.

## Implemented phases and use cases

1. `experiment.py` seals exact trial/artifact identity, model weights/configuration,
   engine hashes, runtime versions, conditions, seeds, views, control seeds,
   endpoints, exclusions and analysis before the first generator call. Completed,
   failed and cancelled attempts retain receipts; interrupted attempts stay OPEN.
   Legacy reports are not retroactively relabelled.
2. `generation.py` uses the committed run ID and binds its finished report to the
   protocol. Partial frames are removed on Python failures/interrupts, preserving
   the protocol. Loading checks weight/configuration identity before and after.
3. CLI/shared service exposes discovery, status, explicit packet export and
   append-only reviews. Inspection verifies trial/report/frame/date/review identity.
   ZIP creation streams frames, fixes ZIP metadata, preserves date-only PNGs and
   publishes exclusively. Export failures remove only the private temporary file.
   Source filenames, local paths and model labels are absent from the packet.
4. Ratings require every planned sample, exact endpoint keys and Boolean/null
   decisions. Unknown fields, duplicate keys, wrong protocol, oversized inputs
   and missing samples fail before review writes. Shared root guards remain.

Collection parsing casts follow runtime dictionary/key/list checks. CLI decorator
and dispatch annotations describe existing behavior, avoiding multiplication of
old typing errors. No application Any, ignore, dependency change or suppression
was introduced. The new module retains one frame's bytes at a time during packet
writing; indexes and ZIP directory metadata scale with frame count. It is not a
constant-total-memory or throughput benchmark claim.

## Executed evidence

`source-before.zip` retains PCUC-001 source bytes. `before.xml` records 18 failing
integration cases and two passing arithmetic cases with the new review core
present but the original generation path unconnected. It is a before-integration
failure, not a test of the wholly unchanged archived tree. Initial integration:
138 passed; expanded checks: 46 passed. Final source-bound suite counts live in
`full-command.json`, `full-native.xml`, `full-native.txt` and `acceptance.json`.

Regressions cover protocol timing with synthetic outputs, all three task adapters,
packet privacy/date metadata, exclusive export, retained failures, legacy/open
runs, trial/report/frame/review drift, invalid ratings, all 32 binary arm patterns,
every filtered arm, incomplete-group suppression, CLI/service operation and root
guards. Synthetic model doubles exercise production control flow, not pretrained
generation or human judgments about protection. Loader fixtures likewise execute
real adapter code with stub components and persistent load-time mutations.

Pre-review contract rejection and raw-source failures are retained. The first raw
audit reported 885 errors; the next reported 778 after helper annotations and two
new-module corrections. Final source identity and the still-failing raw audit are
recorded in `acceptance.json`. Package checks use existing Windows dependencies.
No clean install, GPU execution, native Linux/macOS acceptance, real-model task
outcomes or population efficacy inference is established.

The final contract rerun refreshed an execution log after the deferred inventory
was captured. The identity verifier rejected that stale inventory;
`inventory-after-contracts-drift.json` retains the exact changed evidence hashes.
The deferred read-only plan was regenerated against final evidence. No application
or CSV change caused that rejection. Final `verification.txt` records readback.

## Next question

Use independently selected artworks and predefined held-out model families/tasks
to test whether proxy gains predict these outcomes. Cohort sampling, validated
task rubrics, independent raters, family coverage and actual CUDA generation remain
separate research/qualification work. This infrastructure establishes none of
those experimental results.
