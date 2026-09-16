# Wave 03 handoff — RIPOSTE 0.3.0

## Product direction

The user's purpose is image-integrated artwork security at acceptable visual quality. The workshop is a helper, not the application. Do not turn the next wave into another test-dashboard/UI expansion. Do not replace model-driven defense with cosmetic noise when models or dependencies are unavailable.

## Delivered in this grouped wave

The main application now has independently optimized multi-size batch outputs, one-time model loading with real execution probes, best-feasible quantized checkpoint selection, regional colour/pixel fidelity gates, exact-file review and date-only PNG packs. Cooperative cancellation/resume, stale-output checks and metadata contracts are carried through. An optional original SVD temporal-gradient pathway is integrated into the same exported raster budget. Workshop testing is a secondary exact-output handoff.

The real temporal objective is deliberately narrow: first-step predicted-latent temporal-energy reduction, not decoded-video/task success and not text conditioning. The v0.2 editing and benchmark paths are preserved. All previous unit tests remain byte-identical.

## Prior plan status, without completion inflation

| Prior work package | Status after this release |
|---|---|
| Q01 native CUDA/pretrained qualification | Still pending. Runtime execution probes implemented/tested with synthetic oracles; optional dependency installation failed here. |
| Q02 real artist-approved illustration outcomes | Still pending. Only explicitly synthetic images were processed. No artist quality judgments fabricated. |
| Q03 attack the publishing path | Generic real codec previews and exact export binding implemented; actual social-platform upload/download and adaptive removal remain pending. |
| Q04 video-targeted optimization | Partial, substantive implementation: a genuine first-step SVD temporal computation graph now drives the shared raster. No full-video/text-guided or independent-family efficacy established. |
| Q05 integrate product findings/batch queues | Main production workflow and persistent review implemented. No recipe promoted as empirically recommended because real efficacy evidence is absent. |

## Next grouped development, in order

**1 / Reproducible local model qualification.** On an actually available native runtime, install compatible CUDA/PyTorch and fixed model dependencies, retain safe technical version/weight/config information, and execute encoder, inpainting and temporal probes at real publishing sizes. Test full reference generation. Record memory/time and useful failure codes. Run native Windows and Apple paths, not merely launcher parsing. Keep artwork off external services.

**2 / Compare final published-use outputs.** Use a diverse, explicitly approved set of the artist's sanitized illustrations. Fix budgets, seeds and meaningful editing/animation tasks. Compare clean, candidate and matched controls; include held-out images and independently selected model families. Human review should score whether the intended reuse succeeded, whether the source composition/style was preserved and whether useful motion/instruction-following remained. Pixel/latent difference is not this outcome.

**3 / Develop a genuine modern video defense where evidence points.** Evaluate whether the current early temporal signal correlates with decoded-video behavior. Replace or extend it if it does not. Add differentiable multi-step/text-conditioning work for an appropriate reproducible modern model family rather than advertising SVD as text-guided. Include real social-platform derivatives, screenshots and adaptive cleanup. Keep the same shared visual budget and exact final-export path.

**4 / Promote useful recipes, not names.** Only a recipe with acceptable artist-reviewed quality and meaningful above-control task disruption earns a qualified recommendation, scoped to its tested conditions. Keep failed cases. Batch usability, source cleanliness and the direct publishing path remain primary; workshop instrumentation supports these experiments and must not replace them.

These are grouped development/qualification deliverables, not a request for approval after every small repair. Native hardware/model availability is a real dependency, not a reason to invent efficacy figures or declare a method universally impossible.

## Source map and regression invariants

`quality.py` -> `release_guard.py` -> `publication.py` -> `server.py` / `cli.py` / `static/publish.*` is the primary dependency chain. `runtime_probe.py` and `temporal.py` supply model execution and the optional temporal branch. Existing `models`, `views`, `coupled`, `sanitize`, `organizer`, `policy` and `store` remain shared infrastructure.

Keep old tests unchanged. Add tests beside them. New numerical tests must use real autograd where relevant and explicitly label synthetic oracles. No synthetic oracles may become user-facing production fallbacks. Verify source, independently installed wheel and a fresh final archive. Browser screenshots must identify their synthetic artwork; loopback HTTP and browser-bridge tests must not be mislabeled as native CUDA/pretrained qualification.
