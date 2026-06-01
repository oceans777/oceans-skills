#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
SOURCE_HOOK_SCRIPT=$SCRIPT_DIR/agent-standards-hook.sh
SOURCE_ASSETS_DIR=$(CDPATH= cd "$SCRIPT_DIR/../assets" && pwd)
CONFIG_HOME=${XDG_CONFIG_HOME:-$HOME/.config}
HOOK_ROOT=$CONFIG_HOME/oceans777/agent-hooks
INSTALL_ROOT=$HOOK_ROOT/lib
INSTALL_SCRIPT_DIR=$INSTALL_ROOT/scripts
INSTALL_ASSETS_DIR=$INSTALL_ROOT/assets
HOOK_SCRIPT=$INSTALL_SCRIPT_DIR/agent-standards-hook.sh
FORCE=0
CHAIN_EXISTING=0

usage() {
  cat <<EOF
Usage: install-global-hooks.sh [--force] [--chain-existing]

Installs global Git hooks that run the oceans777 agent standards guard for
every local repository. Existing global core.hooksPath is not overwritten unless
--force or --chain-existing is provided.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --force)
      FORCE=1
      shift
      ;;
    --chain-existing)
      CHAIN_EXISTING=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v git >/dev/null 2>&1; then
  echo 'git is required but was not found in PATH.' >&2
  exit 1
fi

if [ ! -f "$SOURCE_HOOK_SCRIPT" ]; then
  echo "Hook source not found: $SOURCE_HOOK_SCRIPT" >&2
  exit 1
fi

existing_hooks_path=$(git config --global --get core.hooksPath || true)

resolve_hooks_path() {
  path=$1
  case "$path" in
    \~)
      printf '%s\n' "$HOME"
      ;;
    \~/*)
      printf '%s/%s\n' "$HOME" "${path#\~/}"
      ;;
    *)
      printf '%s\n' "$path"
      ;;
  esac
}

existing_hooks_path_resolved=
if [ -n "$existing_hooks_path" ]; then
  existing_hooks_path_resolved=$(resolve_hooks_path "$existing_hooks_path")
fi

if [ -n "$existing_hooks_path_resolved" ] && [ "$existing_hooks_path_resolved" != "$HOOK_ROOT" ]; then
  if [ "$FORCE" -ne 1 ] && [ "$CHAIN_EXISTING" -ne 1 ]; then
    cat >&2 <<EOF
Global core.hooksPath already exists:
  $existing_hooks_path

Refusing to overwrite it.

Use --chain-existing to run oceans777 checks first and then call the existing
hooks when present, or --force to replace the global hooks path.
EOF
    exit 1
  fi
fi

mkdir -p "$HOOK_ROOT" "$INSTALL_SCRIPT_DIR" "$INSTALL_ASSETS_DIR"
cp "$SOURCE_HOOK_SCRIPT" "$HOOK_SCRIPT"
chmod +x "$HOOK_SCRIPT"
cp "$SCRIPT_DIR/dedupe-agent-docs.sh" "$INSTALL_SCRIPT_DIR/dedupe-agent-docs.sh"
chmod +x "$INSTALL_SCRIPT_DIR/dedupe-agent-docs.sh"

for asset in AGENTS.template.md CLAUDE.template.md; do
  if [ ! -f "$SOURCE_ASSETS_DIR/$asset" ]; then
    echo "Required asset not found: $SOURCE_ASSETS_DIR/$asset" >&2
    exit 1
  fi
  cp "$SOURCE_ASSETS_DIR/$asset" "$INSTALL_ASSETS_DIR/$asset"
done

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

write_hook() {
  hook_name=$1
  existing_hook=
  if [ "$CHAIN_EXISTING" -eq 1 ] && [ -n "$existing_hooks_path_resolved" ] && [ "$existing_hooks_path_resolved" != "$HOOK_ROOT" ]; then
    existing_hook=$existing_hooks_path_resolved/$hook_name
  fi

  hook_path=$HOOK_ROOT/$hook_name
  {
    echo '#!/bin/sh'
    echo 'set -eu'
    printf 'HOOK_SCRIPT=%s\n' "$(shell_quote "$HOOK_SCRIPT")"
    printf 'EXISTING_HOOK=%s\n' "$(shell_quote "$existing_hook")"
    printf 'sh "$HOOK_SCRIPT" %s "$@"\n' "$hook_name"
    echo 'if [ -n "$EXISTING_HOOK" ] && [ -x "$EXISTING_HOOK" ]; then'
    echo '  exec "$EXISTING_HOOK" "$@"'
    echo 'fi'
  } > "$hook_path"
  chmod +x "$hook_path"
}

write_hook pre-commit
write_hook commit-msg
write_hook pre-push

git config --global core.hooksPath "$HOOK_ROOT"

cat <<EOF
Installed oceans777 global Git hooks:
  $HOOK_ROOT

Installed self-contained guard library:
  $INSTALL_ROOT

Configured:
  git config --global core.hooksPath "$HOOK_ROOT"

The first standards-guarded commit in each repository may create or open
AGENTS.md / CLAUDE.md and block once for review.
EOF
