# PAC-041 - workspace storage and recovery health

Implementation: `riposte health ROOT`; terminal **Terminal & workspace > Storage
& recovery**; browser **Storage & recovery**. Optional, cancellable inspection
creates no workspace state, acquires/reclaims no lease, and prunes no files.

The report separates logical workspace/private/recovery/float bytes and volume
capacity. A suffix-based backup envelope is explicitly not required peak space
or a fit guarantee. All observed history headers are counted, including unfinished
and unverified histories. Backup hashes and restore conflicts are not checked;
the existing Preview undo remains the verification route. Markers do not prove
owner liveness. Slow filesystem calls can delay cooperative cancellation/budgets.

Windows capabilities use the documented [volume information flags](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw)
on the [resolved volume path](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumepathnamew).
These advertise support, not tested permissions, write/commit or crash durability.
POSIX reports statvfs read-only flags, with hard-link capability unknown. This
stage was executed on Windows, not independently on a POSIX filesystem.

Evidence retained here:

- `focused-first.xml/txt`: 5 failures, 20 passes, 1 skip. Four exposed Windows
  lstat/fstat ctime disagreement; one fixture attempted to read the locked lease.
  Fixed comparison uses cross-API identity/size/mtime and same-API revalidation.
- `focused-second.xml/txt`: 25 passes, 1 symlink-privilege skip.
- `focused.xml/txt`: health, lease and recovery regressions: 73 passes, 1 skip.
- `suite.xml/txt`: 1,608 passes, 11 platform/privilege skips; five browser tests
  run separately. Synthetic/model plumbing evidence does not qualify efficacy.
- `native.xml/txt`: all five actual Chromium tests passed, including the new
  health workflow and existing recipe/category/duplicate/publication interfaces.
  `wide.png` and `narrow.png` were visually inspected. Real-server inspection
  preserves fixture bytes/mtimes; partial/cancelled UI states and offline/late
  replies are injected. Keyboard Escape and narrow focus restoration are tested.
- Earlier native failures are preserved: missing harness polling and a real
  hidden narrow-screen opener. `browser-final.xml/txt` records the focused pass.
- `contract-review.json`, `contracts-final.txt`: reviewed external declarations,
  79 application files, 561 signatures, 65 importable leaf modules; seven stages
  pass and 13 negative consumers produce their expected diagnostics.
- `raw-source-first.txt`, `raw-source.txt`, `raw-delta.json`: separate failing
  strict source audit: 862 diagnostics in 36 of 68 files, 21 additional calls to
  existing untyped terminal report helpers versus PAC-040; no suppression or source-body
  certification. The final new health module has no diagnostics in this audit.
- `ui-static.json`, `ui-review.json`: 88 static findings with scoped dispositions;
  not a global UI pass. The optional design.md linter is unavailable offline.
- `documentation.json`, `build.txt`, `verification.json`: shipping parser,
  local links, retained historical documents and wheel/sdist byte parity.
- `requirement-review.json`, `OGM-*.json`, guarded operation receipts and
  `governance.json`: scoped source-bound PACER reconciliation and final state.

Commands are recorded by the reports. Tests use the existing Windows dependency
environment. No new installation, physical user terminal, screen-reader/human
acceptance, pretrained model efficacy or filesystem write qualification is claimed.
