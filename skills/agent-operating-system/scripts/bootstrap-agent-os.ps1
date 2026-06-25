param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$BaselineBranch = 'dev',
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
        $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        if ($content -match [regex]::Escape($line)) {
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

$existingAgentEntries = [System.Collections.Generic.List[string]]::new()
$configuredHooksPath = (& git config --get core.hooksPath 2>$null)
if ($LASTEXITCODE -ne 0) {
    $configuredHooksPath = ''
}
if (-not [string]::IsNullOrWhiteSpace($configuredHooksPath) -and $configuredHooksPath -ne '.githooks') {
    $existingAgentEntries.Add("core.hooksPath=$configuredHooksPath")
}
if (Test-Path -LiteralPath (Join-Path $repoRoot 'common/git-hooks') -PathType Container) {
    $existingAgentEntries.Add('common/git-hooks')
}
foreach ($path in @(
    'scripts/agent-verify.sh',
    'scripts/agent-verify.ps1',
    'scripts/agent-bootstrap.sh',
    'scripts/agent-bootstrap.ps1'
)) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $path) -PathType Leaf) {
        $existingAgentEntries.Add($path)
    }
}

$useBundledAgentEntryPoints = $existingAgentEntries.Count -eq 0
if (-not $useBundledAgentEntryPoints) {
    Info "Existing agent entrypoint(s) found: $($existingAgentEntries -join ', ')"
    Info 'Skipping bundled .githooks and default agent verify/bootstrap scripts.'
}

Ensure-Directory (Join-Path $repoRoot 'docs')
Ensure-Directory (Join-Path $repoRoot 'docs/agent')
Ensure-Directory (Join-Path $repoRoot 'scripts')
if ($useBundledAgentEntryPoints) {
    Ensure-Directory (Join-Path $repoRoot '.githooks')
}
Ensure-Directory (Join-Path $repoRoot '.oceans')
Ensure-Directory (Join-Path $repoRoot '.oceans/templates')

Copy-TemplateIfMissing 'AGENTS.template.md' (Join-Path $repoRoot 'AGENTS.md')
if ($RequireClaude) {
    Copy-TemplateIfMissing 'CLAUDE.template.md' (Join-Path $repoRoot 'CLAUDE.md')
}
Copy-TemplateIfMissing 'AGENTS.template.md' (Join-Path $repoRoot '.oceans/templates/AGENTS.template.md')
Copy-TemplateIfMissing 'CLAUDE.template.md' (Join-Path $repoRoot '.oceans/templates/CLAUDE.template.md')
Copy-TemplateIfMissing 'branch-workflow.template.md' (Join-Path $repoRoot 'docs/agent/branch-workflow.md')
Copy-TemplateIfMissing 'project-reference.template.md' (Join-Path $repoRoot 'docs/agent/project-reference.md')
Copy-FileIfMissing (Join-Path $scriptDir 'dedupe-agent-docs.sh') (Join-Path $repoRoot 'scripts/dedupe-agent-docs.sh')
Copy-TemplateIfMissing 'agent-standards.conf.template' (Join-Path $repoRoot '.oceans/agent-standards.conf')

if ($useBundledAgentEntryPoints) {
    Copy-TemplateIfMissing 'agent-bootstrap.template.ps1' (Join-Path $repoRoot 'scripts/agent-bootstrap.ps1')
    Copy-TemplateIfMissing 'agent-verify.template.ps1' (Join-Path $repoRoot 'scripts/agent-verify.ps1')
    Copy-TemplateIfMissing 'agent-verify.template.sh' (Join-Path $repoRoot 'scripts/agent-verify.sh')
    Copy-FileIfMissing (Join-Path $scriptDir 'agent-standards-hook.sh') (Join-Path $repoRoot 'scripts/agent-standards-hook.sh')
    Copy-TemplateIfMissing 'pre-commit.template' (Join-Path $repoRoot '.githooks/pre-commit')
    Copy-TemplateIfMissing 'commit-msg.template' (Join-Path $repoRoot '.githooks/commit-msg')
}

if ($useBundledAgentEntryPoints) {
    Append-LineIfMissing (Join-Path $repoRoot '.gitattributes') '.githooks/* text eol=lf'
}
Append-LineIfMissing (Join-Path $repoRoot '.gitattributes') 'scripts/*.sh text eol=lf'

if ($UseLocalWorktrees) {
    Append-LineIfMissing (Join-Path $repoRoot '.gitignore') "$WorktreeDir/"
    Ensure-Directory (Join-Path $repoRoot $WorktreeDir)
}

if ($IsLinux -or $IsMacOS) {
    foreach ($path in @(
        'scripts/dedupe-agent-docs.sh',
        'scripts/agent-verify.sh',
        'scripts/agent-standards-hook.sh',
        '.githooks/pre-commit',
        '.githooks/commit-msg'
    )) {
        $fullPath = Join-Path $repoRoot $path
        if (Test-Path -LiteralPath $fullPath) {
            & chmod +x $fullPath 2>$null
        }
    }
}

if ($EnableHooks) {
    if ($useBundledAgentEntryPoints) {
        & git config core.hooksPath .githooks
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to configure core.hooksPath'
        }
        Info 'Configured git core.hooksPath=.githooks'
    } elseif (-not [string]::IsNullOrWhiteSpace($configuredHooksPath)) {
        Info "Keeping existing git core.hooksPath=$configuredHooksPath"
    } elseif (Test-Path -LiteralPath (Join-Path $repoRoot 'common/git-hooks') -PathType Container) {
        & git config core.hooksPath common/git-hooks
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to configure core.hooksPath'
        }
        Info 'Configured git core.hooksPath=common/git-hooks'
    } else {
        Info 'Existing agent scripts detected; no hook path inferred. Configure hooks through the project workflow.'
    }
} else {
    if ($useBundledAgentEntryPoints) {
        Info 'Hooks scaffolded but not enabled. Run: git config core.hooksPath .githooks'
    } else {
        Info 'Bundled hooks were not scaffolded because the project already has agent entrypoints.'
    }
}

Info 'Bootstrap complete. Review existing files before migrating content.'
