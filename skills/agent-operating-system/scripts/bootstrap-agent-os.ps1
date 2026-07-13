param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$BaselineBranch = '',
    [string]$DevBranch = '',
    [string]$TaskPrefix = 'codex',
    [string]$WorktreeDir = '.worktrees',
    [switch]$EnableHooks,
    [switch]$UseLocalWorktrees,
    [switch]$RequireClaude
)

$ErrorActionPreference = 'Stop'

function Info($message) {
    Write-Host "[INFO] $message" -ForegroundColor Cyan
}

function Created($path) {
    Write-Host "[CREATE] $path" -ForegroundColor Green
}

function Exists($path) {
    Write-Host "[EXISTS] $path" -ForegroundColor Yellow
}

function Ensure-Directory($path) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Created $path
    } else {
        Exists $path
    }
}

function Expand-Template($content) {
    $requireClaudeValue = if ($RequireClaude) { '1' } else { '0' }
    return $content.
        Replace('{{BASE_BRANCH}}', $BaselineBranch).
        Replace('{{DEV_BRANCH}}', $DevBranch).
        Replace('{{TASK_PREFIX}}', $TaskPrefix).
        Replace('{{WORKTREE_DIR}}', $WorktreeDir).
        Replace('{{REQUIRE_CLAUDE_MD}}', $requireClaudeValue)
}

function Write-Utf8NoBom($path, $content) {
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($path, $content, $encoding)
}

function Copy-TemplateIfMissing($templateName, $targetPath) {
    $templatePath = Join-Path $assetsDir $templateName
    if (-not (Test-Path -LiteralPath $templatePath -PathType Leaf)) {
        throw "Template missing: $templatePath"
    }

    if (Test-Path -LiteralPath $targetPath) {
        Exists $targetPath
        return
    }

    $parent = Split-Path -Parent $targetPath
    if ($parent) {
        Ensure-Directory $parent
    }

    $content = Get-Content -LiteralPath $templatePath -Raw -Encoding UTF8
    $content = Expand-Template $content
    $normalizedTargetPath = $targetPath -replace '\\', '/'
    if ($normalizedTargetPath -match '/\.githooks/' -or $normalizedTargetPath -match '/scripts/[^/]+\.sh$') {
        $content = ($content -replace "`r`n", "`n") -replace "`r", "`n"
    }
    Write-Utf8NoBom $targetPath $content
    Created $targetPath
}

function Copy-FileIfMissing($sourcePath, $targetPath) {
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Source file missing: $sourcePath"
    }

    if (Test-Path -LiteralPath $targetPath) {
        Exists $targetPath
        return
    }

    $parent = Split-Path -Parent $targetPath
    if ($parent) {
        Ensure-Directory $parent
    }

    Copy-Item -LiteralPath $sourcePath -Destination $targetPath
    Created $targetPath
}

function Append-LineIfMissing($path, $line) {
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $lines = @(Get-Content -LiteralPath $path -Encoding UTF8)
        if ($lines -contains $line) {
            Exists "$path contains '$line'"
            return
        }
        Add-Content -LiteralPath $path -Value $line -Encoding UTF8
        Info "Appended '$line' to $path"
    } else {
        Write-Utf8NoBom $path "$line`n"
        Created $path
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillDir = Split-Path -Parent $scriptDir
$assetsDir = Join-Path $skillDir 'assets'

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "ProjectRoot not found: $ProjectRoot"
}

Set-Location $ProjectRoot
$repoRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    throw "ProjectRoot is not inside a git repository: $ProjectRoot"
}

Set-Location $repoRoot
Info "Bootstrapping agent OS in $repoRoot"

$currentBranchOutput = (& git branch --show-current 2>$null)
$currentBranch = if ($null -eq $currentBranchOutput) { '' } else { $currentBranchOutput.ToString().Trim() }
if ([string]::IsNullOrWhiteSpace($BaselineBranch)) {
    $originHead = (& git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>$null)
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($originHead)) {
        $BaselineBranch = $originHead.Trim() -replace '^origin/', ''
    } else {
        $BaselineBranch = $currentBranch
    }
}
if ([string]::IsNullOrWhiteSpace($DevBranch)) {
    $DevBranch = if ([string]::IsNullOrWhiteSpace($currentBranch)) { $BaselineBranch } else { $currentBranch }
}
if ([string]::IsNullOrWhiteSpace($BaselineBranch) -or [string]::IsNullOrWhiteSpace($DevBranch)) {
    throw 'Could not detect branch policy. Pass -BaselineBranch and -DevBranch explicitly.'
}
foreach ($branchValue in @($BaselineBranch, $DevBranch, "$TaskPrefix/bootstrap-check")) {
    & git check-ref-format --branch $branchValue 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Invalid branch policy value: $branchValue"
    }
}
if ($WorktreeDir.IndexOfAny([char[]](0..31)) -ge 0) {
    throw 'Worktree directory must not contain control characters.'
}
if ($UseLocalWorktrees) {
    if ([System.IO.Path]::IsPathRooted($WorktreeDir)) {
        throw '-UseLocalWorktrees requires a relative directory contained inside the repository.'
    }
    $candidateWorktree = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $WorktreeDir))
    $repoPrefix = [System.IO.Path]::GetFullPath($repoRoot)
    if (-not $repoPrefix.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $repoPrefix += [System.IO.Path]::DirectorySeparatorChar
    }
    if (-not $candidateWorktree.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw '-UseLocalWorktrees refuses a path outside the repository.'
    }
    if (Test-Path -LiteralPath $candidateWorktree) {
        $candidateWorktree = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $candidateWorktree).Path)
        if (-not $candidateWorktree.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw '-UseLocalWorktrees refuses a path that resolves outside the repository.'
        }
    }
}
Info "Branch defaults: baseline=$BaselineBranch integration=$DevBranch"

Ensure-Directory (Join-Path $repoRoot 'docs')
Ensure-Directory (Join-Path $repoRoot 'docs/agent')
Ensure-Directory (Join-Path $repoRoot 'scripts')
Ensure-Directory (Join-Path $repoRoot '.githooks')
Ensure-Directory (Join-Path $repoRoot '.oceans')
Ensure-Directory (Join-Path $repoRoot '.oceans/templates')

Copy-TemplateIfMissing 'AGENTS.template.md' (Join-Path $repoRoot 'AGENTS.md')
if ($RequireClaude) {
    Copy-TemplateIfMissing 'CLAUDE.template.md' (Join-Path $repoRoot 'CLAUDE.md')
}
Copy-TemplateIfMissing 'AGENTS.template.md' (Join-Path $repoRoot '.oceans/templates/AGENTS.template.md')
Copy-TemplateIfMissing 'CLAUDE.template.md' (Join-Path $repoRoot '.oceans/templates/CLAUDE.template.md')
Copy-TemplateIfMissing 'branch-workflow.template.md' (Join-Path $repoRoot 'docs/agent/branch-workflow.md')
Copy-TemplateIfMissing 'prompting-workflow.template.md' (Join-Path $repoRoot 'docs/agent/prompting-workflow.md')
Copy-TemplateIfMissing 'project-reference.template.md' (Join-Path $repoRoot 'docs/agent/project-reference.md')
Copy-TemplateIfMissing 'agent-bootstrap.template.ps1' (Join-Path $repoRoot 'scripts/agent-bootstrap.ps1')
Copy-TemplateIfMissing 'agent-bootstrap.template.sh' (Join-Path $repoRoot 'scripts/agent-bootstrap.sh')
Copy-TemplateIfMissing 'agent-verify.template.ps1' (Join-Path $repoRoot 'scripts/agent-verify.ps1')
Copy-TemplateIfMissing 'agent-verify.template.sh' (Join-Path $repoRoot 'scripts/agent-verify.sh')
Copy-FileIfMissing (Join-Path $scriptDir 'agent-standards-hook.sh') (Join-Path $repoRoot 'scripts/agent-standards-hook.sh')
Copy-FileIfMissing (Join-Path $scriptDir 'dedupe-agent-docs.sh') (Join-Path $repoRoot 'scripts/dedupe-agent-docs.sh')
Copy-TemplateIfMissing 'agent-standards.conf.template' (Join-Path $repoRoot '.oceans/agent-standards.conf')
Copy-TemplateIfMissing 'pre-commit.template' (Join-Path $repoRoot '.githooks/pre-commit')
Copy-TemplateIfMissing 'commit-msg.template' (Join-Path $repoRoot '.githooks/commit-msg')

Append-LineIfMissing (Join-Path $repoRoot '.gitattributes') '.githooks/* text eol=lf'
Append-LineIfMissing (Join-Path $repoRoot '.gitattributes') 'scripts/*.sh text eol=lf'

if ($UseLocalWorktrees) {
    Ensure-Directory (Join-Path $repoRoot $WorktreeDir)
    Append-LineIfMissing (Join-Path $repoRoot '.gitignore') "$WorktreeDir/"
}

if ($IsLinux -or $IsMacOS) {
    & chmod +x (Join-Path $repoRoot 'scripts/agent-bootstrap.sh') 2>$null
    & chmod +x (Join-Path $repoRoot 'scripts/agent-verify.sh') 2>$null
    & chmod +x (Join-Path $repoRoot 'scripts/agent-standards-hook.sh') 2>$null
    & chmod +x (Join-Path $repoRoot 'scripts/dedupe-agent-docs.sh') 2>$null
    & chmod +x (Join-Path $repoRoot '.githooks/pre-commit') 2>$null
    & chmod +x (Join-Path $repoRoot '.githooks/commit-msg') 2>$null
}

if ($EnableHooks) {
    & git config core.hooksPath .githooks
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to configure core.hooksPath'
    }
    Info 'Configured git core.hooksPath=.githooks'
} else {
    Info 'Hooks scaffolded but not enabled. Run: git config core.hooksPath .githooks'
}

Info 'Bootstrap complete. Review existing files before migrating content.'
