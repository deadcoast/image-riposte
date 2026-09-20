# PAC-037 — guided category editing

User authority: “Next: PAC-037 — guided category editing”. NDL-023 / OGM-024.

The browser replaces rule syntax fields with category rows: display name, stable
folder name, matching phrases, exclusions and priority. Validation associates
correction text with each field and focuses the first invalid field on Review.
Loaded folder names survive display-name changes. Saved rules load automatically
unless a user already edited a draft. Reload protects unsaved input. Review is
read-only and Save explicitly replaces the reviewed revision.

Per-file native selectors offer saved categories, keep-current, automatic and
explicit uncategorized choices. Fifty files render per page, preserving choices
across pages. Changes invalidate prior previews and acknowledgements. Stale
destinations are marked; reset recovers pending choices for removed files/rules.
Categories remain optional. CLI and terminal expert syntax are unchanged.

## Executed evidence

- `focused.txt` / `focused.xml`: 95 parser, rules, API, terminal, sort and browser-job
  regressions passed; one unavailable Windows symlink test skipped; native test
  selected separately.
- `browser-final.txt`: shipping HTML/JS in real Chromium with fixture responses.
  Discovery, inline validation/focus, stable rename, duplicate fields, protected
  reload, stale reviews/previews, explicit save/apply/undo, optional categories,
  paged selections, native Tab/arrows/dropdown/Escape and narrow layout pass.
- `live-final.txt`, `browser-live.json`, `live_browser.py`, `live_probe.js`: real
  authenticated server and Chromium, without fetch mocks. Empty rules remain
  sortable; create/review/save/rename, actual concurrent-rule conflict, guided
  assignments, exact preview, consented sort and undo pass for 58 generated PNGs.
  Two float files are excluded. Every original byte and mtime is restored, with
  no unexpected public files. The known persistent operation lease is internal.
- `wide-rules.png`, `narrow-rules.png`, `narrow-choice-open.png`: actual rendering,
  including the platform-owned select popup. Screenshots are visually reviewed.

Initial failures are retained: sandbox Chromium timeout, old probe references to
removed syntax fields, a test key sequence that did not open the native dropdown,
and live harness assumptions about `state.jobs` and the persistent internal lease.
These were harness corrections; none are evidence of a passing pre-fix application.

- `suite.txt` / `suite.xml`: 1,499 passed, nine platform skips, three native checks
  selected separately. `native.txt` / `native.xml`: all three Chromium checks pass.
  The final close-status-only JavaScript refinement was followed by repeated native
  and live-server checks; all Python application files remain byte-identical.
- `contracts.txt`, `contract-review.json`: all seven external contract stages pass,
  531 signatures, 62 leaf modules, 73 application files and 13 expected negative
  diagnostics. `raw-source.txt`: strict source typing still fails with 823 errors
  in 36 files; settings and runtime Python are unchanged.
- `build-local-cache.txt`, `verification.json`: fresh wheel and sdist contain every
  reviewed application byte; current README and design/UX/status docs match sdist.
  The package check identified that PROJECT-STATUS.md was omitted; MANIFEST.in
  now includes it. This is packaging coherence, not clean-install qualification.
  The initial default uv cache was inaccessible; the repository-local cache worked.
- `ui-static.json`: the generic static audit reports 81 findings (78 literal
  buttons whose handlers are in separate scripts, one documented native-select
  ownership decision, the existing runtime-populated download link, and the
  existing duplicate settings textarea). `ui-review.json` records the disposition.
  This is not a global UI audit pass. `docs/DESIGN.md` and `docs/UX-CONTRACT.md`
  remain the intentional design authority; no duplicate root DESIGN file is added.
- `inventory-final.txt`, `acceptance-review.json`, `OGM-*.json`, `governance.json`:
  guarded source registration, refreshed affected requirement evidence, and final
  PACER validation/closure. Earlier manual evidence artifacts are preserved.

Current implementation does not qualify independent human
usability, assistive technologies, other terminal hosts, clean installation,
filename classification accuracy or protection-model efficacy. PAC-034 remains
shelved. The strict source typing debt is reported separately from external contracts.
