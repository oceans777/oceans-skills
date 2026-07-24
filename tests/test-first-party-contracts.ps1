$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Aos = Join-Path $RepoRoot 'skills\agent-operating-system'
$Config = Get-Content -LiteralPath (Join-Path $Aos 'assets\agent-standards.conf.template') -Raw -Encoding UTF8
$AosSkill = Get-Content -LiteralPath (Join-Path $Aos 'SKILL.md') -Raw -Encoding UTF8
$Triage = Get-Content -LiteralPath (Join-Path $RepoRoot 'skills\experience-triage\SKILL.md') -Raw -Encoding UTF8
if ($Config -notmatch '(?m)^schema_version=2\r?$') { throw 'Missing schema version.' }
if ($Config -notmatch '(?m)^generator_version=') { throw 'Missing generator version.' }
if ($AosSkill -notmatch 'invoke `experience-triage`') { throw 'Agent OS does not delegate durable-learning classification.' }
foreach ($term in @('observe','candidate','adopted','automated','retired','Classify two independent axes','hooks require deterministic pass/fail logic')) {
    if ($Triage -notmatch [regex]::Escape($term)) { throw "Missing triage contract term: $term" }
}
if ($Triage -match 'first matching layer') { throw 'Legacy first-match decision model remains.' }
$Cases = Get-Content -LiteralPath (Join-Path $RepoRoot 'skills\experience-triage\references\evaluation-cases.md') -Encoding UTF8
if (($Cases | Where-Object { $_ -match '^\| ' }).Count -lt 20) { throw 'Insufficient evaluation cases.' }
Write-Host 'First-party PowerShell contract tests passed.'
