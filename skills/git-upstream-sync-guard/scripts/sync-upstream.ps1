param(
  [Parameter(Mandatory=$true)][string]$RepoPath,
  [string]$DevBranch = "dev",
  [switch]$PushMirror
)

$ErrorActionPreference = "Stop"

function Run-Git([string[]]$Args) {
  & git @Args
  if ($LASTEXITCODE -ne 0) { throw "git command failed: git $($Args -join ' ')" }
}

Push-Location $RepoPath
try {
  $dirty = (& git status --porcelain)
  if ($LASTEXITCODE -ne 0) { throw "git status failed" }
  if ($dirty) { throw "Working tree is not clean. Stop before upstream sync." }

  $remotes = @(& git remote)
  if (-not ($remotes -contains "upstream")) { throw "Missing upstream remote." }

  Run-Git @("fetch", "upstream", "--prune", "--tags")
  Run-Git @("remote", "set-head", "upstream", "-a")

  $head = (& git symbolic-ref --short refs/remotes/upstream/HEAD).Trim()
  if ($LASTEXITCODE -ne 0 -or -not $head.StartsWith("upstream/")) { throw "Unable to determine upstream default branch." }
  $mirror = $head.Substring("upstream/".Length)

  Run-Git @("checkout", $mirror)
  Run-Git @("merge", "--ff-only", "upstream/$mirror")

  if ($PushMirror -and ($remotes -contains "origin")) {
    Run-Git @("push", "origin", $mirror)
  }

  & git show-ref --verify --quiet "refs/heads/$DevBranch"
  if ($LASTEXITCODE -ne 0) { throw "Missing dev branch '$DevBranch'." }

  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $backup = "backup/$DevBranch-before-upstream-$stamp"
  Run-Git @("branch", $backup, $DevBranch)

  Run-Git @("checkout", $DevBranch)
  & git merge $mirror
  if ($LASTEXITCODE -ne 0) {
    Write-Output "Merge into $DevBranch has conflicts. Backup branch: $backup"
    exit 2
  }

  Write-Output "Upstream merged into $DevBranch. Backup branch: $backup. Run project tests before release."
} finally {
  Pop-Location
}
