param(
    [Parameter(Mandatory = $true)]
    [string]$TaskName,
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$BaselineBranch = '',
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
        $lines = @(Get-Content -LiteralPath $path -Encoding UTF8)
        if ($lines -contains $line) {
            return
        }
    }

    $parent = Split-Path -Parent $path
    $stagingPath = Join-Path $parent ('.gitignore.oceans-stage.' + [Guid]::NewGuid().ToString('N'))
    try {
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Copy-Item -LiteralPath $path -Destination $stagingPath
        } else {
            [System.IO.File]::WriteAllBytes($stagingPath, [byte[]]@())
        }
        $existingBytes = [System.IO.File]::ReadAllBytes($stagingPath)
        $prefix = if ($existingBytes.Length -gt 0 -and $existingBytes[$existingBytes.Length - 1] -ne 10) { [Environment]::NewLine } else { '' }
        $encoding = New-Object System.Text.UTF8Encoding($false)
        $appendBytes = $encoding.GetBytes($prefix + $line + [Environment]::NewLine)
        $stream = [System.IO.File]::Open($stagingPath, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try { $stream.Write($appendBytes, 0, $appendBytes.Length) } finally { $stream.Dispose() }
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            [System.IO.File]::Replace($stagingPath, $path, $null)
        } else {
            Move-Item -LiteralPath $stagingPath -Destination $path
        }
    } finally {
        if (Test-Path -LiteralPath $stagingPath) { Remove-Item -LiteralPath $stagingPath -Force }
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

if ([string]::IsNullOrWhiteSpace($BaselineBranch)) {
    $currentBranch = (& git branch --show-current 2>$null)
    if ($null -ne $currentBranch) {
        $BaselineBranch = $currentBranch.ToString().Trim()
    }
}
if ([string]::IsNullOrWhiteSpace($BaselineBranch)) {
    throw 'Could not detect a task source branch. Pass -BaselineBranch.'
}
& git check-ref-format --branch $BaselineBranch 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Invalid baseline branch: $BaselineBranch"
}

$slug = Get-TaskSlug $TaskName
if ([string]::IsNullOrWhiteSpace($BranchName)) {
    $BranchName = "$TaskPrefix/$slug"
}

& git check-ref-format --branch $BranchName 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Invalid branch name: $BranchName"
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

$worktreeRootExisted = Test-Path -LiteralPath $worktreeRoot -PathType Container
if (-not (Test-Path -LiteralPath $worktreeRoot -PathType Container)) {
    New-Item -ItemType Directory -Path $worktreeRoot -Force | Out-Null
}
$worktreeRoot = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $worktreeRoot).Path)
$repoPrefix = [System.IO.Path]::GetFullPath($repoRoot)
if (-not $repoPrefix.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
    $repoPrefix += [System.IO.Path]::DirectorySeparatorChar
}
$worktreeInsideRepo = $worktreeRoot.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)

$gitIgnorePath = Join-Path $repoRoot '.gitignore'
if ($EnsureIgnore) {
    if ([System.IO.Path]::IsPathRooted($WorktreeDir) -or -not $worktreeInsideRepo) {
        if (-not $worktreeRootExisted) { Remove-Item -LiteralPath $worktreeRoot -ErrorAction SilentlyContinue }
        throw '-EnsureIgnore only supports a worktree directory contained inside the repository.'
    }
    if (Test-Path -LiteralPath $gitIgnorePath) {
        $gitIgnoreItem = Get-Item -LiteralPath $gitIgnorePath -Force
        if ($gitIgnoreItem.PSIsContainer -or
            ($gitIgnoreItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            if (-not $worktreeRootExisted) { Remove-Item -LiteralPath $worktreeRoot -ErrorAction SilentlyContinue }
            throw 'Refusing to modify a reparse point or non-file .gitignore.'
        }
    }
}

$worktreePath = Join-Path $worktreeRoot $slug
if (Test-Path -LiteralPath $worktreePath) {
    throw "Worktree path already exists: $worktreePath"
}

Info "Creating branch $BranchName from $baselineRef"
try {
    Run-Git @('worktree', 'add', '-b', $BranchName, $worktreePath, $baselineRef)
} catch {
    if (-not $worktreeRootExisted) { Remove-Item -LiteralPath $worktreeRoot -ErrorAction SilentlyContinue }
    throw 'Failed to create task worktree; no ignore rule was changed.'
}

if ($EnsureIgnore) {
    $relativeCanonical = $worktreeRoot.Substring($repoPrefix.Length).Replace('\', '/')
    $ignoreLine = "$($relativeCanonical.TrimEnd('/'))/"
    try {
        Append-LineIfMissing $gitIgnorePath $ignoreLine
    } catch {
        & git worktree remove --force $worktreePath 1>$null 2>$null
        & git branch -D $BranchName 1>$null 2>$null
        if (-not $worktreeRootExisted) { Remove-Item -LiteralPath $worktreeRoot -ErrorAction SilentlyContinue }
        throw 'Failed to update .gitignore; task worktree and branch were rolled back.'
    }
}

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
Write-Host '  verify, commit, and share only as authorized'
