# Saved category rules / PAC-027BA

The user requested "begin the next step of development" on 2026-09-18.
This bounded continuation of PAC-027B implements reusable rules, explicit CLI
save, and read-only filename matching. PAC-027BB retains destination previews,
movement, original-title provenance, assignments, undo and terminal/browser/API
sorting integration. No new native visual or model-efficacy acceptance is claimed.

Rules use version 1 private JSON, 32 categories, normalized whole words and
contiguous phrases, explicit aliases, category-specific exclusions and integer
priority. Highest priority wins; equal highest matches stay ambiguous. Slugs are
unique normalized path components, with Windows device names and Uncategorized
reserved. Rename with an explicit existing slug to keep folder identity.

Preview creates no state. Save requires explicit --save and the previously read
revision, checks again under the workspace lock and after flushing a unique
temporary, then atomically replaces only the rule file. Reads are bounded to
1 MiB and reject malformed/duplicate-key/unsupported-version JSON, links and
nonfiles. Failed commits retain previous rule bytes. This is protection against
ordinary concurrent application/external edits, not a sandbox for hostile local
processes that continually exchange directory entries during system calls.

Only rules are saved. Filename samples and matching results remain transient;
generated numbered titles are excluded until trustworthy provenance or manual
assignments exist. Saving rules leaves the existing sort layout and undo intact.
Legacy .shroud workspaces retain their namespace. Shared-service effects distinguish
inspection from saving rules. The current terminal Categories form remains a
session draft; use `category-rules` for persistence.

The user's moved design documents remain in docs/. Their live PACER paths,
typing inventory and sdist manifest were repaired. No application media or model
files were used during validation.

Final validation: `suite-permitted.txt/xml` records **1,030 passed, eight platform
skips**. The native-browser regression passes with loopback/browser access.
`contracts.txt` and `typing.json` record all external stages passing: 375
signatures, 44 importable leaf modules, 53 application files and 13/13 expected
negative diagnostics. `package.json` passes fresh package/install/wrapper checks.
`raw-source.txt` still reports **1,076 strict diagnostics in 37 files (47
checked)**; the new rule module has none. The new CLI command contributes three
existing-style untyped decorator/dispatch diagnostics. No clean raw-source claim
is made. `index-final.txt` records source/typing registration reconciliation.

Acceptance reports bind the new requirement and the affected existing workflow,
packaging, menu, recovery, commit-safety and discovery requirements to these
fresh bounded regression checks. Prior native-console evidence remains historical;
these checks do not establish new interactive category-save or browser category
controls, model execution, protection efficacy or category sorting/recovery.

Evidence retained here:

- `focused-first.txt.gz`: original failure output, losslessly compressed. 82
  tests passed, one skipped, and one oversized-data parameter caused setup and
  teardown errors because pytest used the megabyte value as a Windows environment
  variable test name. Explicit short parameter IDs repaired the test harness.
- `focused.txt/xml`: 83 focused tests passed, one Windows symlink test skipped.
  Includes read-only behavior, matching semantics, Unicode, unsafe slugs, stale
  revisions, malformed state, interrupted commit, concurrent edit during flush,
  locks, legacy state, CLI/service parity and ordinary sort/undo compatibility.
- `suite.txt/xml`: first full sandbox run: 1,029 passed, eight platform skips,
  one existing native-browser Page.navigate timeout. The rerun with local browser
  access is retained separately in `suite-permitted.txt/xml`.
- `contracts-first.txt`: passing external contracts. `raw-source-first.txt`
  exposed one new-module type-inference diagnostic; the explicit dynamic match-row
  annotation was corrected. The later source audit remains a separate failing
  application-wide check, not a contract pass.
- `source-review.json`: four reviewed application changes; every other source
  hash matches the previous reviewed snapshot. New/changed declarations have
  been checked against their source, not generated merely to suppress drift.
- `verify_package.py` and `package.json`: byte comparison of fresh source/wheel/
  installed package, moved-document sdist inclusion, installed preview/save/reload
  and the real Windows wrapper. Fixtures are filenames only, not decoded media.

Commands are run from the repository root using existing environments and
repository-local cache/temp directories:

```powershell
uv run --no-sync --frozen --cache-dir typing/.cache/uv python -m pytest -q -o cache_dir=.tmp/category-rules/cache --basetemp .tmp/category-rules/suite-permitted --junitxml=evidence/category-rules/suite-permitted.xml
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv build --offline --cache-dir typing/.cache/uv --out-dir .tmp/category-rules/dist
uv pip install --offline --no-deps --cache-dir typing/.cache/uv --python .venv/Scripts/python.exe --target typing/.cache/category-rules/installed .tmp/category-rules/dist/riposte_studio-0.5.0-py3-none-any.whl
uv run --no-sync --frozen --cache-dir typing/.cache/uv python evidence/category-rules/verify_package.py
```
