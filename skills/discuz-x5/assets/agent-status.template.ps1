param(
    [switch]$FailOnWhitespaceDrift,
    [switch]$FixWhitespaceDrift,
    [int]$MaxItems = 50
)

$ErrorActionPreference = 'Stop'
$failed = $false

function Fail($message) {
    Write-Host "[FAIL] $message" -ForegroundColor Red
    $script:failed = $true
}

function Pass($message) {
    Write-Host "[OK] $message" -ForegroundColor Green
}

function Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function GitLines($arguments) {
    $output = & git @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($output -join [Environment]::NewLine)
    }
    return @($output | Where-Object { $_ -ne $null -and $_ -ne '' })
}

function Normalize-GitPath($path) {
    return ($path -replace '\\', '/')
}

function Test-GitDiffWhitespaceOnly($path, $cached) {
    $normalized = Normalize-GitPath $path
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $arguments = @('-c', 'core.autocrlf=false', 'diff')
        if ($cached) {
            $arguments += '--cached'
        }
        $arguments += @('--quiet', '--ignore-space-at-eol', '--ignore-blank-lines', '--', $normalized)
        & git @arguments *> $null
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $previousPreference
    }
}

function Get-StatusPath($line) {
    if ($line.Length -lt 4) {
        return $null
    }

    $path = $line.Substring(3)
    if ($path -like '* -> *') {
        $path = ($path -split ' -> ', 2)[1]
    }

    return $path
}

function Get-WhitespaceOnlyStatusChanges() {
    $statusLines = GitLines @('status', '--porcelain=v1', '-uall')
    $changes = New-Object System.Collections.Generic.List[object]

    foreach ($line in $statusLines) {
        if ($line.Length -lt 4) {
            continue
        }

        $state = $line.Substring(0, 2)
        if ($state -eq '??' -or $state -eq '!!' -or $state -notmatch 'M') {
            continue
        }

        $path = Get-StatusPath $line
        if ([string]::IsNullOrWhiteSpace($path)) {
            continue
        }

        $hasStagedChange = ($state[0] -ne ' ' -and $state[0] -ne '?' -and $state[0] -ne '!')
        $hasWorktreeChange = ($state[1] -ne ' ' -and $state[1] -ne '?' -and $state[1] -ne '!')

        $stagedWhitespaceOnly = $false
        $worktreeWhitespaceOnly = $false

        if ($hasStagedChange) {
            $stagedWhitespaceOnly = Test-GitDiffWhitespaceOnly $path $true
        }

        if ($hasWorktreeChange) {
            $worktreeWhitespaceOnly = Test-GitDiffWhitespaceOnly $path $false
        }

        if (($hasStagedChange -and $stagedWhitespaceOnly) -or ($hasWorktreeChange -and $worktreeWhitespaceOnly)) {
            $changes.Add([pscustomobject]@{
                State = $state
                Path = $path
                StagedWhitespaceOnly = $stagedWhitespaceOnly
                WorktreeWhitespaceOnly = $worktreeWhitespaceOnly
            })
        }
    }

    return $changes
}

$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    throw 'Not inside a git repository.'
}

$repoRoot = $repoRoot.Trim()
Set-Location $repoRoot

Info "Repository: $repoRoot"

$statusLines = GitLines @('status', '--short', '-uall')
if ($statusLines.Count -eq 0) {
    Pass 'Working tree is clean'
} else {
    Info "Working tree items: $($statusLines.Count)"
    $statusLines | Select-Object -First $MaxItems | ForEach-Object {
        Write-Host "  $_"
    }
    if ($statusLines.Count -gt $MaxItems) {
        Info "Only showing first $MaxItems item(s)."
    }
}

$whitespaceOnlyChanges = @(Get-WhitespaceOnlyStatusChanges)
if ($whitespaceOnlyChanges.Count -eq 0) {
    Pass 'No whitespace-only drift'
} else {
    Info "Whitespace-only drift item(s): $($whitespaceOnlyChanges.Count)"
    $whitespaceOnlyChanges | Select-Object -First $MaxItems | ForEach-Object {
        Write-Host "  $($_.State) $($_.Path)"
    }

    if ($FixWhitespaceDrift) {
        foreach ($change in $whitespaceOnlyChanges) {
            if ($change.StagedWhitespaceOnly) {
                & git restore --staged -- $change.Path
                if ($LASTEXITCODE -ne 0) {
                    Fail "Failed to unstage whitespace-only drift: $($change.Path)"
                }
            }
            if ($change.WorktreeWhitespaceOnly) {
                & git restore --worktree -- $change.Path
                if ($LASTEXITCODE -ne 0) {
                    Fail "Failed to restore whitespace-only drift: $($change.Path)"
                }
            }
        }
        if (-not $failed) {
            Pass 'Whitespace-only drift restored'
        }
    } elseif ($FailOnWhitespaceDrift) {
        Fail 'Whitespace-only drift detected. Run scripts/agent-status.ps1 -FixWhitespaceDrift after reviewing the listed files.'
    }
}

if ($failed) {
    exit 1
}

Pass 'agent status completed'
exit 0
