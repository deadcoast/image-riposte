# Current workflow and data contract

This guide describes the 0.5.0 development checkout, reviewed for PAC-039 on
2026-09-20. Application source defines implemented behavior. Historical design
documents record their original scope; they do not override these current
boundaries. See the [documentation map](README.md), [command reference](CLI.md)
and [current project status](PROJECT-STATUS.md) for entry points and qualifications.

## Independent workflows and consent

**Riposte Sorter** offers Sort, Dry Run and Enter Path. It uses the opinionated
date/media/optional-category/size layout; **Full Sort Workshop** exposes detailed
settings. Current years use `Year/Month/img-or-vid/[Category if found]/Size`.
Missing, tied or unavailable category matches leave the ordinary route available.
Sorting skips `_float_` and `__float__` directories, case-insensitively, at every
depth. Standalone RIPOSTE can still process their images.

**RIPOSTE** processes selected images into a results workspace, without sorting or
replacing those inputs. **Sort + RIPOSTE** combines the operations with explicit
source-replacement consent. Duplicate Finder is a separate, read-only scan;
including float directories is independently selectable.

Startup, folder selection and preview are not consent to modify files. Sorting
apply requires a matching preview receipt and source-removal acknowledgement;
the terminal requires `REPLACE`. Changed files or options require a new preview.
The combined receipt binds both sorting and protection choices. Dry Run has no
apply action. Undo has its own preview and confirmation; terminal/browser bind
the inspected sort ID. Direct CLI users can name it with `--sort-id SORT_ID`.

Publishing candidates require separate visual acceptance and acknowledgements
before inclusion in a publishing pack. Preview, model scores, opening an image
and running an experiment do not supply that approval. The expert workshop's
standalone export is an explicitly unverified path, documented separately.

Implementation: [sorting and intake](../src/riposte/intake.py),
[sort execution](../src/riposte/organizer.py), [publishing](../src/riposte/publication.py),
[terminal actions](../src/riposte/terminal/state.py).

## Generated image metadata

Generated image files are reconstructed and audited PNGs with day-only
`Creation Time` (`YYYY-MM-DD`) and an allowlist of structural chunks. Source
EXIF, XMP, comments, profiles, thumbnails and editing history are not copied into
them. Public publishing packs contain only accepted PNGs; their ZIP entries use
day-only midnight timestamps with no comments or extra fields.

This promise concerns generated image containers and publishing packs. It does
not describe all files in the artwork root, private databases, recovery backups,
technical reports, explicitly exported JSON/CSV evidence or the host filesystem.
Sorted videos retain their original bytes and embedded metadata. Visible pixels
can still identify people, places or an artist; the cleaner is not OCR, location
recognition, universal steganography removal or forensic erasure.

Implementation: [PNG writer](../src/riposte/sanitize.py),
[container audit](../src/riposte/sanitize.py),
[publishing packs](../src/riposte/publication.py).

## Public outputs versus private state

| Artifact | Actual contents and sharing boundary |
| --- | --- |
| Generated PNGs | Reconstructed pixels and retained day; visible content still matters. |
| Publishing pack | Accepted PNGs only; excludes originals, reports, model identities and recovery state. |
| Sorted videos | Byte-preserved video files, including embedded metadata; sorting does not sanitize them. |
| `.riposte/sort-history/SORT_ID/` | Private original-byte backups and journals with original names, paths, hashes and modification times. Necessary for exact undo and interrupted-sort recovery. |
| Private catalog `sort_titles` table | Original filenames, category choices, matched terms, rule revision and image hash for private provenance/search. Public artwork filenames do not inherit the titles. |
| Publishing `inputs/IMAGE_ID.png` | Sanitized snapshots for selected raw inputs. Resume/review/packaging use these snapshots; they do not require continued access to the original input paths. |
| Technical protocols, reports and reviews | Local IDs, hashes, model/settings identity and, where needed, technical timestamps. These records are not subject to the PNG metadata allowlist. |
| Duplicate Finder JSON/CSV exports | Explicitly requested plaintext evidence with member paths and findings; JSON also contains the scan root, identities, options and detailed evidence. Inspect before sharing. A scan alone does not create these exports. |
| Experiment/panel review packets | Explicit research exports containing their documented review material and technical records. They are not publishing packs or an efficacy certificate. |

Keep the private `.riposte` directory (or a supported legacy `.shroud` workspace)
out of public uploads. Deleting recovery history removes recovery capability.
Do not treat the entire selected folder as a shareable, metadata-clean export.
See [publishing](PUBLISHING.md), [Duplicate Finder](DUPLICATES.md),
[research protocols](PCUC.md) and [threat model](THREAT-MODEL.md).

Implementation: [recovery history](../src/riposte/sort_history.py),
[private title records](../src/riposte/sort_titles.py),
[duplicate exports](../src/riposte/duplicate_review.py).

## Recovery and locks

Sorting records private recovery material before destructive replacement.
Undo checks the selected history and file identities and stops on conflicts;
it does not overwrite unknown changes. Preserve both history and surviving
files when recovery fails. An ordinary sort may process valid planned files
while reporting blockers; an incomplete result does not mean every original was
removed. Whole-workspace audit and selected-input publishing have different scope.

The persistent root file `.riposte-operation.lease` is an OS lease target, not an
active-process indicator. The application can reclaim its matching abandoned
`operation.lock` only after acquiring the exclusive lease. An unknown or
unmatched marker remains blocked; neither age nor a PID proves safe ownership.
Keep the lease file and lock markers in place. Follow the operation's recovery
message; do not manually delete a lock to force an operation through.

Implementation: [workspace locking](../src/riposte/store.py),
[sort recovery](../src/riposte/sort_history.py),
[shared guidance](../src/riposte/recovery.py).

## Superseded historical claims

| Historical claim and location | Current replacement |
| --- | --- |
| DEVELOPMENT-SPEC: absolute ban on persistent originals, no rollback copy, hashes only after cleaning | [Public outputs versus private state](#public-outputs-versus-private-state) and [Recovery and locks](#recovery-and-locks): explicit sorting retains private recovery originals and provenance. |
| DEVELOPMENT-SPEC and early engine/lifecycle documents: date-only language applied to the whole workspace | [Generated image metadata](#generated-image-metadata): applies to generated PNGs and publishing packs, with explicit private-state/video/report boundaries. |
| DEVELOPMENT-SPEC and WAVE-04: seven actions, 27 commands, sorting as the required first step | [Independent workflows and consent](#independent-workflows-and-consent) and the [complete current CLI inventory](CLI.md#command-inventory). |
| DEVELOPMENT-SPEC: fixed three-year sorting buckets | [Independent workflows and consent](#independent-workflows-and-consent): actual year/month directories, preserving legacy catalog compatibility. |
| TERMINAL-DESIGN.spec and old validation/merge reports: then-current interface and acceptance statements | [Current UX contract](UX-CONTRACT.md), [CLI](CLI.md) and [project evidence with its limits](PROJECT-STATUS.md#evidence-and-its-limits). Historical results prove only their recorded stage. |

The historical bodies and archived documents remain preserved. The current
threat model and publishing guide are maintained documents; PAC-039 corrects
their conflicting old paragraphs. Their exact pre-edit bytes and the historical
preservation check are retained in [documentation evidence](../evidence/documentation-contracts/README.md).

## Evidence and qualification limits

Local hashes and review receipts detect changes relative to trusted records;
they do not authenticate an independent person or defeat a hostile machine
owner. Visual acceptance, deterministic synthetic tests, tiny-model numerical
plumbing and measured protection efficacy are separate kinds of evidence.
No document cleanup upgrades those qualifications. Clean-install/platform
qualification remains shelved under PAC-034; the release milestone remains open.
