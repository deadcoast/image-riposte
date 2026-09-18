param(
    [Parameter(Position = 0)][Alias("ArtworkFolder")][string]$ImageFolder,
    [switch]$Lab,
    [switch]$Browser,
    [switch]$NoAnimation,
    [switch]$Linear,
    [ValidateSet("goks", "dark", "light", "mono")][string]$Theme = "goks"
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Project = $PSScriptRoot
if ($Lab) { throw 'Dependency installation moved to INSTALL.ps1 -Lab. Then run START.ps1.' }
$Images = $null
if (-not [string]::IsNullOrWhiteSpace($ImageFolder)) {
    if (-not (Test-Path -LiteralPath $ImageFolder -PathType Container)) { throw 'The image folder must already exist.' }
    $Images = (Resolve-Path -LiteralPath $ImageFolder).Path.TrimEnd('\', '/')
    $ProjectFull = (Resolve-Path -LiteralPath $Project).Path.TrimEnd('\', '/')
    $Sep = [IO.Path]::DirectorySeparatorChar
    if ($Images.Equals($ProjectFull, [StringComparison]::OrdinalIgnoreCase) -or
        $Images.StartsWith($ProjectFull + $Sep, [StringComparison]::OrdinalIgnoreCase) -or
        $ProjectFull.StartsWith($Images + $Sep, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Keep the application and images in separate, non-overlapping folders.'
    }
}
if ($Browser -and -not $Images) { throw 'Browser mode requires -ImageFolder. Run START.ps1 without flags for the interactive menu.' }
$Python = Join-Path $Project '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'RIPOSTE is not installed. Run .\INSTALL.ps1, then .\START.ps1 to open the menu.'
}
$Expected = & $Python -c "import sys,tomllib; print(tomllib.load(open(sys.argv[1], 'rb'))['project']['version'])" (Join-Path $Project 'pyproject.toml')
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
$Installed = & $Python -c "import importlib.metadata as m, importlib.util as u, pathlib, sys; s=u.find_spec('riposte'); current=s is not None and s.origin is not None and pathlib.Path(s.origin).resolve()==(pathlib.Path(sys.argv[1])/'src/riposte/__init__.py').resolve(); print(next((d.version for d in m.distributions() if d.metadata['Name'] == 'riposte-studio'), 'absent') if current else 'absent')" $Project
if ($LASTEXITCODE -ne 0) { throw 'The virtual environment is not working; recreate .venv using README.md.' }
if ($Installed.Trim() -ne $Expected.Trim()) {
    throw 'Refresh this checkout with .\INSTALL.ps1, then run .\START.ps1. Launching does not install dependencies.'
}
$LaunchArgs = @('-m', 'riposte', '--theme', $Theme)
if ($NoAnimation) { $LaunchArgs += '--no-animation' }
if ($Linear) { $LaunchArgs += '--plain' }
if ($Browser) { $LaunchArgs += @('serve', $Images) }
else { $LaunchArgs += 'ui'; if ($Images) { $LaunchArgs += $Images } }
& $Python @LaunchArgs
exit $LASTEXITCODE
