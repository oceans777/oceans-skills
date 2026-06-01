param(
    [switch]$SkipVerify
)

$ErrorActionPreference = 'Stop'

function Pass($message) {
    Write-Host "[OK] $message" -ForegroundColor Green
}

function Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Fail($message) {
    throw $message
}

$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    Fail 'Not inside a git repository.'
}

$repoRoot = $repoRoot.Trim()
Set-Location $repoRoot

$hooksDir = Join-Path $repoRoot '.githooks'
$preCommitHook = Join-Path $hooksDir 'pre-commit'
$commitMsgHook = Join-Path $hooksDir 'commit-msg'
$agentVerify = Join-Path $repoRoot 'scripts/agent-verify.ps1'
$agentStandardsHook = Join-Path $repoRoot 'scripts/agent-standards-hook.sh'
$dedupeAgentDocs = Join-Path $repoRoot 'scripts/dedupe-agent-docs.sh'

if (-not (Test-Path -LiteralPath $hooksDir -PathType Container)) {
    Fail "Hooks directory not found: $hooksDir"
}

if (-not (Test-Path -LiteralPath $preCommitHook -PathType Leaf)) {
    Fail "pre-commit hook not found: $preCommitHook"
}

if (-not (Test-Path -LiteralPath $commitMsgHook -PathType Leaf)) {
    Fail "commit-msg hook not found: $commitMsgHook"
}

if (-not (Test-Path -LiteralPath $agentVerify -PathType Leaf)) {
    Fail "Agent verify script not found: $agentVerify"
}

if (-not (Test-Path -LiteralPath $agentStandardsHook -PathType Leaf)) {
    Fail "Agent standards hook script not found: $agentStandardsHook"
}

if (-not (Test-Path -LiteralPath $dedupeAgentDocs -PathType Leaf)) {
    Fail "Agent docs dedupe script not found: $dedupeAgentDocs"
}

Info "Repository: $repoRoot"

& git config core.hooksPath .githooks
if ($LASTEXITCODE -ne 0) {
    Fail 'Failed to configure core.hooksPath.'
}

$hooksPath = (& git config --get core.hooksPath).Trim()
if ($hooksPath -ne '.githooks') {
    Fail "Unexpected core.hooksPath after bootstrap: $hooksPath"
}

Pass 'Git hooks path configured: .githooks'

if (-not $SkipVerify) {
    & $agentVerify -AllowDevBranch
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Pass 'Agent bootstrap completed'
exit 0
