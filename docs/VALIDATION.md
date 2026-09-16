# RIPOSTE 0.4 / internal development verification

These are developer checks performed as part of implementation, not a request for the user to test or qualify an unfinished application. Passing them does not establish adversarial effectiveness or independent visual preference.

## Executed

| Execution | Result |
|---|---|
| Source suite | 667 passed |
| Separately installed local wheel | 667 passed |
| Fresh final ZIP extraction | See the external final release report; execution follows packaging |
| Inherited tests | All 449 cases retained; 18 modules plus `conftest.py` byte-identical |
| New terminal/CLI cases | 218 cases across four added modules |
| Source/wheel/installed package bytes | 44 files equal |
| CLI inventory | 27 actual Typer command names, including one publish alias |
| Real POSIX terminal cases | 4 scenarios: normal exit, Ctrl+C, SIGTERM, live resize |
| Windows key adapter | 6 mocked-console key scenarios plus output-failure cleanup, not native Windows execution |
| Same-controller main product path | Real sanitation, source-replacement boundary, numerical candidate, review, exact-byte ZIP and model/viewer failures |
| Read-only real-terminal recording | 76 recorded output events, exit 0, 2.37 seconds; original synthetic artwork |
| Shell launcher | `bash -n` successful; native macOS/PowerShell not executed |

The final archive verification report is external to avoid a circular hash dependency. Its reported test result is only written after running the final extracted artifact. The source and installed-wheel reports are included under `evidence/`.

## What ran versus what was substituted

The actual Typer parser, Rich segment renderer, keyboard controller, POSIX alternate-screen terminal, line-input interface, Python worker lifecycle, image sanitation, operation locks, publication state, quality limits, CPU autograd, image codecs, output approval and ZIP assembly executed.

The protection workflow scenarios use an explicitly labeled synthetic differentiable model oracle; they are not pretrained model results. The local image-viewer test uses an explicit subprocess substitute so automated developer checks do not open an unrelated desktop application. Windows `msvcrt` key sequences are adapter checks, not proof of native Windows console behavior. Backend/API regression tests inherited from prior releases still run; unchanged web code was not newly credited with another browser-design milestone.

## Native terminal lifecycle

A real POSIX pseudo-terminal exercised Rich's alternate screen and the actual input reader, including search, arrow/menu actions, F2/F3, resizing to a noninteractive small window, returning to 79×24 and exit. The child process compared cooked-terminal settings before and after running the application. Captured output includes alternate-screen exit, bracketed-paste disable and cursor-show sequences. SIGTERM returns 143 after cleanup; a non-daemon owned worker is joined before return.

Python 3.13 emitted four `forkpty()` deprecation warnings because the test host process is multithreaded. These were warnings, not hidden passes or assertion failures. Native Windows/macOS launchers, assistive technologies and GPU backends were not run in this host.

## Safety and behavior checks

The new checks cover every command's generated help, menu-to-Typer argument equivalence, invalid input without private-value echo, date/size filters, read-only planning, publishing/source confirmation, both real review acknowledgements, exact-byte package contents, model failures without noise, changed-pixel rejection, explicit viewer handoff without implicit approval, worker cancellation and commit completion, malformed/fragmented escape sequences, bounded multiline paste, motion freezing, all three palettes and small-screen action suspension.

A broad scene matrix verifies pure ASCII cell dimensions and Rich rendering at 79×24, 100×34 and 132×46. Those mechanical checks complement direct inspection of the captures; they do not certify that any user will like the design.

## Continuity and evidence artifacts

`provenance.json` identifies the actual prior archive digest and every inherited package/test file. 27 of 29 old package files are byte-identical; only `cli.py` and the version module changed. Fifteen terminal package files were added. No original image-engine algorithm or browser asset was replaced for this wave.

`package-equality.json` compares all 44 package files across source, built wheel and separately installed wheel. The final manifest and external release report additionally bind the extracted release. Re-running checks in another environment may change warning counts or timings; no wall-clock performance guarantee is claimed.

The GIF and PNGs are captures of the actual ASCII cell renderer. The `.cast` is a separate recording of a running terminal, not a rendered mockup. All visible artwork consists of the shipped original synthetic geometric fixtures. No user artwork, font file, pretrained model weight or secret source metadata is in the archive.

## Scope

This release implements the requested terminal/application surfaces. It does not claim completion of every future image-security objective. It makes no new pretrained-model, AI-resistance, CUDA-performance, native-Windows or text-guided-video efficacy assertion. Development continues through product implementation; these limits are not a handoff asking the user to stop and evaluate a prototype.
