> Current implementation extension: **RIPOSTE 0.3.0**. The main product is now Protect & publish. See PUBLISHING.md, ENGINE-v03.md and WAVE-03-HANDOFF.md for current behavior; the following foundation specification remains historical where it describes earlier delivery scope.

# RIPOSTE — development specification

**Release:** 0.2.0 · **Status:** integrated workbench, controlled qualification and experimental coupled engine; pretrained efficacy unqualified.

## Product purpose

Prepare an artist's own illustrations for public display without viewer authentication or watermarking, while minimizing metadata exposure and developing measurable resistance to AI-mediated reuse. Source cleanliness, acceptable appearance, and demonstrated model-specific resistance are independent requirements. Passing one cannot compensate for failing another.

## Non-negotiable contracts

1. **Metadata contract:** every managed image and generated image artifact is rebuilt as an audited date-only PNG. Never persist raw image metadata, source bytes, source hashes, original filenames, original folder paths, or original metadata-bearing thumbnails.
2. **Organization contract:** use the requested year roots, English months, fixed pixel-area categories and collision-safe names. Create only needed directories. All existing content in the selected artwork root is in scope except the application's validated reserved state directory.
3. **Mutation contract:** default scans are read-only. Apply is explicit. Write and verify a new canonical image before unlinking its source. Do not preserve contaminated originals in an automatic backup, quarantine or Trash. On uncertainty, retain the unprocessed source and report `INCOMPLETE`; never manufacture a clean checkpoint.
4. **Protection contract:** no watermark payload, generic-noise fallback, audience gate, automated cloud upload, or universal-success claim. A model-derived candidate is still experimental until measured on the intended misuse task and publishing path.
5. **Evidence contract:** display fidelity, transport, model-proxy behavior, actual generation outcomes and review judgment separately. Do not convert surrogate divergence into a probability of protection.

## Requirement coverage

| User requirement | Implemented behavior | Boundary |
|---|---|---|
| Size/quality categories per month | Fixed pixel-area bins and displayed dimensions/bytes | Resolution is measured; artistic quality is not inferred |
| 2026 / 2025 / 2024 / other years | Exact roots, exact retained date | Other-year January files share one January directory |
| English month names; no empty scaffolding | Lazy folder creation, chronological UI tree | Native file managers may alphabetize names |
| Reconcile existing layouts | Recursive content-sniffed migration, canonical renaming, collision handling | Links, unknown files and unsupported formats require review |
| Date is sole retained image metadata | Fresh pixels, orientation/color handling, strict PNG audit | Structural encoding data is necessary to display an image |
| Remove location data and hidden container data | No copied EXIF/XMP/comments/profiles; no raw backups; no trailing/compressed tail data; invisible RGB zeroed | Not a pixel-steganography detector or disk-forensic eraser |
| Cleanup before protection | Complete workspace audit gates candidate creation/import | No claim of an adversarial filesystem-race sandbox |
| Image-integrated anti-AI methods | Coupled codec/mask/optional early-inpaint optimization, original EOT baseline and external-candidate path | Pretrained/GPU effectiveness unverified |
| Editing and video | Five-arm img2img/inpainting/SVD reference runners and separate video-objective research track | No built-in temporal defense or current proprietary-model guarantee |
| Visual application | Local library, inspector, lab, divider, delta view, transport table, evidence register | No batch protection queue or persisted human-review annotations yet |
| Third-party packages | Declared core/lab/test dependencies, local-only model loading | Dependencies and model licenses remain separate obligations |

## Architecture and source navigation

| Module | Responsibility |
|---|---|
| `policy.py` | Date policy, size categories, format limits and canonical naming |
| `sanitize.py` | Decode, orientation/color application, fresh raster, encoding and independent container audit |
| `store.py` | Safe paths, legacy/current identity, explicit state upgrade, locks, atomic clean/report writes and minimal catalog |
| `organizer.py` | Read-only plan, migration, residual checks and checkpoint audit |
| `metrics.py` | Paired real-codec transforms, fidelity measurements, difference visualization |
| `optimizer.py` | Retained EOT-VAE baseline and differentiable JPEG/rounding utilities |
| `models.py` | Fixed local KL/Tiny encoder adapters, early inpainting probe, safe runtime/file preflight |
| `views.py` | Actual codecs, approximate backward transforms, masks, spatial budgets and matched controls |
| `coupled.py` | One-raster masked/codec/early-conditioning projected optimizer |
| `qualification.py` | Three-control encoder qualification, protocol/model scope, committed reports |
| `generation.py` | Five-arm img2img/inpainting/SVD baseline generation and hash-bound frame review |
| `lab.py` | Clean public raster, candidate import/render, trial records and export |
| `benchmark.py` | Retained two-arm benchmark compatibility path; new work uses `generation.py` |
| `server.py` | Loopback API, transient session token, job queue and sanitized image access |
| `cli.py` | Explicit commands and machine-readable results |
| `static/` | Self-hosted HTML/CSS/JavaScript; no external assets or analytics |
| `methods.json` | Source-linked research register, including integration boundaries |

### Pipeline

```text
read-only scan
    └─ classify by decoder, date and dimensions
         └─ explicit apply
              └─ decoded pixels → orientation/color → fresh raster
                   └─ date-only PNG → audit → verified commit
                        └─ catalog clean output → unlink unchanged source
                             └─ rescan → COMPLETE or INCOMPLETE

COMPLETE checkpoint
    └─ clean master → public-size RGB raster
         ├─ model-dependent optimization
         └─ external candidate → sanitize and match dimensions
              └─ clean/candidate paired transforms
                   └─ inspect fidelity and surviving differences
                        ├─ controlled encoder qualification and five-arm generation/review
                        └─ explicit unverified export → audited PNG
```

The catalog stores a random asset ID, canonical relative path, retained day, date-basis enum, dimensions, encoded byte count, and a hash computed from the clean output. It never needs an original-input fingerprint. Failed-source references exist only transiently while processing; persistent failures are aggregate codes and counts.

## Canonical image profile

Output is non-interlaced RGB8 or RGBA8 PNG. Allowed chunks: `IHDR`, `IDAT`, `IEND`, and exactly one `tEXt` entry named `Creation Time` with a valid `YYYY-MM-DD` value. Audit verifies chunk CRCs and bounds, permitted color type/bit depth, decoded information, exact decompressed raster length, no hidden compressed tail, no trailing bytes, and zero RGB under fully transparent alpha.

Valid source profiles are applied before being discarded. Original color-profile metadata is not retained. Masters keep their dimensions and alpha. Public candidates are flattened on white, downscaled only when needed, and rebuilt again. User approval of appearance remains necessary; numerical fidelity is not an artistic-quality oracle.

Files are capped at 512 MiB and 60 million pixels. High-bit/HDR, multi-frame/layered and unsupported inputs stop rather than undergo undocumented lossy conversion. This profile is deliberately narrower than “all images accepted.” Broader codec support must preserve the same checkpoint and no-silent-loss properties.

## Date and layout rules

`download` means birth/creation time when the platform exposes it, otherwise modified time with a recorded fallback. `modified` is explicit filesystem modification time. `embedded` selects supported embedded date fields before the fallback. No guessed timestamp is invented from an ambiguous filename.

Use pixel area `p = width × height`: SML for `p < 10^6`; MED for `10^6 ≤ p < 4×10^6`; LRG for `4×10^6 ≤ p < 16×10^6`; XTL otherwise. These same thresholds apply in every month. Limits still cap admissible images. Naming uses the next available category suffix, padded to at least two digits. Gaps need not be filled and existing clean assets must not be renumbered simply for cosmetic compactness.

## Implemented optimization and controlled evaluation

See [ENGINE-v02.md](ENGINE-v02.md) for the complete algorithm, exact branch/view/mask definitions, integer budget, two-pass gradient aggregation, approximate JPEG backward, controls and limitations. `coupled-v1` is the new default engine; `encoder` retains the original experiment. No paper's protection claims attach to these original implementations.

Generation and qualification are integrated into the same trial IDs and sanitized candidate bytes. Evaluation compares three exact-magnitude sign controls in 24 contexts per encoder. Full-generation review uses five arms under matched seeds, fixed prompts and optional masks. All measurements remain scoped; codec-surviving pixel change is not a security result.

## Evidence states

| State | What is established | What is not established |
|---|---|---|
| `DATE_ONLY` | Canonical PNG/container checks passed | Model resistance |
| `PIXEL_TRANSPORT_ONLY` | Paired pixel measurements after stated operations | Editing or generation failure |
| `ENCODER_PROXY_ONLY` | Legacy encoder objective ran | Full task outcomes |
| `MASKED_ENCODER_PROXY_ONLY` | Coupled masked/codec encoder objective ran | Full task outcomes |
| `EARLY_DENOISER_PROXY_ONLY` | Optional early-conditioning objective ran | Complete diffusion-edit resistance |
| `CONTROLLED_ENCODER_PROXY` | Candidate and three controls compared through specified encoders | Statistically qualified protection |
| `CONTROLLED_GENERATIONS_UNSCORED` | Five-arm generation outputs available for review | Automatic judgment that misuse failed |
| `PAIRED_GENERATIONS_UNSCORED` | Earlier two-arm compatibility runner produced review output | Noise-controlled efficacy |
| `FILES_PRESENT_NOT_EXECUTED` | Selected local model files passed preflight | Successful loading, gradients or GPU capacity |

Every current candidate retains `ai_protection: UNVERIFIED`. Export acknowledgment changes permission to export, not evidence. Synthetic test oracles and pipeline doubles must remain visibly identified. An external candidate without recorded optimization settings must not inherit the defaults and acquire false held-out evidence.

## State upgrade and report commits

The installed project is `riposte-studio`, Python package/command `riposte`, current state directory `.riposte` and marker `RIPOSTE_WORKSPACE_1`. Legacy `.shroud` plus its exact old marker can be read without an automatic write. Explicit `upgrade` changes the state directory/marker only. Assets and trial IDs remain unchanged. Conflicting directories, unsupported markers and linked state fail closed. An interrupted directory rename before marker update is recognized and resumable.

Catalog reads use read-only SQLite. New trial/evaluation/generation reports use a monotonically increasing local sequence for ordering rather than image dates or random IDs. Artifact writes are already sanitized. The final JSON report is the commit marker; a caught failure rolls back newly generated trial/run artifacts. A power interruption can leave clean orphan data or a stale lock and requires inspection; this is not a filesystem-wide transaction or raw-source recovery journal.

Hashes bind cleaned candidate bytes and served generation frames. These detect changed bytes relative to trusted local reports; they are not signatures or protection against someone who can rewrite the entire application state. Model weight hashes are not source-image hashes and do not contain location metadata.

## API and command navigation

| Action | API | CLI |
|---|---|---|
| Read local runtime | `GET /api/runtime` | `doctor` |
| Inspect selected local VAE files | `POST /api/preflight` | `doctor --vae ...` |
| Upgrade old app state | `POST /api/upgrade-workspace` | `upgrade ROOT` |
| Create experimental candidate | `POST /api/guard` | `guard ROOT IMAGE_ID --vae ... --engine coupled` |
| Controlled encoder qualification | `POST /api/qualify` | `qualify ROOT TRIAL_ID --vae ...` |
| List evaluations | `GET /api/evaluations/{trial}` | Qualification JSON returned by command |
| Five-arm reference generation | `POST /api/generate` | `challenge ROOT TRIAL_ID --model ... --task edit\|inpaint\|video` |
| List generation reviews | `GET /api/generations/{trial}` | Generation JSON returned by command |
| Retrieve audited frame | `GET /api/generation/{id}/frame?relative=...` | Date-only files in managed state |
| Cancel eligible job | `POST /api/jobs/{id}/cancel` | Ctrl+C; re-audit after interruption |

The existing organizer, audit, catalog, candidate import, trial/image, benchmark and export endpoints remain in `server.py`. Request schemas reject unsupported fields. Model and source path inputs exist only in the operation context. The UI clears external-import path input after submission. No secret/raw-path-bearing exceptions are returned to the browser.

## Interface and failure requirements

The artwork is primary, controls stay beside their effect, and real state drives the interface. The source-removing apply gate and experimental-export acknowledgment are separate. Clean status does not imply AI resistance. Counters distinguish catalog state from the last completed audit. Missing models cannot be replaced with a plausible-looking preview.

Long-running model jobs use one active queue slot. Cancellation is checked between branches/frames and before commits, not inside a GPU kernel. The organizer is not advertised as midway-cancellable. A callback error or cancelled job must not publish a final successful report.

The server binds only loopback, uses a transient per-launch session token, strict host/origin checks, same-origin assets, no-store responses and code-only failures. It is an operator interface, not a multi-user remote service. The decoder/model runtime is not process-sandboxed; malicious local code/OS/filesystem races remain outside the promise. Details: [THREAT-MODEL.md](THREAT-MODEL.md).

## Qualification and next work

[WAVE-02-PLAN.md](WAVE-02-PLAN.md) records the delivered grouped work and the next real-model/video milestone. [VALIDATION.md](VALIDATION.md) records actual tests rather than aspirational pass counts. Hard acceptance gates remain cleanliness, artist-approved visual quality, task-specific improvement beyond controls, and separately evidenced transfer. Native GPU/model integration, performance, broader prompts/masks, text-guided video objectives, persisted review, batch queues, platform profiles and process isolation remain distinct work—not implicit capabilities of this release.
