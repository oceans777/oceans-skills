$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$AosRoot = Join-Path $RepoRoot 'skills\agent-operating-system'
$TestRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("oceans-aos-test-" + [Guid]::NewGuid().ToString('N'))

function Run-Git([string[]]$Arguments) {
    & git @Arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed" }
}

try {
    $CallerLocation = (Get-Location).Path
    $Project = Join-Path $TestRoot 'project'
    Run-Git @('init', '-b', 'main', $Project)
    Run-Git @('-C', $Project, 'config', 'user.name', 'AOS Test')
    Run-Git @('-C', $Project, 'config', 'user.email', 'aos-test@example.invalid')
    Set-Content -LiteralPath (Join-Path $Project 'README.md') -Value '# test' -Encoding UTF8
    Run-Git @('-C', $Project, 'add', 'README.md')
    Run-Git @('-C', $Project, 'commit', '-m', 'test: initialize')

    & (Join-Path $AosRoot 'scripts\bootstrap-agent-os.ps1') -ProjectRoot $Project
    if ((Get-Location).Path -ne $CallerLocation) { throw 'Bootstrap changed the caller working directory.' }
    if (-not (Test-Path -LiteralPath (Join-Path $Project 'AGENTS.md'))) {
        throw 'Bootstrap did not create AGENTS.md.'
    }

    $failed = $false
    try {
        & (Join-Path $AosRoot 'scripts\start-agent-task.ps1') -ProjectRoot $Project `
          -TaskName invalid -BranchName 'bad..branch' -EnsureIgnore -NoFetch
    } catch { $failed = $true }
    if (-not $failed) { throw 'Expected invalid branch to fail.' }
    if (Test-Path -LiteralPath (Join-Path $Project '.gitignore')) {
        throw 'Failed task setup created .gitignore.'
    }

    $failed = $false
    try {
        & (Join-Path $AosRoot 'scripts\start-agent-task.ps1') -ProjectRoot $Project `
          -TaskName escaped -BranchName 'codex/escaped' -WorktreeDir '..\escaped' -EnsureIgnore -NoFetch
    } catch { $failed = $true }
    if (-not $failed) { throw 'Expected escaped ignore path to fail.' }

    & (Join-Path $AosRoot 'scripts\start-agent-task.ps1') -ProjectRoot $Project `
      -TaskName valid -BranchName 'codex/valid' -WorktreeDir '.worktrees' -EnsureIgnore -NoFetch
    if ((Get-Location).Path -ne $CallerLocation) { throw 'Task setup changed the caller working directory.' }
    if (-not (Test-Path -LiteralPath (Join-Path $Project '.worktrees\valid'))) {
        throw 'Expected worktree was not created.'
    }

    Write-Host 'Agent operating system PowerShell tests passed.'
} finally {
    if (Test-Path -LiteralPath $TestRoot) {
        Remove-Item -LiteralPath $TestRoot -Recurse -Force
    }
}
