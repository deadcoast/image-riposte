# RIPOSTE — Wave 02 handoff and next grouped work

## Delivered as 0.2.0

| Work package | Outcome |
|---|---|
| Rename and safe legacy-state upgrade | Implemented; reads do not mutate legacy state, explicit upgrade preserves asset/trial IDs and artwork |
| Reference-led working UI | Implemented; connected stages, real collection tree, zoom/pan, transform previews, scoped evidence and five-arm review |
| Coupled raster optimization | Implemented experimentally; real JPEG-forward/masked contexts, optional early-inpainting probe, common integer budget |
| Controlled qualification | Implemented; three exact-magnitude sign controls, 24 cells per encoder, known/unknown protocol and weight relations |
| Generation review | Implemented fixed reference adapters for img2img, nine-channel inpainting and SVD; five arms and same-seed review |
| Runtime/preflight/cancellation | Implemented; file presence is not execution, cooperative model cancellation, no generic-noise fallback |
| Inherited/new regression and package QA | Executed; see `VALIDATION.md` and release evidence |
| Real pretrained-model/CUDA protection qualification | NOT EXECUTED; optional dependency/model access failed in the CPU-only runtime |

## Wave 03 — real-model qualification and meaningful video defense

This is one grouped milestone, not approval after each repair. Preserve the current organization, metadata and evidence contracts.

**Q01 / qualify the native runtime.** Execute the launchers on Windows and select a compatible CUDA build. Freeze exact dependency/model configurations and run encoder, inpainting-probe and full-generation smoke cases. Measure actual memory and runtime. No source images, model paths or location metadata in reports.

**Q02 / evaluate real illustration outputs.** Use a diverse artist-approved set with clean masters retained only in canonical sanitized form. Compare original encoder baseline, coupled encoder, coupled early-inpainting and matched controls under fixed budgets. Freeze prompts/masks/seeds and separate development and held-out image/model partitions. Record quality judgments and failed cases, not just displacement.

**Q03 / attack the publishing path.** Test actual published/downloaded files, screenshot resampling and adaptive cleanup. Add control arms only where they answer a testable question. Three sign controls are a mechanics baseline; broaden independent repeated trials before uncertainty claims.

**Q04 / implement actual video-targeted optimization.** Select a currently reproducible temporal/text-conditioning method after code/license/runtime review. Keep the exported raster budget shared with editing objectives. Evaluate against generated videos from an independently held-out family and against useful-motion/source-preservation/task-success criteria. SVD alone cannot establish text-guided video protection.

**Q05 / integrate findings into the product.** Persist review annotations and useful model recipes; enable batch queues only with resource/cancellation/privacy semantics carried through. A recipe becomes recommended only after quality acceptance and actual misuse-task improvement over controls. Keep unsuccessful/unverified states visible.

## Acceptance gates

Cleanliness and artwork fidelity are hard gates. Proxy advantage alone cannot pass efficacy. Different weight hashes cannot pass architecture transfer. A filtered output cannot pass disruption. A demo/test double cannot pass pretrained qualification. Named-paper results cannot be attributed to RIPOSTE's original code.

No watermarks, audience gates, uploads, raw-source backups, source metadata histories or universal-success promises are added in these waves.
