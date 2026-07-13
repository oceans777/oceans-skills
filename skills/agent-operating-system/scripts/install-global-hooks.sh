#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
SOURCE_HOOK_SCRIPT=$SCRIPT_DIR/agent-standards-hook.sh
CONFIG_HOME=${XDG_CONFIG_HOME:-$HOME/.config}
HOOK_ROOT=$CONFIG_HOME/oceans777/agent-hooks
INSTALL_ROOT=$HOOK_ROOT/lib
INSTALL_SCRIPT_DIR=$INSTALL_ROOT/scripts
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
if [ ! -f "$SCRIPT_DIR/dedupe-agent-docs.sh" ]; then
  echo "Dedupe helper not found: $SCRIPT_DIR/dedupe-agent-docs.sh" >&2
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

HOOK_PARENT=$(dirname "$HOOK_ROOT")
mkdir -p "$HOOK_PARENT"
LOCK_ROOT=$HOOK_PARENT/.agent-hooks.oceans-lock
if ! mkdir "$LOCK_ROOT" 2>/dev/null; then
  if [ -L "$LOCK_ROOT" ] || [ ! -d "$LOCK_ROOT" ]; then
    echo "Refusing unsafe installer lock: $LOCK_ROOT" >&2
    exit 1
  fi
  lock_pid=$(sed -n '1p' "$LOCK_ROOT/pid" 2>/dev/null || true)
  case "$lock_pid" in
    ''|*[!0-9]*) lock_active=1 ;;
    *) if kill -0 "$lock_pid" 2>/dev/null; then lock_active=1; else lock_active=0; fi ;;
  esac
  if [ "$lock_active" -eq 1 ]; then
    echo 'Another global hook installation is active.' >&2
    exit 1
  fi
  rm -rf "$LOCK_ROOT"
  mkdir "$LOCK_ROOT"
fi
if ! printf '%s\n' "$$" > "$LOCK_ROOT/pid"; then
  rm -rf "$LOCK_ROOT"
  exit 1
fi

BACKUP_ROOT=$HOOK_PARENT/.agent-hooks.oceans-backup
STAGING_ROOT=
HOOK_ACTIVATED=0
INSTALL_COMMITTED=0

cleanup_install() {
  if [ "$INSTALL_COMMITTED" -ne 1 ] && [ "$HOOK_ACTIVATED" -eq 1 ]; then
    rm -rf "$HOOK_ROOT"
    if [ -e "$BACKUP_ROOT" ] && [ ! -L "$BACKUP_ROOT" ]; then
      mv "$BACKUP_ROOT" "$HOOK_ROOT" || true
    fi
  fi
  if [ -n "${STAGING_ROOT:-}" ] && [ -d "$STAGING_ROOT" ]; then
    rm -rf "$STAGING_ROOT"
  fi
  if [ -d "$LOCK_ROOT" ] && [ ! -L "$LOCK_ROOT" ]; then
    rm -rf "$LOCK_ROOT"
  fi
  return 0
}
trap 'cleanup_install' EXIT
trap 'cleanup_install; exit 129' HUP
trap 'cleanup_install; exit 130' INT
trap 'cleanup_install; exit 143' TERM

if [ -e "$BACKUP_ROOT" ]; then
  if [ -L "$BACKUP_ROOT" ]; then
    echo "Refusing unsafe installer backup: $BACKUP_ROOT" >&2
    exit 1
  fi
  if [ -e "$HOOK_ROOT" ]; then
    rm -rf "$BACKUP_ROOT"
  else
    mv "$BACKUP_ROOT" "$HOOK_ROOT"
  fi
fi

STAGING_ROOT=$(mktemp -d "$HOOK_PARENT/.agent-hooks.oceans-stage.XXXXXX") || exit 1

STAGING_INSTALL_SCRIPT_DIR=$STAGING_ROOT/lib/scripts
STAGING_HOOK_SCRIPT=$STAGING_INSTALL_SCRIPT_DIR/agent-standards-hook.sh
mkdir -p "$STAGING_INSTALL_SCRIPT_DIR"
cp "$SOURCE_HOOK_SCRIPT" "$STAGING_HOOK_SCRIPT"
chmod +x "$STAGING_HOOK_SCRIPT"
cp "$SCRIPT_DIR/dedupe-agent-docs.sh" "$STAGING_INSTALL_SCRIPT_DIR/dedupe-agent-docs.sh"
chmod +x "$STAGING_INSTALL_SCRIPT_DIR/dedupe-agent-docs.sh"

shell_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

write_hook() {
  hook_name=$1
  existing_hook=
  if [ "$CHAIN_EXISTING" -eq 1 ] && [ -n "$existing_hooks_path_resolved" ] && [ "$existing_hooks_path_resolved" != "$HOOK_ROOT" ]; then
    existing_hook=$existing_hooks_path_resolved/$hook_name
  fi

  hook_path=$STAGING_ROOT/$hook_name
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

if [ -e "$HOOK_ROOT" ]; then
  if [ -L "$HOOK_ROOT" ]; then
    echo "Refusing to replace symlink hook root: $HOOK_ROOT" >&2
    exit 1
  fi
  mv "$HOOK_ROOT" "$BACKUP_ROOT"
fi

if ! mv "$STAGING_ROOT" "$HOOK_ROOT"; then
  if [ -e "$BACKUP_ROOT" ] && [ ! -e "$HOOK_ROOT" ]; then
    mv "$BACKUP_ROOT" "$HOOK_ROOT" || true
  fi
  echo 'Failed to activate global hook files; previous installation was restored.' >&2
  exit 1
fi
STAGING_ROOT=
HOOK_ACTIVATED=1

if ! git config --global core.hooksPath "$HOOK_ROOT"; then
  rm -rf "$HOOK_ROOT"
  if [ -e "$BACKUP_ROOT" ]; then
    mv "$BACKUP_ROOT" "$HOOK_ROOT"
  fi
  HOOK_ACTIVATED=0
  if [ -n "$existing_hooks_path" ]; then
    git config --global core.hooksPath "$existing_hooks_path" || true
  else
    git config --global --unset core.hooksPath >/dev/null 2>&1 || true
  fi
  echo 'Failed to configure global hooks; previous installation and Git configuration were restored.' >&2
  exit 1
fi

if [ -e "$BACKUP_ROOT" ]; then
  rm -rf "$BACKUP_ROOT"
fi
INSTALL_COMMITTED=1

cat <<EOF
Installed oceans777 global Git hooks:
  $HOOK_ROOT

Installed self-contained guard library:
  $INSTALL_ROOT

Configured:
  git config --global core.hooksPath "$HOOK_ROOT"

The guard is read-only. Missing required agent docs block the commit and must be
created explicitly with the bootstrap command or by the user.
EOF
