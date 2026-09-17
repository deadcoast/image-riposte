# Selective-patch closure

PAC-006 resolves the malformed NDL-003 asset list through the guarded PACER
`correct_assets` command. The [reviewed mapping](correction-review.json) retains
all 58 original OVR identities. The original prose, exact before/after values,
mapping and actor evidence remain in the nodule's dated Notes. The command was
previewed and applied through the updated PACER source checkout's CLI; its
[application receipt](correction-applied.json) changes only the nodule register.

The command's implementation and tests are in
`C:/Users/ryanf/github/ASSETS/PACER`, under its task 36. It passed 23 focused
correction cases and the full 208-test PACER suite, Ruff, source registration
and mypy. Existing removal, freshness and absorption guards remain enforced.
No global plugin installation was changed.

## Current evidence

- [Continuity](continuity.json): all 47 application files match the reviewed
  audit repairs. The ten later source changes are explicitly attributed to that
  authorization. Both original ZIP checksums, every incoming file decision,
  preserved dependency declarations and original merge snapshots match.
- [Terminal regressions](terminal.txt): **187 passed, 4 skipped**. This includes
  all 49 patch revision cases and the repaired linear form navigation. Skips
  are the existing POSIX pseudo-terminal cases on Windows.
- [External contracts](contracts.txt): **PASS**, with 318 matched signatures,
  38 importable leaf modules, 9 runtime fixtures, 10 tooling regressions and
  all 13 expected invalid-consumer diagnostics. Outputs were redirected into
  `contracts/` so previous accepted evidence stays intact.
- The original selective-merge failures remain unchanged under `patch-v050/`.
  This continuation's first terminal run had a missing parent directory for
  pytest's local temporary path. Its output and XML are retained as
  `terminal-initial-harness.*`; the replay script now creates that parent.

Replay the continuity and terminal checks from the RIPOSTE root:

```powershell
uv run --frozen --no-sync --cache-dir typing/.cache/uv python scripts/verify_patch_continuity.py
```

Replay contracts into the separate evidence directory:

```powershell
@'
from pathlib import Path
import sys
sys.path.insert(0, str(Path('typing').resolve()))
import check
check.EVIDENCE = Path('evidence/patch-closure/contracts').resolve()
raise SystemExit(check.main())
'@ | uv run --project typing --frozen --cache-dir typing/.cache/uv python -
```

`scripts/verify_v05_merge.py` remains an immutable-snapshot historical receipt.
The new verifier explicitly checks continuity through the later authorized
repairs instead of rewriting that earlier proof boundary.
