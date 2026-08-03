#!/usr/bin/env python3
"""Configuration, locking, and managed path access for Idea Ledger."""
from __future__ import annotations

from _idea_ledger_foundation import *

def config_path(root: Path) -> Path:
    return safe_project_path(root, CONFIG_FILE, "config_file")


def parse_config_text(root: Path, text: str, *, label: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{label} JSON 无效：{exc}") from exc
    if not isinstance(data, dict):
        raise LedgerError(f"{label} 顶层必须是对象。")
    return normalize_config(root, data, label=label)


def load_config(root: Path, *, require: bool = True) -> dict[str, Any]:
    path = config_path(root)
    if not path.exists():
        if require:
            raise LedgerError("当前项目尚未初始化 Idea Ledger；显式运行 init。")
        return default_config()
    config = read_json_object(path, label="Idea Ledger 配置")
    return normalize_config(root, config)


def _try_file_lock(fd: int) -> str:
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return "fcntl"
    if msvcrt is not None:  # pragma: no cover - exercised on Windows
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"\0")
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        return "msvcrt"
    raise LedgerError("当前平台不支持可靠的文件锁。")


def _release_file_lock(fd: int, backend: str) -> None:
    if backend == "fcntl":
        assert fcntl is not None
        fcntl.flock(fd, fcntl.LOCK_UN)
    elif backend == "msvcrt":  # pragma: no cover - exercised on Windows
        assert msvcrt is not None
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


@contextlib.contextmanager
def ledger_lock(root: Path, *, timeout_seconds: float = 5.0) -> Iterator[None]:
    """Use an OS advisory lock; crashes release it without stale-file deletion races."""
    if timeout_seconds < 0:
        raise LedgerError("锁等待时间不能为负数。")
    path = safe_project_path(root, LOCK_FILE, "lock_file")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise LedgerError(f"锁文件不得是符号链接：{path}") from exc
        raise LedgerError(f"无法打开账本锁：{path}：{exc}") from exc
    deadline = time.monotonic() + timeout_seconds
    backend: str | None = None
    try:
        while backend is None:
            try:
                backend = _try_file_lock(fd)
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise LedgerError(f"无法获取账本锁：{path}：{exc}") from exc
                if time.monotonic() >= deadline:
                    raise LedgerError(f"账本正被另一个进程使用：{path}") from exc
                time.sleep(0.05)
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, f"pid={os.getpid()}\nacquired_at={utc_now()}\n".encode("utf-8"))
        os.fsync(fd)
        yield
    finally:
        if backend is not None:
            with contextlib.suppress(OSError):
                _release_file_lock(fd, backend)
        os.close(fd)


def records_dir(root: Path, config: dict[str, Any] | None = None) -> Path:
    cfg = config or load_config(root)
    return safe_project_path(root, str(cfg["records_dir"]), "records_dir")


def index_path(root: Path, config: dict[str, Any] | None = None) -> Path:
    cfg = config or load_config(root)
    return safe_project_path(root, str(cfg["index_file"]), "index_file")


def prd_dir(root: Path, config: dict[str, Any] | None = None) -> Path:
    cfg = config or load_config(root)
    return safe_project_path(root, str(cfg["prd_dir"]), "prd_dir")


def record_path(root: Path, idea_id: str, config: dict[str, Any] | None = None) -> Path:
    path = records_dir(root, config) / f"{normalize_id(idea_id)}.md"
    if path.is_symlink():
        raise LedgerError(f"记录文件不得是符号链接：{path}")
    return path


def list_record_paths(root: Path, config: dict[str, Any] | None = None) -> list[Path]:
    directory = records_dir(root, config)
    if not directory.exists():
        return []
    _validate_existing_kind(directory, "records_dir", directory=True)
    paths: list[Path] = []
    invalid_names: list[str] = []
    for path in directory.iterdir():
        if path.name.startswith("IDEA-") and path.suffix == ".md":
            match = RECORD_FILE_RE.fullmatch(path.name)
            if not match:
                invalid_names.append(path.name)
                continue
            canonical = f"IDEA-{int(match.group(1)):04d}.md"
            if path.name != canonical:
                invalid_names.append(path.name)
                continue
        else:
            continue
        if path.is_symlink():
            raise LedgerError(f"记录文件不得是符号链接：{path}")
        try:
            info = path.lstat()
        except OSError as exc:
            raise LedgerError(f"无法检查记录文件：{path}：{exc}") from exc
        if not stat.S_ISREG(info.st_mode):
            raise LedgerError(f"记录路径必须是普通文件：{path}")
        paths.append(path)
    if invalid_names:
        raise LedgerError("记录文件名必须使用规范编号（例如 IDEA-0001.md）：" + "、".join(sorted(invalid_names)))
    return sorted(paths, key=lambda path: int(RECORD_FILE_RE.fullmatch(path.name).group(1)))  # type: ignore[union-attr]

__all__ = [name for name in globals() if not name.startswith("__")]
