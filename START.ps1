param(
    [Parameter(Position = 0)][string]$ArtworkFolder,
    [switch]$Lab,
    [switch]$Browser,
    [switch]$NoAnimation,
    [switch]$Linear,
    [ValidateSet("goks", "dark", "light", "mono")][string]$Theme = "goks"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Project = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ArtworkFolder)) {
    $ArtworkFolder = Read-Host 'Existing artwork folder (separate from RIPOSTE and model folders)'
}
if (-not (Test-Path -LiteralPath $ArtworkFolder -PathType Container)) {
    throw 'The artwork folder must already exist. No artwork files have been changed.'
}
$Artwork = (Resolve-Path -LiteralPath $ArtworkFolder).Path.TrimEnd('\', '/')
$ProjectFull = (Resolve-Path -LiteralPath $Project).Path.TrimEnd('\', '/')
$Sep = [IO.Path]::DirectorySeparatorChar
if ($Artwork.Equals($ProjectFull, [StringComparison]::OrdinalIgnoreCase) -or
    $Artwork.StartsWith($ProjectFull + $Sep, [StringComparison]::OrdinalIgnoreCase) -or
    $ProjectFull.StartsWith($Artwork + $Sep, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Keep the application and artwork in separate, non-overlapping folders.'
}
$Python = Join-Path $Project '.venv\Scripts\python.exe'
$Created = $false
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    Write-Host "`n RIPOSTE / INSTALLING LOCAL ENVIRONMENT`n"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv (Join-Path $Project '.venv')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv (Join-Path $Project '.venv')
    } else {
        throw 'Install Python 3.13 first, or use the manual Python 3.11+ instructions in README.md.'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed. See the manual instructions.' }
    $Created = $true
}
$Expected = & $Python -c "import sys,tomllib; print(tomllib.load(open(sys.argv[1], 'rb'))['project']['version'])" (Join-Path $Project 'pyproject.toml')
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
$Installed = & $Python -c "import importlib.metadata as m, importlib.util as u, pathlib, sys; s=u.find_spec('riposte'); current=s is not None and s.origin is not None and pathlib.Path(s.origin).resolve()==(pathlib.Path(sys.argv[1])/'src/riposte/__init__.py').resolve(); print(next((d.version for d in m.distributions() if d.metadata['Name'] == 'riposte-studio'), 'absent') if current else 'absent')" $Project
if ($LASTEXITCODE -ne 0) { throw 'The virtual environment is not working; recreate .venv using README.md.' }
if ($Created -or $Lab -or $Installed.Trim() -ne $Expected.Trim()) {
    $Target = $Project
    if ($Lab) { $Target = $Project + '[lab]' }
    # Editable installation keeps code-only checkout updates visible even when
    # the version is unchanged. Old copied installs are refreshed by the check above.
    & $Python -m pip install --editable $Target
    if ($LASTEXITCODE -ne 0) { throw 'Package installation failed. Artwork has not been modified.' }
}
$LaunchArgs = @('-m', 'riposte', '--theme', $Theme)
if ($NoAnimation) { $LaunchArgs += '--no-animation' }
if ($Linear) { $LaunchArgs += '--plain' }
if ($Browser) { $LaunchArgs += @('serve', $Artwork) }
else { $LaunchArgs += @('ui', $Artwork) }
& $Python @LaunchArgs
exit $LASTEXITCODE
