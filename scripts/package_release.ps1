# One-command Windows packager wrapper.
# Usage:
#   .\scripts\package_release.ps1 --bump patch --notes "Beta for testers"
#   .\scripts\package_release.ps1 0.2.0 --notes "..." --skip-github
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PackageArgs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python (Join-Path $Root "scripts\package_release.py") @PackageArgs
exit $LASTEXITCODE
