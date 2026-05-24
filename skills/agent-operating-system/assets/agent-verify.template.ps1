param(
    [switch]$AllowBaselineBranch,
    [switch]$AllowRiskyFiles,
    [string]$CommitMessageFile,
    [string]$BaselineBranch = '{{BASE_BRANCH}}',
    [string]$TaskPrefix = '{{TASK_PREFIX}}'
)

$ErrorActionPreference = 'Continue'
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

$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    throw 'Not inside a git repository.'
}
Set-Location $repoRoot

$gitDir = (& git rev-parse --git-dir).Trim()
$isMergeInProgress = Test-Path -LiteralPath (Join-Path $gitDir 'MERGE_HEAD')

Info "Repository: $repoRoot"

$branch = (& git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    Fail 'Detached HEAD is not allowed for normal agent work.'
} elseif ($branch -eq $BaselineBranch -and -not ($AllowBaselineBranch -or $isMergeInProgress)) {
    Fail "Work is on $BaselineBranch. Use a $TaskPrefix/<task-name> branch or pass -AllowBaselineBranch for an intentional merge."
} elseif ($branch -ne $BaselineBranch -and $branch -notlike "$TaskPrefix/*") {
    Fail "Unexpected branch '$branch'. Expected $TaskPrefix/<task-name> or $BaselineBranch."
} else {
    Pass "Branch policy: $branch"
}

$stagedFiles = GitLines @('diff', '--cached', '--name-only', '--diff-filter=ACMRD')
if ($stagedFiles.Count -eq 0) {
    Info 'No staged files found. Running format checks against working tree diff.'
} else {
    Pass "Staged files: $($stagedFiles.Count)"
}

$diffCheckArgs = if ($stagedFiles.Count -gt 0) { @('diff', '--check', '--cached') } else { @('diff', '--check') }
$diffCheck = & git @diffCheckArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail "git diff --check failed:`n$($diffCheck -join [Environment]::NewLine)"
} else {
    Pass 'git diff --check'
}

$riskyPatterns = @(
    '(^|/)\.env($|[./])',
    '\.(pem|key|p12|pfx)$',
    '\.(zip|7z|rar)$',
    '(^|/)data/cache/',
    '(^|/)data/template/',
    '(^|/)data/attachment/',
    '\.log$'
)

if ($stagedFiles.Count -gt 0 -and -not $AllowRiskyFiles) {
    $risky = @()
    foreach ($file in $stagedFiles) {
        $normalized = $file -replace '\\', '/'
        foreach ($pattern in $riskyPatterns) {
            if ($normalized -match $pattern) {
                $risky += $file
                break
            }
        }
    }
    if ($risky.Count -gt 0) {
        Fail "Risky staged files require explicit review:`n$($risky -join [Environment]::NewLine)"
    } else {
        Pass 'No risky staged files'
    }
}

$phpFiles = @()
if ($stagedFiles.Count -gt 0) {
    $phpFiles = $stagedFiles | Where-Object {
        $_ -match '\.php$' -and (Test-Path -LiteralPath $_ -PathType Leaf)
    }
}

if ($phpFiles.Count -gt 0) {
    $php = Get-Command php -ErrorAction SilentlyContinue
    if (-not $php) {
        Fail 'php command not found; cannot run php -l on staged PHP files.'
    } else {
        foreach ($file in $phpFiles) {
            $lint = & php -l $file 2>&1
            if ($LASTEXITCODE -ne 0) {
                Fail "php -l failed for ${file}:`n$($lint -join [Environment]::NewLine)"
            }
        }
        if (-not $failed) {
            Pass "php -l checked $($phpFiles.Count) file(s)"
        }
    }
} else {
    Info 'No staged PHP files to lint.'
}

if ($CommitMessageFile) {
    if (-not (Test-Path -LiteralPath $CommitMessageFile -PathType Leaf)) {
        Fail "Commit message file not found: $CommitMessageFile"
    } else {
        $firstLine = (Get-Content -LiteralPath $CommitMessageFile -Encoding UTF8 | Select-Object -First 1)
        if ($firstLine -notmatch '^(feat|fix|docs|style|refactor|perf|test|chore): .+') {
            Fail "Commit message must use '<type>: <title>'. Found: $firstLine"
        } else {
            Pass 'Commit message format'
        }
    }
}

if ($failed) {
    exit 1
}

Pass 'agent verification passed'
