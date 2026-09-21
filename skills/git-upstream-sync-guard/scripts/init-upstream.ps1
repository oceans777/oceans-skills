param(
  [Parameter(Mandatory=$true)][string]$RepoPath,
  [Parameter(Mandatory=$true)][string]$UpstreamUrl,
  [string]$OriginUrl = "",
  [string]$DevBranch = "dev",
  [switch]$CreateRelease,
  [string]$ReleaseBranch = "release"
)

$ErrorActionPreference = "Stop"

function Run-Git([string[]]$Args) {
  & git @Args
  if ($LASTEXITCODE -ne 0) { throw "git command failed: git $($Args -join ' ')" }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "git is not installed or not available in PATH"
}

if (-not (Test-Path $RepoPath)) {
  if ([string]::IsNullOrWhiteSpace($OriginUrl)) {
    throw "RepoPath does not exist. Provide OriginUrl to clone the user's fork safely."
  }
  Run-Git @("clone", $OriginUrl, $RepoPath)
}

Push-Location $RepoPath
try {
  Run-Git @("rev-parse", "--is-inside-work-tree")

  $dirty = (& git status --porcelain)
  if ($LASTEXITCODE -ne 0) { throw "git status failed" }
  if ($dirty) { throw "Working tree is not clean. Commit or intentionally handle local changes first." }

  $remoteNames = @(& git remote)
  if ($OriginUrl) {
    if ($remoteNames -contains "origin") {
      Run-Git @("remote", "set-url", "origin", $OriginUrl)
    } else {
      Run-Git @("remote", "add", "origin", $OriginUrl)
    }
  }

  if ($remoteNames -contains "upstream") {
    Run-Git @("remote", "set-url", "upstream", $UpstreamUrl)
  } else {
    Run-Git @("remote", "add", "upstream", $UpstreamUrl)
  }

  Run-Git @("fetch", "upstream", "--prune", "--tags")
  Run-Git @("remote", "set-head", "upstream", "-a")

  $head = (& git symbolic-ref --short refs/remotes/upstream/HEAD).Trim()
  if ($LASTEXITCODE -ne 0 -or -not $head.StartsWith("upstream/")) {
    throw "Unable to determine upstream default branch."
  }
  $mirror = $head.Substring("upstream/".Length)

  & git show-ref --verify --quiet "refs/heads/$mirror"
  if ($LASTEXITCODE -eq 0) {
    Run-Git @("checkout", $mirror)
    & git merge-base --is-ancestor "$mirror" "upstream/$mirror"
    if ($LASTEXITCODE -ne 0) {
      throw "Local mirror branch contains divergence or commits not safely fast-forwardable to upstream."
    }
    Run-Git @("merge", "--ff-only", "upstream/$mirror")
  } else {
    Run-Git @("checkout", "-b", $mirror, "--track", "upstream/$mirror")
  }

  & git show-ref --verify --quiet "refs/heads/$DevBranch"
  if ($LASTEXITCODE -ne 0) {
    Run-Git @("checkout", "-b", $DevBranch, $mirror)
  } else {
    Run-Git @("checkout", $DevBranch)
  }

  if ($CreateRelease) {
    & git show-ref --verify --quiet "refs/heads/$ReleaseBranch"
    if ($LASTEXITCODE -ne 0) {
      Run-Git @("branch", $ReleaseBranch, $DevBranch)
    }
  }

  Write-Output "Initialized safely. upstream default branch: $mirror; dev branch: $DevBranch"
} finally {
  Pop-Location
}
