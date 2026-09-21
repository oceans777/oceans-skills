#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${1:?usage: init-upstream.sh <repo-path> <upstream-url> [origin-url]}"
UPSTREAM_URL="${2:?usage: init-upstream.sh <repo-path> <upstream-url> [origin-url]}"
ORIGIN_URL="${3:-}"
DEV_BRANCH="${DEV_BRANCH:-dev}"

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }

if [[ ! -d "$REPO_PATH" ]]; then
  [[ -n "$ORIGIN_URL" ]] || { echo "repo path does not exist; provide origin URL" >&2; exit 1; }
  git clone "$ORIGIN_URL" "$REPO_PATH"
fi

cd "$REPO_PATH"
[[ -z "$(git status --porcelain)" ]] || { echo "working tree is not clean" >&2; exit 1; }

if git remote get-url upstream >/dev/null 2>&1; then
  git remote set-url upstream "$UPSTREAM_URL"
else
  git remote add upstream "$UPSTREAM_URL"
fi

if [[ -n "$ORIGIN_URL" ]]; then
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$ORIGIN_URL"
  else
    git remote add origin "$ORIGIN_URL"
  fi
fi

git fetch upstream --prune --tags
git remote set-head upstream -a
HEAD_REF="$(git symbolic-ref --short refs/remotes/upstream/HEAD)"
MIRROR="${HEAD_REF#upstream/}"

if git show-ref --verify --quiet "refs/heads/$MIRROR"; then
  git checkout "$MIRROR"
  git merge-base --is-ancestor "$MIRROR" "upstream/$MIRROR" || {
    echo "local mirror branch diverged; refusing destructive repair" >&2
    exit 2
  }
  git merge --ff-only "upstream/$MIRROR"
else
  git checkout -b "$MIRROR" --track "upstream/$MIRROR"
fi

if git show-ref --verify --quiet "refs/heads/$DEV_BRANCH"; then
  git checkout "$DEV_BRANCH"
else
  git checkout -b "$DEV_BRANCH" "$MIRROR"
fi

echo "initialized safely: mirror=$MIRROR dev=$DEV_BRANCH"
