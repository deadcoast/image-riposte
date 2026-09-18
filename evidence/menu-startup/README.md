# PAC-022: menu-first image workflows

This evidence covers the current checkout's interactive entry, location browser,
launch/setup separation, neutral image terminology, preserved workflow routing,
and distribution contents. It is not a model efficacy or end-user visual-quality
acceptance result. Synthetic inputs only were used.

## Reproduced defects and retained failed attempts

- `before.txt` / `before.xml`: **2 failed**. A rootless controller immediately
  opened a path editor, hiding the action menu even from the linear entry.
- `targeted-first.*`: **2 failed, 162 passed, 4 skipped**. Existing tests expected
  the old path-first behavior. They were updated to exercise browsing while
  retaining their original read-only/preview assertions.
- `package-before.json`: source distribution lacked INSTALL/START scripts,
  the local wrapper, and the lockfile. `MANIFEST.in` now includes them.
- `native-console-first.txt`: initial ConPTY harness inherited redirected runner
  handles. The application rejected non-TTY input. The harness now uses explicit
  null startup handles as described in Microsoft's terminal discussion 15814;
  production keyboard handling was not bypassed or replaced.
- `source-mypy.txt`: an incorrect audit flag was rejected. The corrected command
  and actual diagnostics are retained in `source-mypy-final.txt`.

## Current verification

- Full suite: `pytest.txt` / `pytest.xml` report **880 passed, 7 skipped, 1 failed**.
  The only failure was the native Chromium test timing out under the sandbox.
  `browser.txt` / `browser.xml` rerun all **21 browser checks successfully** outside
  the sandbox, including that native test. Across these runs, all **881 runnable
  tests passed**. The seven skips are Windows symlink privileges and POSIX PTYs.
- `native-console-powershell.json` and `native-console-cmd.json`: **PASS** through
  the real Windows ConPTY, `START.ps1` and `START.cmd`, using the existing editable
  environment. No linear mode or controller mocks: menu before a path, Enter,
  arrow keys, numeric shortcuts, multi-input selection, explained results folder,
  Escape/back, quit, cursor restoration, and unchanged synthetic inputs.
- `typing.txt`: external contracts **PASS**, 339 source/stub signatures, 40 leaf
  modules, strict declarations/tooling, runtime fixtures, and 13 expected negative
  diagnostics. The new browser API and affected controller/renderer declarations
  were reviewed; `typing/evidence/source-reviewed-menu.json` records that review.
- Separate raw implementation mypy audit remains **FAIL: 1043 errors in 37 files,
  43 source files checked**. Passing external contracts does not make source-body
  typing clean. This task does not close the existing strict-source typing work.
- `home-small.png`, `home-wide.png`, `browser-small.png`: inspected production
  cell renders at 72x24 and 100x34 with a simulated dark terminal background.
  The narrow browser retains visible Cancel and the end of long folder paths.
  These images are renderer captures; native keyboard proof is separate above.
- `lock.txt`: the existing lockfile remains coherent; no new runtime dependencies.
- `build-final.txt`, `install.txt`, `package.json`: fresh sdist/wheel and isolated
  no-dependency installation agree with all **49 application files**. All 30
  commands remain registered; Sort, RIPOSTE and combined previews run from the
  installed package; its no-command entry reaches the menu. The sdist contains
  byte-identical INSTALL/START scripts, wrapper and lockfile.
- Installer tests exercise real PowerShell/Bash script routing with an adapted
  uv subprocess. They prove setup argument selection and no implicit launch,
  not a fresh network/dependency installation on another machine.

The native terminal checks do not prove macOS/Linux raw-key behavior on this
Windows host. Processing/model tests use the existing test doubles and local
fixtures. No new pretrained model, CUDA, or protection-efficacy claim is made.
`RELEASE-MANIFEST.json` and archives in `packages/` describe historical releases;
the current build hashes are in `package.json`.

## Repeat the checks

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp .tmp/menu-full
.venv/Scripts/python.exe evidence/menu-startup/native_console.py
.venv/Scripts/python.exe evidence/menu-startup/native_console.py --entry cmd
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv lock --check --offline --cache-dir typing/.cache/uv
uv build --offline --cache-dir typing/.cache/uv
uv pip install --python .venv/Scripts/python.exe --offline --no-deps --cache-dir typing/.cache/uv --target typing/.cache/menu-installed dist/riposte_studio-0.5.0-py3-none-any.whl
.venv/Scripts/python.exe evidence/menu-startup/check_package.py
```
