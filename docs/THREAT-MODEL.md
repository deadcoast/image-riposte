# Threat model and data lifecycle

Maintained for the 0.5.0 development checkout, reviewed under PAC-039. This guide
describes current boundaries, including private undo history and independent
workflows. See [the current contract](CURRENT-CONTRACT.md) for exact artifact
scope and [project status](PROJECT-STATUS.md) for qualification limits.

## Protected assets and attacker access

The artist publishes a human-readable image. A recipient can obtain those published pixels; RIPOSTE does not encrypt them or control a recipient's software. The anti-AI track attempts to make specified model-mediated reuse harder while preserving acceptable appearance. It does not prevent downloading, manual redrawing or redistribution of the published file.

The privacy track addresses image-container metadata and application-created copies. It assumes a trusted local operator and operating system, a deliberately selected artwork folder and user-supplied local model weights. It does not assume the public model is cooperative.

## Location-data edict as an executable boundary

For generated PNGs, RIPOSTE discards the source metadata container and rebuilds from pixels under a tiny allowlist. Date is the only retained descriptive image field. Hashes in public image-processing reports refer to cleaned artifacts. Private sorting/recovery and duplicate analysis also hash original bytes for identity and integrity; these hashes can fingerprint originals and are not anonymous identifiers.

Explicit sorting intentionally persists original bytes and metadata in private `.riposte/sort-history/` backups, with original paths, names, hashes and modification times in recovery journals. The private catalog's `sort_titles` table retains original filenames and category provenance. Keep this state out of public uploads; deleting it removes undo/recovery capability. Standalone RIPOSTE leaves selected originals unchanged and stores sanitized input snapshots. Generated image writes contain audited PNG data, but recovery backups deliberately contain original data. Sorted videos retain their complete original bytes and embedded metadata.

A source that cannot be safely decoded or faithfully converted remains where it was and prevents a complete whole-workspace sort/audit. An ordinary sort may still process valid planned files and retain their recovery history. Standalone RIPOSTE validates selected inputs without requiring an unrelated whole-folder cleanup. Unknown files are not deleted speculatively. Known sidecars and thumbnail caches require explicit discard authorization; float directories are excluded from sorting. Empty former directories may be removed after migration. Neither an incomplete sort nor generated-image sanitation claims to erase every original byte on disk.

The application does not recursively cleanse unrelated folders, an external model directory or an external candidate's original file. Importing an external candidate sanitizes the pixels copied into the managed workspace; its source is read-only. Global filesystem cleanup was neither requested nor safely inferable from an artwork-root operation.

## What the PNG audit establishes

An accepted generated image has a validated RGB8/RGBA8 PNG structure, correct CRCs, the retained day, and no unapproved ancillary fields, appended bytes or extra compressed tail. Fully transparent pixels cannot conceal nonzero RGB. Embedded thumbnails, editing history, comments, EXIF, XMP and source color profiles are not copied.

This is **container and explicit hidden-alpha sanitation**, not a proof against all steganography. Information can be encoded in visible pixel choices, subtle least-significant-bit patterns, partly transparent artwork, depicted street signs, signatures or recognizable places. A raster-preserving cleaner cannot honestly certify that it has removed every such signal without examining and potentially changing the artwork itself. No location recognition, facial identity extraction or OCR is performed by this application.

Filesystem ownership, creation timestamps, extended attributes, alternate data streams, journals and physical storage remnants are outside the image-container audit. New files avoid intentionally copying source extended attributes/streams, but RIPOSTE does not enumerate or certify the host filesystem's entire metadata state. Unlinking a file is not a promise of forensic erasure. Other applications, browser extensions, sync clients, OS thumbnails, swap and backups are not controlled.

## Local web interface

The launcher binds only loopback. API calls require a per-launch token carried by a custom header; the initial browser URL places it in the fragment rather than server request logs. The app keeps it in browser session storage. Host/origin checks, cross-site request rejection, local-only assets, a content-security policy, disabled API docs, no-store responses and safe error codes reduce accidental exposure.

The private interface is an operator tool. Viewers of exported artwork never interact with it or authenticate. Do not expose its port using a reverse proxy or remote tunnel. A compromised browser, malicious extension or malware running as the user is outside this release's security boundary. This is not a remote multi-user service.

Decoding and model execution currently occur in the application's process/thread context. Pixel/file caps reduce obvious resource excess, but they do not replace a sandbox or prove codecs free of vulnerabilities. Process isolation, platform privilege reduction and dependency-integrity qualification remain specified future hardening. This release is not certified for ingesting intentionally weaponized files from hostile parties.

## Data stored by the application

| Item | Retained contents |
|---|---|
| Clean master | Fresh pixels and day only |
| Catalog | Random ID; canonical path; day/date-basis; dimensions; bytes; clean-output hash |
| Trial | Clean/candidate/difference date-only rasters; numerical fidelity/proxy/transport results; clean-derived references |
| Encoder qualification | Clean control PNGs; safe model weight hashes; view/mask scope; numerical comparisons; unknown protocol retained as unknown |
| Generation review | Date-only frames; safe model component hashes; fixed conditioning; seeds/views; filter flags; numerical comparisons; explicit unscored status |
| Legacy benchmark | Earlier date-only paired frames and fixed settings; compatibility data |
| Publishing pack / workshop image export | Date-only PNGs; main packs require accepted outputs, while the expert workshop export is explicitly unverified |
| Sort recovery | Private original bytes/metadata; journal paths, names, hashes and modification times |
| Private title provenance | Original filenames, categories, matched terms, rule revision and hashes in `sort_titles` |
| Sorted video | Original bytes and embedded metadata; no image-sanitation claim |
| Explicit duplicate report export | Plaintext paths/findings; JSON also retains scan root, options, identity hashes and detailed evidence |
| Experiment/cohort/panel state and packets | Local commitments, technical identities/settings, timestamps where needed and review material; not publishing packs |
| Persistent failure report | Fixed error codes and aggregate counts; no raw exception or source-path dump |
| Transient jobs | In-memory status and sanitized results; user-entered local resource paths used only to perform the requested operation |

The reserved `.riposte` directory is accepted only with the expected workspace marker. A valid legacy `.shroud` directory can be read without migration; explicit upgrade changes its state identity without rewriting artwork. Conflicting states are rejected. The documented interrupted-rename state is recognized for resumable upgrade. An unrelated folder with that name is a conflict, not an excuse to skip user files. The system does not claim to securely adopt an attacker-written database or arbitrary files planted inside a trusted state directory.

## File safety tradeoffs

Explicit Apply with a matching preview and source-removal acknowledgement is the boundary for source replacement. Sorting creates private recovery material before destructive replacement, verifies the planned source and destination, writes/verifies the output and records progress. A failure can leave a source, a clean output and/or recoverable private backup. Undo and interrupted-sort recovery validate journal/file identities and reject conflicts rather than overwrite unknown changes. Selected-input standalone protection does not remove its source files.

The write protocol and lock reduce accidental collisions and concurrent RIPOSTE operations. They are not a transaction across the filesystem and database. A hostile process can race directory changes; a power loss can leave partial state. Recovery reclaims a matching abandoned marker only while holding the exclusive OS lease; unknown markers remain blocked. Do not delete lock markers or the persistent root lease file. A changed or missing catalog file blocks clean qualification. Preserve available files/history and follow the [current recovery boundary](CURRENT-CONTRACT.md#recovery-and-locks).

## Anti-AI claims allowed by this release

The application may report the exact perturbation budget, observed pixel fidelity, actual transport measurements and encoder-proxy changes produced by its run. Controlled qualification may compare exact-magnitude sign-scrambled controls under stated encoders and transforms. The five-arm reference runner may report generated outputs, with its model-family and evaluation limitations. Same-seed output differences and pipeline content-filter flags do not establish protection. Three controls do not confer statistical qualification.

It may not report “AI-proof,” “cannot be recognized,” “prevents all copying,” or an uncalibrated protection percentage. It may not inherit efficacy numbers from a paper whose implementation and model conditions were not reproduced. Export acknowledgment changes permission to export, not the scientific evidence state.

## New report and model boundaries

Trial/export and generation-frame access verify cleaned hashes and retained dates. Only report-listed frame paths inside the corresponding run are served. Reports are committed after sanitized artifacts. Caught failure removes partial new trial/evaluation/run artifacts; power-loss orphans may still exist and require inspection. Report hashes detect changes relative to a trusted report, not an attacker who can rewrite the report itself.

Model paths are transient operator inputs. Weight fingerprints identify local model files, not raw source images. The loader fixes known classes/components, requires safetensors for the learned model path and disables automatic Hub access. This reduces incidental downloads and unsafe checkpoint use; it is not a sandbox, a model license audit, or certification that all configuration/library behavior is harmless. Install trusted packages/models outside the artwork root.

GPU/CPU tensors, framework caches, error behavior in third-party libraries and process memory are not forensic-erasure targets. The application avoids deliberately logging model/source paths in its own structured responses. Dependency diagnostic output under operator control can still mention local installation details; it is not embedded into artwork or normal catalog reports.

This distinction is the central product boundary: **privacy sanitation is enforced now; broad AI-reuse resistance is the experimental objective, not a completed guarantee.**


## Publishing boundary

The primary publishing path adds numeric fidelity gates and exact-file review/export binding, not an efficacy certificate. Its request records use technical model identities and cleaned-image hashes, excluding raw source filenames/paths and raw metadata. This restriction describes publishing records, not private sort recovery or user-requested duplicate reports. Publishing packs contain accepted date-only PNGs only. Review receipts are local integrity relationships, not signatures against a hostile machine owner. Cancellation retains completed sanitized outputs. Existing copies and previously downloaded packs cannot be erased remotely. The temporal branch measures first-step predicted-latent dynamics, not decoded-video suppression or text-guided protection. See [Publishing](PUBLISHING.md) and [current research qualifications](PCUC.md).
