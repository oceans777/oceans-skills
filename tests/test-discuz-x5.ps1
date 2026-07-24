$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SkillRoot = Join-Path $RepoRoot 'skills\discuz-x5'
$Verifier = Join-Path $SkillRoot 'assets\agent-verify.template.ps1'
$Content = Get-Content -LiteralPath $Verifier -Raw -Encoding UTF8
if ($Content -match 'phpstudy|Discuz_X5\.0_|codex/') { throw 'Verifier contains project-specific policy.' }
if ($Content -notmatch 'finally\s*\{\s*Set-Location') { throw 'Verifier must restore caller location.' }
if ($Content -notmatch 'git status --porcelain') { throw 'Verifier must inspect unstaged changes when nothing is staged.' }
if (-not (Test-Path (Join-Path $SkillRoot 'assets\discuz-x5.conf.template'))) { throw 'Missing config template.' }
Write-Host 'Discuz X5 PowerShell contract tests passed.'
