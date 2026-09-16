# Main product contract: protect and publish

The normal path imports no workshop module. `publication.py` owns the publishing lifecycle; `open_in_workshop` is the only optional bridge into `lab.py`. That bridge copies the exact committed pixels and is idempotent for the same output. There is no engine rerun, extra resizing or secret change of candidate.

## State and data boundaries

The actively maintained calendar hierarchy holds canonical clean masters. Publishing operations use `.riposte/publishing/BATCH_ID/`; old `.shroud` workspaces use their existing namespace until explicit upgrade. Model directories must be outside the managed artwork folder.

`request.json` stores a fixed recipe, technical model identities, execution-probe results, internal image IDs, date-only values and already-clean master hashes. No raw metadata, pre-clean image hashes, raw source filenames, source locations, user identity or local model pathname is stored. The metadata/date sanitation implementation from the clean foundation is unchanged.

Each task has one clean publishing baseline, one candidate and a report. These PNGs have already passed strict date-only encoding/audit before their first disk write. The report commits last. Temporary files contain only sanitized data or code-defined JSON. A failed task removes its own uncommitted item directory. An abrupt process interruption can leave sanitized orphans; resume removes only an uncommitted task's directory, never a committed result.

The plan is read-only and creates no publishing tree. Models load and pass an actual numerical input-gradient probe before a new publishing request is committed. A failed loader cannot generate a noise substitute or an apparently successful batch. If an individual illustration cannot satisfy the requested numerical objectives/quality, it is blocked while other tasks may finish.

## Exact output and review identity

A ready output is `READY_FOR_REVIEW`; it is never automatically approved. Numeric quality and human visual approval are separate. A review receipt binds both the final candidate's PNG hash and the full committed report hash. The receipt contains only decision and acknowledgement fields, not free-text personal data.

Before serving/approving/packing, the application checks the request/task/image/date relationship, strict PNG audit, candidate/baseline hashes, canonical output path, expected dimensions, source-clean hash, and an independently regenerated clean publishing baseline from the canonical master. It recomputes numerical quality rather than trusting the old PASS string. Modifying a report requires a new review; modifying committed image bytes stops the operation.

The hash relationships catch accidental stale/changed outputs; they are not signatures against a hostile person who controls the entire machine and can rewrite every receipt and report. No such stronger security boundary is advertised.

API review accepts several item IDs in one request and validates the full selection before writing approvals. CLI `--item` is repeatable. The UI presents individual image review. `REJECTED` reverses an earlier acceptance for future downloads. An already distributed pack cannot be revoked remotely.

## Publishing packs

The main download API assembles only accepted PNG files, in your year/month/actual-output-size hierarchy. It rechecks accepted hashes and acknowledgements while holding the workspace operation lock. No reports, model names, clean baselines, raw assets, alternate metadata-bearing formats or empty directories enter the pack. ZIP entries have no comments/extra fields, have date-only midnight timestamps, and carry PNG bytes unchanged.

The in-memory pack limit is 512 MiB of accepted PNG data; a larger batch must be approved/exported in smaller selections. The CLI writes the same pack under `.riposte/exports/BATCH_ID/RIPOSTE.zip`. Assembly and writing hold a single lock, preventing an intervening review revocation from being overlooked inside that operation. Subsequent reviews affect subsequent snapshots only.

## Resume and cancellation

One serialized job runs per application instance; the workspace lock also rejects conflicting writers. Cancellation is cooperative at model/iteration/item boundaries, not mid-kernel preemption. The current output is not committed after a cancellation check fires. Already committed outputs remain available, including when the UI job itself is marked cancelled.

Resume repeats input/committed-artifact validation, reconstructs the original recipe, reloads caller-selected local models and compares their safe identities with the recorded selection. Matching paths are not required; matching model identities are. Recomputed tasks use the original index-derived seed. Completed files are not regenerated or renamed. Model hashes identify selected weight bytes, not all possible library/kernel/configuration effects; this is not a reproducibility or transfer certificate.

A stale process lock following a system crash requires stopping all RIPOSTE processes and confirming that no operation remains active before manual removal. No unsafe automatic unlock was added. A committed-but-corrupted result is not quietly replaced. Failed model loads or unavailable GPU memory remain explicit failures rather than triggers to drop the requested defense objective.

## Useful views, not a new application inside the application

The primary page owns collection selection, rendition choices, pixel budget, optional model objectives, the batch queue, exact-pixel review, actual JPEG/resize/crop/blur previews, and the final PNG download. Native-pixel inspection and numerical quality do not require entry into the workshop.

The supporting workshop owns advanced encoder controls and five-arm full-generation comparison. Its old standalone export remains an explicitly unverified expert path for compatibility, not the main reviewed publishing-pack workflow. No old helper command was silently removed. No workshop score becomes an automatic success badge on publishing outputs.
