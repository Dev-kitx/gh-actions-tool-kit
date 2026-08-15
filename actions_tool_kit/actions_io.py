from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Union


def which(tool: str, *, required: bool = False) -> Optional[str]:
    """Locate a tool on PATH using shutil.which.

    Args:
        tool: Executable name to search for (e.g. ``"git"``).
        required: If True, raise FileNotFoundError when the tool is absent.

    Returns:
        Absolute path to the binary, or None when not found and required=False.

    Raises:
        FileNotFoundError: When required=True and the tool is not on PATH.
    """
    path = shutil.which(tool)
    if path is None and required:
        raise FileNotFoundError(f"Tool not found on PATH: {tool!r}")
    return path


def mkdirp(path: Union[str, Path]) -> Path:
    """Create a directory and all intermediate parents (no-op if it already exists).

    Args:
        path: Directory path to create.

    Returns:
        The resolved Path that was created (or already existed).
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def rmrf(path: Union[str, Path]) -> None:
    """Recursively remove a file, symlink, or directory tree.

    Silently does nothing when path does not exist.

    Args:
        path: Path to remove.
    """
    p = Path(path)
    if not p.exists() and not p.is_symlink():
        return
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(str(p))
    else:
        p.unlink()


def cp(src: Union[str, Path], dest: Union[str, Path]) -> Path:
    """Copy *src* to *dest* and return the destination path.

    Directories are copied recursively (``shutil.copytree``).
    When *dest* is an existing directory the source is copied **into** it,
    matching the behaviour of the Unix ``cp -r`` command.
    Parent directories of *dest* are created automatically for file copies.

    Args:
        src: Source file or directory.
        dest: Destination path or parent directory.

    Returns:
        The final destination path.
    """
    s, d = Path(src), Path(dest)
    if s.is_dir():
        if d.is_dir():
            d = d / s.name
        shutil.copytree(str(s), str(d))
    else:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(s), str(d))
    return d


def mv(src: Union[str, Path], dest: Union[str, Path]) -> Path:
    """Move *src* to *dest* and return the destination path.

    Parent directories of *dest* are created automatically.

    Args:
        src: Source file or directory.
        dest: Destination path.

    Returns:
        The final destination path.
    """
    s, d = Path(src), Path(dest)
    d.parent.mkdir(parents=True, exist_ok=True)
    result = shutil.move(str(s), str(d))
    return Path(result)


def glob(pattern: str, *, root: Optional[Union[str, Path]] = None) -> List[Path]:
    """Return all paths under *root* that match *pattern*, sorted.

    Supports ``**`` for recursive matching (e.g. ``"**/*.py"``).
    *root* defaults to the current working directory.

    Args:
        pattern: Glob pattern relative to *root*.
        root: Base directory for the search (default: ``Path.cwd()``).

    Returns:
        Sorted list of matching :class:`~pathlib.Path` objects.
    """
    base = Path(root) if root is not None else Path.cwd()
    return sorted(base.glob(pattern))


__all__ = ["which", "mkdirp", "rmrf", "cp", "mv", "glob"]
