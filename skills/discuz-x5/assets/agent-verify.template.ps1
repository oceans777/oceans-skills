param(
    [switch]$AllowDevBranch,
    [switch]$AllowRiskyFiles,
    [switch]$AllowWhitespaceOnlyChanges,
    [switch]$SkipHooksPathCheck,
    [string]$CommitMessageFile
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

function Test-WhitespaceOnlyChange($path, $state) {
    $hasStagedChange = ($state[0] -ne ' ' -and $state[0] -ne '?' -and $state[0] -ne '!')
    $hasWorktreeChange = ($state[1] -ne ' ' -and $state[1] -ne '?' -and $state[1] -ne '!')

    if (-not $hasStagedChange -and -not $hasWorktreeChange) {
        return $false
    }

    $stagedWhitespaceOnly = $false
    $worktreeWhitespaceOnly = $false

    if ($hasStagedChange) {
        $stagedWhitespaceOnly = Test-GitDiffWhitespaceOnly $path $true
    }

    if ($hasWorktreeChange) {
        $worktreeWhitespaceOnly = Test-GitDiffWhitespaceOnly $path $false
    }

    return (($hasStagedChange -and $stagedWhitespaceOnly) -or ($hasWorktreeChange -and $worktreeWhitespaceOnly))
}

function Get-WhitespaceOnlyStatusChanges() {
    $statusLines = GitLines @('status', '--porcelain=v1', '-uall')
    $changes = New-Object System.Collections.Generic.List[string]

    foreach ($line in $statusLines) {
        if ($line.Length -lt 4) {
            continue
        }

        $state = $line.Substring(0, 2)
        if ($state -eq '??' -or $state -eq '!!' -or $state -notmatch 'M') {
            continue
        }

        $path = $line.Substring(3)
        if ($path -like '* -> *') {
            $path = ($path -split ' -> ', 2)[1]
        }

        if (Test-WhitespaceOnlyChange $path $state) {
            $changes.Add("$state $path")
        }
    }

    return $changes
}

function Find-PhpCommand() {
    $php = Get-Command php -ErrorAction SilentlyContinue
    if ($php) {
        return $php.Source
    }

    $candidateRoots = @(
        'D:/phpstudy_pro/Extensions/php',
        'C:/phpstudy_pro/Extensions/php'
    )

    foreach ($root in $candidateRoots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) {
            continue
        }

        $candidate = Get-ChildItem -LiteralPath $root -Recurse -Filter php.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1

        if ($candidate) {
            return $candidate.FullName
        }
    }

    return $null
}

function Find-NodeCommand() {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if ($node) {
        return $node.Source
    }

    return $null
}

function Test-HooksPathConfigured($repoRoot) {
    $hooksPath = (& git config --get core.hooksPath 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($hooksPath)) {
        return $false
    }

    $configured = ($hooksPath.Trim() -replace '\\', '/').TrimEnd('/')
    if ($configured -eq '.githooks' -or $configured -eq './.githooks') {
        return $true
    }

    $expected = ((Join-Path $repoRoot '.githooks') -replace '\\', '/').TrimEnd('/')
    return ($configured -eq $expected)
}

$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    throw 'Not inside a git repository.'
}
Set-Location $repoRoot
$gitDir = (& git rev-parse --git-dir).Trim()
$isMergeInProgress = Test-Path -LiteralPath (Join-Path $gitDir 'MERGE_HEAD')

Info "Repository: $repoRoot"

if (-not $SkipHooksPathCheck) {
    if (Test-HooksPathConfigured $repoRoot) {
        Pass 'Git hooks path: .githooks'
    } else {
        Fail 'Git hooks are not enabled for this checkout. Run scripts/agent-bootstrap.ps1 so pre-commit and commit-msg gates protect this workspace.'
    }
}

$branch = (& git branch --show-current).Trim()
if ([string]::IsNullOrWhiteSpace($branch)) {
    Fail 'Detached HEAD is not allowed for normal agent work.'
} elseif ($branch -eq 'dev' -and -not ($AllowDevBranch -or $isMergeInProgress)) {
    Fail 'Work is on dev. Create a codex/<task-name> branch or pass -AllowDevBranch for an intentional dev merge.'
} elseif ($branch -notmatch '^(codex/|dev$)') {
    Fail "Unexpected branch '$branch'. Expected codex/<task-name> for tasks or dev for intentional merges."
} else {
    Pass "Branch policy: $branch"
}

$stagedEntries = GitLines @('diff', '--cached', '--name-status', '--diff-filter=ACMRD')
$stagedFiles = @()
$stagedStatusByFile = @{}
foreach ($entry in $stagedEntries) {
    $parts = $entry -split "`t"
    if ($parts.Count -lt 2) {
        continue
    }
    $status = $parts[0]
    $file = $parts[$parts.Count - 1]
    $stagedFiles += $file
    $stagedStatusByFile[$file] = $status
}
if ($stagedFiles.Count -eq 0) {
    Info 'No staged files found. Running format checks against working tree diff.'
} else {
    Pass "Staged files: $($stagedFiles.Count)"
}

$diffCheckArgs = if ($stagedFiles.Count -gt 0) {
    @('diff', '--check', '--cached')
} else {
    @('diff', '--check')
}
$diffCheck = & git @diffCheckArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Fail "git diff --check failed:`n$($diffCheck -join [Environment]::NewLine)"
} else {
    Pass 'git diff --check'
}

if (-not $AllowWhitespaceOnlyChanges) {
    $whitespaceOnlyChanges = Get-WhitespaceOnlyStatusChanges
    if ($whitespaceOnlyChanges.Count -gt 0) {
        Fail "Whitespace-only drift is not allowed. Restore it with scripts/agent-status.ps1 -FixWhitespaceDrift or rerun verification with -AllowWhitespaceOnlyChanges after explicit review:`n$($whitespaceOnlyChanges -join [Environment]::NewLine)"
    } else {
        Pass 'No whitespace-only drift'
    }
}

$generatedRuntimePatterns = @(
    'Discuz_X5\.0_20260501/upload/data/cache/',
    'Discuz_X5\.0_20260501/upload/data/template/',
    'Discuz_X5\.0_20260501/upload/data/attachment/',
    '(^|/)data/(install|update|sendmail)\.lock$',
    'Discuz_X5\.0_20260501/upload/data/sysdata/cache_'
)

$riskyPatterns = @(
    '(^|/)\.env($|[./])',
    '\.(pem|key|p12|pfx)$',
    '\.(zip|7z|rar)$',
    $generatedRuntimePatterns,
    '\.log$'
)

if ($stagedFiles.Count -gt 0 -and -not $AllowRiskyFiles) {
    $risky = @()
    foreach ($file in $stagedFiles) {
        $normalized = $file -replace '\\', '/'
        $status = $stagedStatusByFile[$file]
        $isGeneratedRuntime = $false
        foreach ($pattern in $generatedRuntimePatterns) {
            if ($normalized -match $pattern) {
                $isGeneratedRuntime = $true
                break
            }
        }
        if ($status -eq 'D' -and $isGeneratedRuntime) {
            continue
        }
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
    $php = Find-PhpCommand
    if (-not $php) {
        Fail 'php command not found in PATH or phpstudy; cannot run php -l on staged PHP files.'
    } else {
        foreach ($file in $phpFiles) {
            $lint = & $php -l $file 2>&1
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

$jsFiles = @()
if ($stagedFiles.Count -gt 0) {
    $jsFiles = $stagedFiles | Where-Object {
        $status = $stagedStatusByFile[$_]
        $_ -match '\.js$' -and $status -notmatch '^D' -and (Test-Path -LiteralPath $_ -PathType Leaf)
    }
}

if ($jsFiles.Count -gt 0) {
    $node = Find-NodeCommand
    if (-not $node) {
        Fail 'node command not found in PATH; cannot run node --check on staged JavaScript files.'
    } else {
        foreach ($file in $jsFiles) {
            $lint = & $node --check $file 2>&1
            if ($LASTEXITCODE -ne 0) {
                Fail "node --check failed for ${file}:`n$($lint -join [Environment]::NewLine)"
            }
        }
        if (-not $failed) {
            Pass "node --check checked $($jsFiles.Count) file(s)"
        }
    }
} else {
    Info 'No staged JavaScript files to check.'
}

$jsBehaviorTestFiles = @()
if ($jsFiles.Count -gt 0) {
    $jsBehaviorTestFileMap = @{}
    foreach ($file in $jsFiles) {
        $normalized = $file -replace '\\', '/'
        if ($normalized -match '(^|/)tests/[^/]+_js_behavior_test\.js$') {
            $jsBehaviorTestFileMap[$normalized] = $true
        }
        if ($normalized -match '^(Discuz_X5\.0_20260501/upload/source/plugin/[^/]+)/') {
            $pluginTestDir = Join-Path $Matches[1] 'tests'
            if (Test-Path -LiteralPath $pluginTestDir -PathType Container) {
                $pluginTests = Get-ChildItem -LiteralPath $pluginTestDir -Filter '*_js_behavior_test.js' -File -ErrorAction SilentlyContinue
                foreach ($testFile in $pluginTests) {
                    $relativeTestPath = Resolve-Path -LiteralPath $testFile.FullName -Relative
                    $normalizedTestPath = ($relativeTestPath -replace '^\.\\', '') -replace '\\', '/'
                    $jsBehaviorTestFileMap[$normalizedTestPath] = $true
                }
            }
        }
    }
    $jsBehaviorTestFiles = @($jsBehaviorTestFileMap.Keys | Sort-Object)
}

if ($jsBehaviorTestFiles.Count -gt 0) {
    if (-not $node) {
        Fail 'node command not found in PATH; cannot run staged JavaScript behavior test files.'
    } else {
        foreach ($file in $jsBehaviorTestFiles) {
            $testOutput = & $node $file 2>&1
            if ($LASTEXITCODE -ne 0) {
                Fail "JavaScript behavior test failed for ${file}:`n$($testOutput -join [Environment]::NewLine)"
            }
        }
        if (-not $failed) {
            Pass "JavaScript behavior tests executed $($jsBehaviorTestFiles.Count) relevant test file(s)"
        }
    }
}

$phpTestFiles = @()
if ($phpFiles.Count -gt 0) {
    $phpTestFiles = $phpFiles | Where-Object {
        ($_ -replace '\\', '/') -match '/tests/[^/]+_test\.php$'
    }
}

if ($phpTestFiles.Count -gt 0) {
    if (-not $php) {
        Fail 'php command not found in PATH or phpstudy; cannot run staged PHP test files.'
    } else {
        foreach ($file in $phpTestFiles) {
            $testOutput = & $php $file 2>&1
            if ($LASTEXITCODE -ne 0) {
                Fail "PHP test failed for ${file}:`n$($testOutput -join [Environment]::NewLine)"
            }
        }
        if (-not $failed) {
            Pass "PHP tests executed $($phpTestFiles.Count) staged test file(s)"
        }
    }
}

if ($CommitMessageFile) {
    if (-not (Test-Path -LiteralPath $CommitMessageFile -PathType Leaf)) {
        Fail "Commit message file not found: $CommitMessageFile"
    } else {
        $firstLine = (Get-Content -LiteralPath $CommitMessageFile -Encoding UTF8 | Select-Object -First 1)
        if ($firstLine -notmatch '^(feat|fix|docs|style|refactor|perf|test|chore)(\([A-Za-z0-9._-]+\))?: .+') {
            Fail "Commit message must use '<type>: <title>' or '<type>(scope): <title>' Chinese title format. Found: $firstLine"
        } else {
            Pass 'Commit message format'
        }
    }
}

if ($failed) {
    exit 1
}

Pass 'agent verification passed'
exit 0
