# PAC-021 installation integration

OBSERVED: the original PowerShell and Bash source launchers compared only package
versions. A copied installation at the same `0.5.0` version skipped refresh and
could run code predating the three workflows. Both cases were reproduced before
repair (`before.txt`: 2 failed, 2 passed).

The launchers now check the imported package's source location as well as its
version and refresh stale copied installs in editable mode. Current checkout
installs are reused. Dependency declarations, lockfile, console entry point,
existing command wrapper, model configuration and application source are unchanged
by this repair. No artwork migration is required.

Verification:

- `after.txt`: 32 passed: both launchers with current/stale installs and all
  28 independent workflow regressions. Launcher tests execute real PowerShell
  and Git Bash, with real Python source/version probes; installation and UI
  subprocess calls are recorded adapters, not live dependency installations.
- `build.txt`: fresh sdist and wheel built offline using the existing uv cache.
- `install.txt`: that wheel installed without dependencies into a separate
  directory under `typing/.cache`, using the existing Python environment.
- `package.json`: all 48 application files match byte-for-byte between checkout,
  sdist, wheel and isolated installation, including `intake.py`, terminal modules,
  model configuration and browser assets. All 30 commands are registered.
- All three installed workflow previews ran without modifying fixture artwork.
- Actual Windows `START.ps1` opened and exited the linear menu, exposing the
  three workflows; actual `riposte.cmd --help` exposed their command names.
  No installation was needed in this already-editable local environment.
- `lock.txt`: current lockfile is consistent (`uv lock --check --offline`).

The actual Windows launcher transcript is `windows-launcher.txt`. The reusable
package/launcher smoke script is `check_package.py`. Fresh archives are under
`dist/`; historical release archives remain unchanged. These checks do not
establish native raw-keyboard acceptance, GPU/model operation or protection
efficacy. Current runtime inspection finds all optional model dependencies
installed, with CPU available and CUDA/MPS unavailable. The existing full-suite
and type boundaries remain recorded under `../workflows/README.md`.
