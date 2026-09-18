# Category sorting and recovery / PAC-027BB

The user requested "CONTINUE TO PAC-027BB:" on 2026-09-18. This implements the
remaining PAC-027 scope: opt-in Year/Month/img-or-vid/Category/Size routing,
read-only exact destinations, trusted private original titles, stable media IDs,
manual assignments, and undo of assignments together with both media catalogs.
The CLI, terminal and authenticated local API/browser share the same backend.

The preview ID binds root identity, policy, rules revision, source file identity
and content, media catalog, private titles, last sort, assignments and allocated
paths. Apply checks it before creating state and again under the workspace lock.
Per-file rechecks and exclusive writes detect later changes; incomplete work
retains its recovery journal. This does not claim isolation from a hostile local
process continuously exchanging paths between operating-system calls.

Ordinary sorting keeps existing category folders and captures trustworthy new
original basenames. Generated numbered names, including compatibility Unicode
forms, remain unknown and require manual assignment. Duplicate content keeps
separate identities. Original names live only in private sort_titles records and
recovery journals, not public image/video rows, output PNG metadata or publishing
packs. Videos retain original bytes and metadata. Version-1 journals and legacy
catalog layouts remain readable. Version-2 undo restores title records in the
same SQLite transaction as images/videos and tolerates interrupted restoration.

Validation is local and synthetic. The final full suite passed 1062 tests with eight
platform skips (four Windows symlink privilege cases and four POSIX PTY cases).
An earlier follow-up passed 200 tests. The final full run in parent-suite.txt also covers the explicit unmatched/ambiguous totals added during parent acceptance review.
External contracts cover 387 signatures, 46 importable leaf modules and 56
application files (49 Python modules), with all stages and 13 negative-consumer
checks passing. The separate raw-source audit remains failing: 1103 diagnostics
in 37 files (49 checked). The new category_sort and sort_titles modules have no
raw-source diagnostics. Contract success does not certify source-body typing.

The Chromium fixture runs the shipping HTML/CSS/JS and covers discovery, rules
review/save/clear/load, duplicate writes, changed drafts, late inspection results,
explicit source replacement, stale server receipts, retry, undo consent and sort
IDs. It checks 1100x900 and 390x844 dialog geometry, reduced-motion emulation,
Escape and focus restoration. Screenshots were inspected locally. Its network
responses are controlled fixtures; separate FastAPI tests exercise the real
backend and filesystem. It does not establish screen-reader, Safari, mobile
hardware or translated UI acceptance. Existing publication/model tests retain
their own synthetic/optional-provider boundaries; no efficacy claim is added.

The fresh sdist/wheel and isolated installation contain byte-identical source,
including the new browser controller and moved docs. Installed CLI saved rules,
exact preview, apply, audit, byte-exact undo, and the actual Windows command
wrapper were exercised. Dependencies and environments were not replaced.

The premium UI strict scanner reports 66 findings. The scanner cannot see
64 externally bound button handlers; the new controls were checked in real
Chromium, while unrelated controls retain their existing evidence scope. The
root-DESIGN heuristic is resolved by the user's
maintained docs/DESIGN.md move and canonical map. One pre-existing publishing
textarea uses vertical resize outside this task. The category textareas use the
shared non-resizing style. No blanket clean static-audit claim is made.

Failed evidence is retained: core-first.txt found the old assertion forbidding
all original names anywhere in the catalog database; its replacement verifies
names are private while public rows and PNGs remain clean. core-second.txt caught
an unnecessary keyword passed through the existing combined-workflow test hook;
default dispatch was restored. browser-sandbox.txt records the blocked loopback
navigation before the permitted native run. build.txt records the denied global
uv cache; the successful build used the repository-local cache. An initial new
module type-inference failure is retained in raw-source-first.txt.gz; explicit annotations fixed
it without suppressions. Scratch browser profiles, builds, installed targets,
caches and screenshots stay under ignored .tmp/; only bounded validation and
source-bound acceptance artifacts are retained here.

Parent acceptance is recorded in parent-acceptance.json, produced by verify_parent.py.
It measures 10,000 actual directory entries with synthetic empty media files,
checks cancellation after 500 entries without writes, and verifies that a real
saved publishing request retains its image identity, clean bytes and request bytes
through two category moves and undo. Only the publishing model-execution stage is
replaced with a fixture; this is a reference-integrity check, not model acceptance.
