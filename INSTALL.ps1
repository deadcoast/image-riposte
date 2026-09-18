param([switch]$Lab)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Project = $PSScriptRoot
Write-Host "RIPOSTE / Install application dependencies"
Write-Host "This sets up the application environment. No image folder is needed."
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $InstallArgs = @('sync', '--frozen', '--inexact', '--project', $Project)
    if ($Lab) { $InstallArgs += @('--extra', 'lab') }
    & uv @InstallArgs
} else {
    $Python = Join-Path $Project '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv (Join-Path $Project '.venv')
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv (Join-Path $Project '.venv')
        } else { throw 'Install Python 3.11 or newer first. See README.md.' }
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
    }
    $Target = $Project
    if ($Lab) { $Target += '[lab]' }
    & $Python -m pip install --editable $Target
}
if ($LASTEXITCODE -ne 0) { throw 'Installation failed. Read the error above before launching.' }
Write-Host 'Installed. Run .\START.ps1 or double-click START.cmd to open the menu.'
Write-Host 'Model weights are selected separately and are not downloaded by this installer.'
if (Get-Command ffprobe -ErrorAction SilentlyContinue) {
    Write-Host 'Video sorting: ffprobe is available.'
} else {
    Write-Host 'Video sorting is optional and needs FFmpeg ffprobe on PATH. Image sorting and protection are available without it.'
}
