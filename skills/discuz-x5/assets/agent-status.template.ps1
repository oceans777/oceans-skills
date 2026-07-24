param(
    [string]$ConfigFile = '.discuz-x5-skill.conf'
)

$ErrorActionPreference = 'Stop'
$originalLocation = (Get-Location).Path
try {
    $repoRoot = (& git rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
        throw 'Not inside a git repository.'
    }
    Set-Location $repoRoot
    Write-Host "Repository: $repoRoot"
    Write-Host "Branch: $((& git branch --show-current).Trim())"
    Write-Host "Config: $ConfigFile"
    if (Test-Path -LiteralPath $ConfigFile -PathType Leaf) {
        Get-Content -LiteralPath $ConfigFile -Encoding UTF8 | Where-Object { $_ -notmatch '^\s*(#|$)' }
    } else {
        Write-Host 'Config file missing; verifier defaults will be used.'
    }
    & git status --short
} finally {
    Set-Location $originalLocation
}
