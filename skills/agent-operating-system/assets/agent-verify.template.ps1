param(
    [switch]$AllowBaselineBranch,
    [switch]$AllowDevBranch,
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

function Get-AgentConfigValue($path, $key, $defaultValue) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return $defaultValue
    }

    $lines = Get-Content -LiteralPath $path -Encoding UTF8
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '' -or $trimmed.StartsWith('#') -or $trimmed -notmatch '=') {
            continue
        }

        $parts = $trimmed -split '=', 2
        if ($parts[0].Trim() -eq $key) {
            return $parts[1].Trim()
        }
    }

    return $defaultValue
}

function Test-Enabled($value) {
    return ($value -in @('1', 'true', 'yes', 'on'))
}

function Test-TrackedOrStaged($path) {
    & git ls-files --error-unmatch $path *> $null
    if ($LASTEXITCODE -eq 0) {
        return $true
    }

    $staged = GitLines @('diff', '--cached', '--name-only', '--', $path)
    return ($staged.Count -gt 0)
}

function Test-AgentDoc($path, $required) {
    if (-not (Test-Enabled $required)) {
        return
    }

    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $path) -PathType Leaf)) {
        Fail "$path is missing. Run agent-operating-system bootstrap, or install the agent standards hook."
    } elseif (-not (Test-TrackedOrStaged $path)) {
        Fail "$path exists but is not tracked or staged."
    } else {
        Pass "$path exists"
    }
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

$configFile = Join-Path $repoRoot '.oceans/agent-standards.conf'
$BaselineBranch = Get-AgentConfigValue $configFile 'baseline_branch' $BaselineBranch
$TaskPrefix = Get-AgentConfigValue $configFile 'task_prefix' $TaskPrefix
$requireAgents = Get-AgentConfigValue $configFile 'require_agents_md' '1'
$requireClaude = Get-AgentConfigValue $configFile 'require_claude_md' '0'
$commitMessagePolicy = Get-AgentConfigValue $configFile 'commit_message' 'conventional'

$gitDir = (& git rev-parse --git-dir).Trim()
$isMergeInProgress = Test-Path -LiteralPath (Join-Path $gitDir 'MERGE_HEAD')

Info "Repository: $repoRoot"

$branch = (& git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    Fail 'Detached HEAD is not allowed for normal agent work.'
} elseif ($branch -eq $BaselineBranch -and -not ($AllowBaselineBranch -or $AllowDevBranch -or $isMergeInProgress)) {
    Fail "Work is on $BaselineBranch. Use a $TaskPrefix/<task-name> branch or pass -AllowDevBranch for an intentional merge."
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

Test-AgentDoc 'AGENTS.md' $requireAgents
Test-AgentDoc 'CLAUDE.md' $requireClaude

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

if ($CommitMessageFile -and $commitMessagePolicy -notin @('off', 'none')) {
    if (-not (Test-Path -LiteralPath $CommitMessageFile -PathType Leaf)) {
        Fail "Commit message file not found: $CommitMessageFile"
    } else {
        $firstLine = (Get-Content -LiteralPath $CommitMessageFile -Encoding UTF8 | Select-Object -First 1)
        if ($firstLine -notmatch '^(feat|fix|docs|style|refactor|perf|test|chore)(\([A-Za-z0-9._-]+\))?: .+') {
            Fail "Commit message must use '<type>: <title>' or '<type>(scope): <title>'. Found: $firstLine"
        } else {
            Pass 'Commit message format'
        }
    }
}

if ($failed) {
    exit 1
}

Pass 'agent verification passed'
