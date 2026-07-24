param(
    [string]$ConfigFile = '.discuz-x5-skill.conf',
    [switch]$AllowRiskyFiles
)

$ErrorActionPreference = 'Stop'
$originalLocation = (Get-Location).Path
$failed = $false

function Info([string]$Message) { Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Pass([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }
function Fail([string]$Message) { Write-Host "[FAIL] $Message" -ForegroundColor Red; $script:failed = $true }

function Read-Config([string]$Path) {
    $values = @{}
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $values }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^\s*(#|$)') { continue }
        $parts = $line -split '=', 2
        if ($parts.Count -eq 2) { $values[$parts[0].Trim()] = $parts[1].Trim() }
    }
    return $values
}

function Config-Value($Values, [string]$Key, [string]$Default) {
    if ($Values.ContainsKey($Key) -and -not [string]::IsNullOrWhiteSpace($Values[$Key])) { return $Values[$Key] }
    return $Default
}

function Command-Path([string]$Command) {
    $found = Get-Command $Command -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    if (Test-Path -LiteralPath $Command -PathType Leaf) { return (Resolve-Path -LiteralPath $Command).Path }
    return $null
}

function Normalize-Path([string]$Path) {
    $normalized = $Path -replace '\\', '/'
    while ($normalized.StartsWith('./')) { $normalized = $normalized.Substring(2) }
    if ($normalized -eq '.') { return '' }
    return $normalized
}

function Join-RepoPath([string]$Base, [string]$Child) {
    if ([string]::IsNullOrWhiteSpace($Base)) { return (Normalize-Path $Child) }
    return (Normalize-Path (Join-Path $Base $Child))
}

function Path-UnderList([string]$Path, [string]$DiscuzRoot, [string]$Csv) {
    foreach ($item in ($Csv -split ',')) {
        $root = (Normalize-Path $item.Trim()).TrimEnd('/')
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $prefixed = (Join-RepoPath $DiscuzRoot $root).TrimEnd('/')
        if ($Path -eq $root -or $Path.StartsWith("$root/") -or $Path -eq $prefixed -or $Path.StartsWith("$prefixed/")) { return $true }
    }
    return $false
}

function Add-RelatedTests([System.Collections.Generic.HashSet[string]]$Tests, [string]$Path, [string]$DiscuzRoot, [string]$PluginRoots) {
    foreach ($item in ($PluginRoots -split ',')) {
        $root = (Normalize-Path $item.Trim()).TrimEnd('/')
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        $prefix = (Join-RepoPath $DiscuzRoot $root).TrimEnd('/') + '/'
        if (-not $Path.StartsWith($prefix)) { continue }
        $rest = $Path.Substring($prefix.Length)
        $plugin = ($rest -split '/', 2)[0]
        $testDir = Join-Path $prefix "$plugin/tests"
        if (Test-Path -LiteralPath $testDir -PathType Container) {
            Get-ChildItem -LiteralPath $testDir -File -ErrorAction SilentlyContinue | Where-Object {
                $_.Name -like '*_test.php' -or $_.Name -like '*_js_behavior_test.js'
            } | ForEach-Object { [void]$Tests.Add((Normalize-Path $_.FullName.Substring((Get-Location).Path.Length + 1))) }
        }
    }
}

try {
    $repoRoot = (& git rev-parse --show-toplevel 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) { throw 'Not inside a git repository.' }
    Set-Location $repoRoot

    $config = Read-Config $ConfigFile
    $schemaVersion = Config-Value $config 'schema_version' '1'
    if ($schemaVersion -ne '1') { throw "Unsupported schema_version: $schemaVersion" }
    $discuzRoot = Normalize-Path (Config-Value $config 'discuz_root' '.')
    if ([System.IO.Path]::IsPathRooted($discuzRoot) -or $discuzRoot -match '(^|/)\.\.(/|$)') { throw 'discuz_root must be repository-relative and contained in the repository.' }
    $pluginRoots = Config-Value $config 'plugin_roots' 'source/plugin'
    $generatedRoots = Config-Value $config 'generated_roots' 'data/cache,data/template,data/attachment'
    $phpCommand = Config-Value $config 'php_command' 'php'
    $nodeCommand = Config-Value $config 'node_command' 'node'
    $runRelatedTests = Config-Value $config 'run_related_tests' '1'
    Info "Discuz root: $discuzRoot"

    $staged = @(& git diff --cached --name-status --diff-filter=ACMRD)
    $entries = New-Object System.Collections.Generic.List[object]
    if ($staged.Count -gt 0) {
        foreach ($line in $staged) {
            $parts = $line -split "`t"
            if ($parts.Count -ge 2) { $entries.Add([pscustomobject]@{ Status = $parts[0]; Path = $parts[-1] }) }
        }
        & git diff --check --cached
    } else {
        foreach ($line in @(& git status --porcelain=v1 -uall)) {
            if ($line.Length -lt 4) { continue }
            $path = $line.Substring(3)
            if ($path -like '* -> *') { $path = ($path -split ' -> ', 2)[1] }
            $entries.Add([pscustomobject]@{ Status = $line.Substring(0, 2).Trim(); Path = $path })
        }
        & git diff --check
    }
    if ($LASTEXITCODE -ne 0) { Fail 'git diff --check failed.' } else { Pass 'git diff --check' }

    $php = Command-Path $phpCommand
    $node = Command-Path $nodeCommand
    $tests = New-Object 'System.Collections.Generic.HashSet[string]'

    foreach ($entry in $entries) {
        $path = Normalize-Path $entry.Path
        $status = $entry.Status.Trim()
        if ((Path-UnderList $path $discuzRoot $generatedRoots) -and $status -ne 'D') {
            Fail "Generated runtime path must not be maintained as source: $path"
        }
        if (-not $AllowRiskyFiles -and $path -match '(^|/)\.env($|\.)|\.(pem|key|p12|pfx|zip|7z|rar|log)$') {
            Fail "Risky file requires explicit review: $path"
        }
        if ($status -eq 'D' -or -not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
        if ($path -match '\.php$') {
            if (-not $php) { Fail "PHP command not found: $phpCommand" }
            else { & $php -l $path *> $null; if ($LASTEXITCODE -ne 0) { Fail "PHP syntax failed: $path" } }
            Add-RelatedTests $tests $path $discuzRoot $pluginRoots
        } elseif ($path -match '\.js$') {
            if (-not $node) { Fail "Node command not found: $nodeCommand" }
            else { & $node --check $path *> $null; if ($LASTEXITCODE -ne 0) { Fail "JavaScript syntax failed: $path" } }
            Add-RelatedTests $tests $path $discuzRoot $pluginRoots
        }
    }

    if ($runRelatedTests -eq '1') {
        foreach ($testFile in ($tests | Sort-Object)) {
            if ($testFile -match '\.php$') {
                if (-not $php) { Fail "PHP command not found for related test: $testFile"; continue }
                & $php $testFile
            } else {
                if (-not $node) { Fail "Node command not found for related test: $testFile"; continue }
                & $node $testFile
            }
            if ($LASTEXITCODE -ne 0) { Fail "Related behavior test failed: $testFile" }
        }
    }

    if ($failed) { exit 1 }
    Pass 'Discuz X5 verification passed'
} finally {
    Set-Location $originalLocation
}
