param(
    [Parameter(Mandatory = $true)]
    [string]$TaskName,
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$BaselineBranch = 'dev',
    [string]$TaskPrefix = 'codex',
    [string]$WorktreeDir = '.worktrees',
    [string]$BranchName = '',
    [string]$VerificationCommand = '',
    [switch]$NoFetch,
    [switch]$EnsureIgnore
)

$ErrorActionPreference = 'Stop'

function Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Warn($message) {
    Write-Host "[WARN] $message" -ForegroundColor Yellow
}

function Ready($message) {
    Write-Host "[READY] $message" -ForegroundColor Green
}

function Run-Git($arguments) {
    & git @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($arguments -join ' ') failed"
    }
}

function Invoke-GitQuietExitCode($arguments) {
    $previousErrorAction = $ErrorActionPreference
    $script:ErrorActionPreference = 'Continue'
    & git @arguments 1>$null 2>$null
    $exitCode = $LASTEXITCODE
    $script:ErrorActionPreference = $previousErrorAction
    return $exitCode
}

function Invoke-GitQuiet($arguments) {
    return (Invoke-GitQuietExitCode $arguments) -eq 0
}

function Test-GitRef($ref) {
    return Invoke-GitQuiet @('rev-parse', '--verify', '--quiet', "$ref^{commit}")
}

function Test-LocalBranch($branch) {
    return Invoke-GitQuiet @('show-ref', '--verify', '--quiet', "refs/heads/$branch")
}

function Test-OriginRemote() {
    $remotes = & git remote
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    return $remotes -contains 'origin'
}

function Get-RemoteBranchState($branch) {
    $exitCode = Invoke-GitQuietExitCode @('ls-remote', '--exit-code', '--heads', 'origin', $branch)
    if ($exitCode -eq 0) {
        return 'exists'
    }
    if ($exitCode -eq 2) {
        return 'missing'
    }
    return 'unknown'
}

function Get-TaskSlug($name) {
    $slug = $name.ToLowerInvariant() -replace '[^a-z0-9]+', '-'
    $slug = $slug.Trim('-')
    if ([string]::IsNullOrWhiteSpace($slug)) {
        $slug = "task-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    }
    if ($slug.Length -gt 48) {
        $slug = $slug.Substring(0, 48).Trim('-')
    }
    return $slug
}

function Append-LineIfMissing($path, $line) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        if ($content -match [regex]::Escape($line)) {
            return
        }
        Add-Content -LiteralPath $path -Value $line -Encoding UTF8
    } else {
        Set-Content -LiteralPath $path -Value $line -Encoding UTF8
    }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "ProjectRoot not found: $ProjectRoot"
}

$repoRoot = (& git -C $ProjectRoot rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    throw "ProjectRoot is not inside a git repository: $ProjectRoot"
}

$repoRoot = $repoRoot.Trim()
Set-Location $repoRoot

$slug = Get-TaskSlug $TaskName
if ([string]::IsNullOrWhiteSpace($BranchName)) {
    $BranchName = "$TaskPrefix/$slug"
}

if (Test-LocalBranch $BranchName) {
    throw "Branch already exists: $BranchName"
}

$baselineRef = $BaselineBranch
$hasOrigin = Test-OriginRemote
if ($hasOrigin -and -not $NoFetch) {
    Info "Fetching origin/$BaselineBranch"
    & git fetch origin $BaselineBranch
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to fetch origin/$BaselineBranch. Refusing to create a task from a potentially stale baseline. Fix origin access or pass -NoFetch to intentionally use local refs."
    }

    $remoteBranchState = Get-RemoteBranchState $BranchName
    if ($remoteBranchState -eq 'exists') {
        throw "Remote branch already exists: origin/$BranchName"
    }
    if ($remoteBranchState -eq 'unknown') {
        throw "Could not check whether origin/$BranchName already exists."
    }
}

if ($hasOrigin -and -not $NoFetch) {
    $baselineRef = (& git rev-parse FETCH_HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($baselineRef)) {
        throw "Fetched origin/$BaselineBranch but could not resolve FETCH_HEAD."
    }
} elseif (Test-GitRef $BaselineBranch) {
    $baselineRef = $BaselineBranch
} elseif ($NoFetch -and (Test-GitRef "origin/$BaselineBranch")) {
    Warn "Using existing origin/$BaselineBranch because -NoFetch was set and local $BaselineBranch was not found."
    $baselineRef = "origin/$BaselineBranch"
} elseif (-not (Test-GitRef $BaselineBranch)) {
    throw "Baseline branch not found locally or at origin: $BaselineBranch"
}

if ([System.IO.Path]::IsPathRooted($WorktreeDir)) {
    $worktreeRoot = $WorktreeDir
} else {
    $worktreeRoot = Join-Path $repoRoot $WorktreeDir
}

if ($EnsureIgnore -and -not [System.IO.Path]::IsPathRooted($WorktreeDir)) {
    Append-LineIfMissing (Join-Path $repoRoot '.gitignore') "$WorktreeDir/"
}

if (-not (Test-Path -LiteralPath $worktreeRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $worktreeRoot -Force | Out-Null
}

$worktreePath = Join-Path $worktreeRoot $slug
if (Test-Path -LiteralPath $worktreePath) {
    throw "Worktree path already exists: $worktreePath"
}

Info "Creating branch $BranchName from $baselineRef"
Run-Git @('worktree', 'add', '-b', $BranchName, $worktreePath, $baselineRef)

Ready "Task worktree created"
Write-Host "Task: $TaskName"
Write-Host "Branch: $BranchName"
Write-Host "Baseline: $baselineRef"
Write-Host "Worktree: $worktreePath"

if (-not [string]::IsNullOrWhiteSpace($VerificationCommand)) {
    Write-Host "Verification: $VerificationCommand"
}

Write-Host ''
Write-Host 'Next steps:'
Write-Host "  Set-Location '$worktreePath'"
Write-Host '  implement only this task'
Write-Host '  stage only task-owned files'
Write-Host '  verify, commit, push, then merge by project policy'
