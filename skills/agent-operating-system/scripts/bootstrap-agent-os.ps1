param(
    [string]$ProjectRoot = (Get-Location).Path,
    [string]$BaselineBranch = 'dev',
    [string]$TaskPrefix = 'codex',
    [string]$WorktreeDir = '.worktrees',
    [switch]$EnableHooks,
    [switch]$UseLocalWorktrees
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
    return $content.
        Replace('{{BASE_BRANCH}}', $BaselineBranch).
        Replace('{{TASK_PREFIX}}', $TaskPrefix).
        Replace('{{WORKTREE_DIR}}', $WorktreeDir)
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
    if (($targetPath -replace '\\', '/') -match '/\.githooks/') {
        $content = ($content -replace "`r`n", "`n") -replace "`r", "`n"
    }
    Write-Utf8NoBom $targetPath $content
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

Ensure-Directory (Join-Path $repoRoot 'docs')
Ensure-Directory (Join-Path $repoRoot 'docs/agent')
Ensure-Directory (Join-Path $repoRoot 'scripts')
Ensure-Directory (Join-Path $repoRoot '.githooks')

Copy-TemplateIfMissing 'AGENTS.template.md' (Join-Path $repoRoot 'AGENTS.md')
Copy-TemplateIfMissing 'branch-workflow.template.md' (Join-Path $repoRoot 'docs/agent/branch-workflow.md')
Copy-TemplateIfMissing 'project-reference.template.md' (Join-Path $repoRoot 'docs/agent/project-reference.md')
Copy-TemplateIfMissing 'agent-verify.template.ps1' (Join-Path $repoRoot 'scripts/agent-verify.ps1')
Copy-TemplateIfMissing 'pre-commit.template' (Join-Path $repoRoot '.githooks/pre-commit')
Copy-TemplateIfMissing 'commit-msg.template' (Join-Path $repoRoot '.githooks/commit-msg')

Append-LineIfMissing (Join-Path $repoRoot '.gitattributes') '.githooks/* text eol=lf'

if ($UseLocalWorktrees) {
    Append-LineIfMissing (Join-Path $repoRoot '.gitignore') "$WorktreeDir/"
    Ensure-Directory (Join-Path $repoRoot $WorktreeDir)
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
