# Main product contract: protect and publish

This maintained guide covers publishing artifacts. The [current data contract](CURRENT-CONTRACT.md#public-outputs-versus-private-state) separately describes private original-byte sort recovery, original-title records, unchanged videos and explicit research/duplicate exports. Statements about sanitized publishing inputs or temporary files below do not apply to those other artifacts.

The normal path imports no workshop module. `publication.py` owns the publishing lifecycle; `open_in_workshop` is the only optional bridge into `lab.py`. That bridge copies the exact committed pixels and is idempotent for the same output. There is no engine rerun, extra resizing or secret change of candidate.


## Reusable publishing recipes

Recipes save the publishing edges, channel-change cap, iterations, restarts,
seed, smooth-white choice, colour cap and local RMS fraction. The private,
versioned library is `.riposte/publishing-recipes.json` inside the results
workspace (`.shroud` for an existing legacy workspace). It holds up to 64 names.
Names contain 1–64 characters, start with a letter or number, and use letters,
numbers, spaces, hyphens or underscores. Names match without case sensitivity.

In a terminal publishing form, press **l** to choose a recipe and **Enter** to
load its settings; **i** inspects the full saved settings. Press **s** in the form
to name and preview the current settings, then **s** on that preview to save.
In the browser's publishing settings, open **Publishing recipes**, choose a
name and click **Load settings**. **Preview settings** shows every saved field;
**Save reviewed recipe** explicitly creates or replaces the named recipe.
Changing settings invalidates that save preview. A conflict retains your draft;
reload the library, compare the saved version, then preview again.

Loading fills editable settings. Saving changes only the private recipe library
and workspace bookkeeping; neither action starts processing. Image selection,
source/result paths, device, local model paths and identities, visual approvals
and export acknowledgements are never saved in recipes. Choose them for each
run. Publishing still validates the current settings and commits its complete
resolved configuration and actual model identity per batch. Resume uses that
batch's committed configuration. Combined sorting still requires its exact
preview and replacement consent. A changed pinned recipe requires reloading.


## State and data boundaries

The actively maintained calendar hierarchy holds canonical clean masters. Publishing operations use `.riposte/publishing/BATCH_ID/`; old `.shroud` workspaces use their existing namespace until explicit upgrade. Model directories must be outside the managed artwork folder.

The terminal and direct CLI expose three independent workflows: Sort, RIPOSTE, and Sort + RIPOSTE. Sorting keeps its explicit source-replacement consent. Standalone publishing accepts selected catalog IDs or raw files/directories without requiring a whole-workspace organization checkpoint. Only selected sources must validate. The combined workflow preflights models, sorts with consent, and starts publishing only after a complete sort.

Raw-input batches store reconstructed date-only PNGs at `inputs/IMAGE_ID.png` inside their batch. The original files and directories are unchanged and do not enter the catalog. Resume, review and packaging verify these clean snapshots instead of requiring the originals to stay available. New requests record `source_mode`; requests without that field retain the historical catalog-source interpretation. Failed or cancelled intake before request commit removes its own incomplete snapshots; a hard process termination may leave sanitized, unlisted orphans. Once a request is committed, existing interruption and resume rules apply.

`request.json` stores a fixed recipe, technical model identities, execution-probe results, internal image IDs, date-only values and already-clean master hashes. No raw metadata, pre-clean image hashes, raw source filenames, source locations, user identity or local model pathname is stored. The metadata/date sanitation implementation from the clean foundation is unchanged.

Each task has one clean publishing baseline, one candidate and a report. These PNGs have already passed strict date-only encoding/audit before their first disk write. The report commits last. Temporary files contain only sanitized data or code-defined JSON. A failed task removes its own uncommitted item directory. An abrupt process interruption can leave sanitized orphans; resume removes only an uncommitted task's directory, never a committed result.

The plan is read-only and creates no publishing tree. Models load and pass an actual numerical input-gradient probe before a new publishing request is committed. A failed loader cannot generate a noise substitute or an apparently successful batch. If an individual illustration cannot satisfy the requested numerical objectives/quality, it is blocked while other tasks may finish.

## Exact output and review identity

A ready output is `READY_FOR_REVIEW`; it is never automatically approved. Numeric quality and human visual approval are separate. A review receipt binds both the final candidate's PNG hash and the full committed report hash. The receipt contains only decision and acknowledgement fields, not free-text personal data.

Before serving/approving/packing, the application checks the request/task/image/date relationship, strict PNG audit, candidate/baseline hashes, canonical output path, expected dimensions, source-clean hash, and an independently regenerated clean publishing baseline from the selected canonical master or clean input snapshot. It recomputes numerical quality rather than trusting the old PASS string. Modifying a report requires a new review; modifying committed image bytes stops the operation.

The hash relationships catch accidental stale/changed outputs; they are not signatures against a hostile person who controls the entire machine and can rewrite every receipt and report. No such stronger security boundary is advertised.

API review accepts several item IDs in one request and validates the full selection before writing approvals. Each item's decoded images and PNG buffers are released after validation; only item IDs and receipt hashes are retained across the selection. Reports are read once with an 8 MiB byte limit, and the receipt hashes that exact parsed snapshot. A later report replacement needs a new review; it cannot supply a hash for an earlier report. An operation that has already read an approved snapshot can finish using that snapshot, while later operations observe the replacement.

CLI `--item` is repeatable. The UI presents individual image review. `REJECTED` reverses an earlier acceptance for future downloads. An already distributed pack cannot be revoked remotely.

## Publishing packs

The main download API assembles only accepted PNG files, in your year/month/actual-output-size hierarchy. It rechecks accepted hashes and acknowledgements while holding the workspace operation lock. No reports, model names, clean baselines, raw assets, alternate metadata-bearing formats or empty directories enter the pack. ZIP entries have no comments/extra fields, have date-only midnight timestamps, and carry PNG bytes unchanged.

The in-memory pack limit is 512 MiB of accepted PNG data; a larger batch must be approved/exported in smaller selections. The CLI writes the same pack under `.riposte/exports/BATCH_ID/RIPOSTE.zip`. Assembly and writing hold a single lock, preventing an intervening review revocation from being overlooked inside that operation. Subsequent reviews affect subsequent snapshots only.

## Resume and cancellation

One serialized job runs per application instance; the workspace lock also rejects conflicting writers. Cancellation is cooperative at model/iteration/item boundaries, not mid-kernel preemption. The current output is not committed after a cancellation check fires. Already committed outputs remain available, including when the UI job itself is marked cancelled.

Resume repeats input/committed-artifact validation, reconstructs the original recipe, reloads caller-selected local models and compares their safe identities with the recorded selection. Matching paths are not required; matching model identities are. Recomputed tasks use the original index-derived seed. Completed files are not regenerated or renamed.

Model identities bind the selected weight bytes and the names and bytes of JSON configuration and tokenizer text files in the selected component directories. The adapters compare configuration fingerprints before and after loading, rejecting a detected change. Moving an unchanged bundle preserves its identity. Changed model configuration, tokenizer vocabulary/merges, scheduler settings, or temporal image normalization requires a new batch. Library and kernel versions are outside this file identity.

Older unfinished batches without configuration fingerprints cannot establish the new identity match and must be restarted as a new batch. Their already committed candidates remain available for review and export.

After a crash, a matching abandoned operation marker can be reclaimed only after RIPOSTE acquires the exclusive OS lease on `.riposte-operation.lease`. Its persistent presence does not mean an operation is active. A live lease or unknown marker remains blocked; do not delete lock markers or the lease file. Follow the operation's recovery guidance and preserve workspace history. See [recovery and locks](CURRENT-CONTRACT.md#recovery-and-locks). A committed-but-corrupted result is not quietly replaced. Failed model loads or unavailable GPU memory remain explicit failures rather than triggers to drop the requested defense objective.

## Useful views, not a new application inside the application

The primary page owns collection selection, rendition choices, pixel budget, optional model objectives, the batch queue, exact-pixel review, actual JPEG/resize/crop/blur previews, and the final PNG download. Native-pixel inspection and numerical quality do not require entry into the workshop.

The supporting workshop owns advanced encoder controls and five-arm full-generation comparison. Its old standalone export remains an explicitly unverified expert path for compatibility, not the main reviewed publishing-pack workflow. No old helper command was silently removed. No workshop score becomes an automatic success badge on publishing outputs.

Date-only metadata is a generated-PNG and publishing-pack boundary. Local JSON
protocols, model/review records and explicit research packets may contain
technical timestamps, hashes and settings. Keep them distinct from artwork
approved for publication; see [the threat model](THREAT-MODEL.md).

## Artist masks

Artist masks reduce the existing per-pixel channel allowance. Black (0) permits
no change; white (255) retains the automatic white/edge budget; gray scales that
budget down with integer flooring. A gray value of 128 with an automatic cap of
4 permits at most 2 channel levels. Masks cannot loosen white, edge, local RMS
or colour-difference gates. A fully protected raster has no editable budget and
produces a blocked item, never fallback noise.

In browser publishing, select artwork, expand **Artist masks**, choose the target
artwork and attach its PNG. **Preview masks** renders the overlay at every distinct
final size. Cyan means artist restraint; the counts include automatic limits too.
**Download exact cap raster** returns a grayscale PNG whose literal values are
0–16 allowed channel levels, so it will look nearly black in an ordinary viewer.
Remove mask restores automatic limits. Model execution is unnecessary for previews.

The terminal exposes Artist mask and Artist mask map under Advanced. A publishing
plan lists each final raster; press `m` to open its overlay in the local viewer.
The cache is private and date-only; opening it does not approve any output.

```powershell
.\riposte.cmd publish D:\Artwork --image IMAGE_ID --budget-mask D:\Masks\linework.png --plan
.\riposte.cmd publish D:\Artwork --image IMAGE_ID --budget-mask D:\Masks\linework.png --plan --view-budget 1
.\riposte.cmd riposte D:\Workspace --input D:\Artwork\drawing.png --budget-mask D:\Masks\linework.png --plan
.\riposte.cmd publish D:\Artwork --all --budget-map D:\Masks\riposte-private-mask-map.json --plan
```

A PNG mask must be one frame, 8-bit grayscale (`L`), without transparency or
nontrivial EXIF orientation; at most 2 MiB, 1,048,576 pixels and 4096 on either edge.
Use the clean, oriented canvas proportions. A reduced mask allows at most one cell
of aspect-ratio rounding. No rotation or crop is guessed. Every output pixel uses
the minimum of all mask cells whose normalized areas overlap it (`overlap-min-v1`).
This applies to enlargement and reduction; thin protected areas survive resizing.
The final output itself still never enlarges the master.

**Export mask map** explicitly downloads a private JSON file for `--budget-map`.
It contains `schema: 1` and `masks`: source SHA-256, width, height, canonical base64
8-bit pixels, and SHA-256 identity covering the version, resampling rule, source,
dimensions and pixels. PNG metadata and filenames are discarded. Up to 200 unique
source masks and 4,194,304 total mask pixels are accepted. The mask is bound to exact
clean date-only source bytes, so identical copies share it. A mask for an unselected
or changed source is rejected rather than silently ignored. Keep masks and maps
outside folders being sorted or scanned for protection; they are user input files,
not artwork. `_float_` only exempts sorting, not standalone image intake.

Saved named recipes still contain general settings only. Masks remain transient
in the browser until an explicitly started batch stores them in its private request
or an explicit map export downloads them. They never enter public PNG metadata or
publishing ZIPs. Each task and quality report bind the mask identity; resume, review,
image serving and packaging reject a changed budget. Resume uses the saved pixels
and needs no original mask file. The engine and independent post-output audit both
apply these limits. Exact output approval remains separate from the overlay.

CLI plans include `budget_revision`; pass it with `--budget-revision` when starting
to reject changed masks, sizes or quality limits. Terminal Start from a mask plan
does this automatically. Combined sorting binds the mask in its existing plan ID
and validates the source selection before replacing anything; use browser or the
ordinary publishing plan for its overlay. No-mask workflows retain their defaults.
These are damage constraints, not evidence of improved AI resistance.

Raster previews return at most three at a time. Browser Previous/Next previews and
terminal `[ / ]` retain the full batch selection. CLI `--budget-offset N --plan`
selects a preview page; `--view-budget N` opens an absolute numbered preview.
Processing skips preview rendering, so pagination never limits batch size.
