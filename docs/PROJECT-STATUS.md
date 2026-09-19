# RIPOSTE / current project status

Reviewed 2026-09-18. **Version 0.5.0; development audit open; release milestone pending.**
The working list, correction and resumption checkpoint are in
[todo-audit.PACER.md](../todo-audit.PACER.md). The four PACER CSVs remain frozen
until that work is complete and the specification can be reconciled together.
The last completed task, PAC-028, identified work; it did not implement its findings.

## Version, configuration and entry points

| Surface | Observed current state |
| --- | --- |
| `pyproject.toml`, `src/riposte/__init__.py`, `uv.lock` | 0.5.0 |
| Existing local installation | Editable 0.5.0 from this checkout; Windows Python 3.14.3 |
| Runtime declaration | Python >=3.11; minimum-version/native platform qualification remains PAC-034 |
| `INSTALL.ps1`, `INSTALL.sh` | Explicit setup; uv frozen/inexact editable install; optional Lab dependencies; no model weights |
| `START.ps1`, `START.cmd`, `START.sh` | Verify local installation, then menu; optional browser; no dependency installation |
| `riposte.cmd` | Direct local Python command forwarding; requires INSTALL first |
| Root/isolated typing configurations | Strict source audit is separate from external contracts; both target Python 3.13 |
| Root release manifest | Current development source/configuration/launcher/document snapshot; not a built-release certificate |
| Archives and old acceptance artifacts | Historical; never substituted for current build/qualification evidence |

An offline `uv sync --locked --offline --inexact --dry-run --cache-dir .tmp/uv-cache`
resolved the lock and proposed refreshing only the editable project. No installation
was performed by that check. Keep the existing uv environments and lockfiles.
Use [REBUILD.md](REBUILD.md) for explicit install, launch, test and build commands.

The previous root manifest described 0.4.0: 98 entries matched, 52 differed,
one path was missing and one historical wheel could not be read in this environment.
Its exact bytes are retained at
[history/v0.4.0/RELEASE-MANIFEST.json](../history/v0.4.0/RELEASE-MANIFEST.json).
The new root manifest covers its declared development inputs only. It does not
certify every historical distribution, test artifact, model or native interface.

## Current operation and privacy contracts

- Sort, RIPOSTE and Sort + RIPOSTE are independent choices. Startup, location
  selection and previews do not grant operation consent. The normal menu has nine
  actions; Workshop is optional. See [README](../README.md) and [CLI](CLI.md).
- Generated images and public publishing packs contain audited date-only PNGs.
  Private recovery history intentionally retains original bytes, metadata, names
  and timestamps. Private category provenance lives in `sort_titles` and recovery
  journals. These are separate from public catalog/export contents.
- Videos are sort-only and byte-preserved, including their metadata; optional
  `ffprobe` is required to inspect them. They do not enter protection processing.
- Category sorting has exact bound previews. Ordinary sorting still has the
  preview-drift finding in PAC-031. Undo supports recorded histories, but a hard
  process exit can leave a lock that blocks apply (PAC-029). Do not remove a lock
  based only on its age or assume its owner is dead.
- Visual acceptance, synthetic model regression checks and measured protection
  efficacy remain separate. Installed Torch/Diffusers/Transformers do not establish
  qualification of any real model or native platform.

## Evidence and its limits

| Evidence | Result and boundary |
| --- | --- |
| Fresh install/start/menu regressions | 29 passed on Windows Python 3.14.3; adapted subprocesses, not clean installation or native macOS/Linux proof |
| Fresh Windows entry checks | Real riposte.cmd version, START.ps1 linear menu open/exit, sort/category-rules CLI help: all exit 0; no artwork/model processing |
| Fresh five audit probes | All observations reproduced; confirms open defects, not repair acceptance |
| Fresh source/stub parameter parity | 387 signatures, 46 importable leaf modules, no mismatches; 56 source files match the reviewed snapshot |
| Retained external contract suite | All recorded stages passed; declarations/consumers/signatures/offline fixtures only |
| Retained source-body audit, current hashes rechecked | 1,103 diagnostics in 37 files, 49 Python files checked; still failing |
| Retained category acceptance suite | 1,062 passed, 8 platform skips; synthetic local scope recorded in the category evidence |
| PACER structural validation | Valid; documentation edits leave OGM-009/010/011/019 evidence stale, deferred under the CSV freeze |

Fresh review data: [milestone reconciliation evidence](../evidence/milestone-reconciliation-2026-09-18/review.json).
Prior implementation evidence: [category sorting](../evidence/category-sort/README.md),
[sort recovery](../evidence/sort-recovery/README.md), and
[typing](../typing/README.md). The CSVs and application source are unchanged by
this documentation/status reconciliation.

The four newly stale evidence records bind documentation changed by this review.
No requirement acceptance was refreshed or rewritten during the freeze. They
must be evaluated and reconciled with the other open evidence at the milestone;
structural validity does not mean evidence freshness or product completion.

## Documentation authority and milestone

Current source defines implemented behavior. README, CLI, UX-CONTRACT and this
status page describe the current checkout. DEVELOPMENT-SPEC, WAVE-04, VALIDATION
and the older threat-model text retain their historical scopes; their earlier
blanket ban on original retention is superseded by explicit private undo history.
The selective 0.5 merge record is historical evidence for that merge, not a current
whole-product acceptance report. See [CHANGELOG.md](CHANGELOG.md) for later work.

The milestone requires completed Markdown acceptance, coordinated guarded PACER
reconciliation, consistent release identity, fresh distribution equality/install
checks, launcher/configuration verification and explicit qualification limits.
It remains open. The next implementation priority is PAC-029, followed by PAC-030
and PAC-031. No tag, new release number or product-complete claim is made by this
review checkpoint.
