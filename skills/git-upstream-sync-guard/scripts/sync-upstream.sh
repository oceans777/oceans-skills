#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${1:?usage: sync-upstream.sh <repo-path>}"
DEV_BRANCH="${DEV_BRANCH:-dev}"
PUSH_MIRROR="${PUSH_MIRROR:-0}"

cd "$REPO_PATH"
[[ -z "$(git status --porcelain)" ]] || { echo "working tree is not clean" >&2; exit 1; }

git remote get-url upstream >/dev/null 2>&1 || { echo "missing upstream remote" >&2; exit 1; }
git fetch upstream --prune --tags
git remote set-head upstream -a
HEAD_REF="$(git symbolic-ref --short refs/remotes/upstream/HEAD)"
MIRROR="${HEAD_REF#upstream/}"

git checkout "$MIRROR"
git merge --ff-only "upstream/$MIRROR"

if [[ "$PUSH_MIRROR" == "1" ]] && git remote get-url origin >/dev/null 2>&1; then
  git push origin "$MIRROR"
fi

git show-ref --verify --quiet "refs/heads/$DEV_BRANCH" || { echo "missing dev branch $DEV_BRANCH" >&2; exit 1; }
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="backup/${DEV_BRANCH}-before-upstream-${STAMP}"
git branch "$BACKUP" "$DEV_BRANCH"
git checkout "$DEV_BRANCH"
if ! git merge "$MIRROR"; then
  echo "merge conflicts detected; backup branch: $BACKUP" >&2
  exit 2
fi

echo "upstream merged into $DEV_BRANCH; backup=$BACKUP; run project tests before release"
