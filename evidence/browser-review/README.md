# Browser publication review repair

The browser now waits for both current preview images to decode before enabling
visual acceptance. Each review fetches fresh pixels through the server's existing
artifact checks. Loading errors leave approval disabled, and rejection remains
available. Opening another image clears previous pixels immediately.

The original candidate must load successfully before a difference or transport
preview can be used during review. Changing the preview resets the visual-quality
checkbox. Both explicit acknowledgements remain necessary. Pending decisions and
workshop handoffs disable repeated actions; a response for an earlier dialog
cannot close or navigate away from a later review. A returned stale receipt is
reported as unapproved. Closing releases the review's object URLs, and late image
responses cannot restore closed or superseded previews.

## Source and tests

- [Shared loader](../../src/riposte/static/app.js): fresh requests bypass both URL
  cache and in-flight request reuse; per-load identity survives same-path retries;
  decoding returns success/failure and owned URLs are released.
- [Publication UI](../../src/riposte/static/publish.js): readiness, acknowledgement,
  session and pending-action guards, visible loading/failure guidance, and native
  dialog close cleanup.
- [Regression entry point](../../tests/test_browser_review.py) and
  [JavaScript cases](../../tests/browser_review.cjs): execute the shipping
  publication module and shared loader with controlled fetch/decode timing.
  The native case uses the actual HTML, shared loader and publication module in
  an isolated headless Chrome profile, with a localhost fixture server and real
  PNG decoding. It checks successful decode, corrupt-image failure, fresh reopening,
  native close events, acknowledgement reset and approval/rejection availability.
  The HTTP responses are fixtures; the native case does not exercise the backend.

## Verification

| Evidence | Result |
| --- | --- |
| [Initial reproduction](red.txt) | 14 failed, 2 passed before the source changes |
| [Browser regressions](browser.txt) | 21 passed, including native Chrome |
| [Publication regression set](focused.txt) | 117 passed before adding the native case |
| [Full suite](full.txt) | 820 passed, 7 platform skips; 2 dependency deprecation warnings |
| [External contracts](contracts.txt) | 320 signatures; all contract checks pass |
| [Source inventory](inventory.txt) | 47 source files, 442 symbols, 1,735 symbol edges; PASS |

The first native probe used Chrome's dump-DOM virtual-time mode and timed out
waiting for a queued native close event. That harness failure is retained in
[native-virtual-time.txt](native-virtual-time.txt). The final test uses Chrome's
debugging protocol with real event timing; the same close-event assertion passes
in [native.txt](native.txt) and the full suite.

No Python interfaces changed. The JavaScript call sites and loader lifecycle were
reviewed before advancing only their two hashes in the external-contract source
snapshot. The prior snapshot is retained in [source-before.json](source-before.json).
Earlier audit and repair evidence remains historical.

Replay from the repository root using the existing application environment:

```powershell
New-Item -ItemType Directory -Force typing/.cache/browser-review | Out-Null
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest tests/test_browser_review.py -q --basetemp typing/.cache/browser-review/replay
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest -q --basetemp typing/.cache/browser-review/replay-full
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
```

JavaScript cases require Node. The native case additionally requires Chromium
(Chrome was used here); `RIPOSTE_TEST_BROWSER` can select its executable. Browser
profiles are isolated temporary directories and are removed after the check.
