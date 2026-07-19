import pytest
from pathlib import Path

from actions_tool_kit.actions_io import which, mkdirp, rmrf, cp, mv, glob


def test_which_finds_python():
    # sys.executable is the full path so which may return None; use "python3" instead
    result = which("python3") or which("python")
    assert result is not None


def test_which_missing_returns_none():
    assert which("__nonexistent_binary_xyz__") is None


def test_which_missing_required_raises():
    with pytest.raises(FileNotFoundError, match="__nonexistent_binary_xyz__"):
        which("__nonexistent_binary_xyz__", required=True)


def test_mkdirp_creates_nested(tmp_path):
    target = tmp_path / "a" / "b" / "c"
    assert not target.exists()
    result = mkdirp(target)
    assert target.is_dir()
    assert result == target


def test_mkdirp_idempotent(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    mkdirp(target)  # must not raise
    assert target.is_dir()


def test_mkdirp_returns_path(tmp_path):
    target = tmp_path / "new_dir"
    returned = mkdirp(target)
    assert isinstance(returned, Path)
    assert returned == target


def test_rmrf_removes_file(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    rmrf(f)
    assert not f.exists()


def test_rmrf_removes_directory_tree(tmp_path):
    d = tmp_path / "tree"
    (d / "sub").mkdir(parents=True)
    (d / "sub" / "file.txt").write_text("x")
    rmrf(d)
    assert not d.exists()


def test_rmrf_missing_path_is_noop(tmp_path):
    rmrf(tmp_path / "does_not_exist")  # must not raise


def test_rmrf_removes_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("data")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    rmrf(link)
    assert not link.exists()
    assert target.exists()  # target untouched


# ---------------------------------------------------------------------------
# cp
# ---------------------------------------------------------------------------

def test_cp_file(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello")
    dest = tmp_path / "dest.txt"
    result = cp(src, dest)
    assert result == dest
    assert dest.read_text() == "hello"
    assert src.exists()  # original untouched


def test_cp_file_creates_parent_dirs(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    dest = tmp_path / "a" / "b" / "dest.txt"
    cp(src, dest)
    assert dest.read_text() == "data"


def test_cp_directory(tmp_path):
    src = tmp_path / "srcdir"
    src.mkdir()
    (src / "file.py").write_text("x = 1")
    (src / "sub").mkdir()
    (src / "sub" / "nested.py").write_text("y = 2")

    dest = tmp_path / "destdir"
    result = cp(src, dest)
    assert result == dest
    assert (dest / "file.py").read_text() == "x = 1"
    assert (dest / "sub" / "nested.py").read_text() == "y = 2"


def test_cp_directory_into_existing_dir(tmp_path):
    src = tmp_path / "mylib"
    src.mkdir()
    (src / "mod.py").write_text("pass")

    parent = tmp_path / "packages"
    parent.mkdir()

    result = cp(src, parent)
    assert result == parent / "mylib"
    assert (parent / "mylib" / "mod.py").read_text() == "pass"


# ---------------------------------------------------------------------------
# mv
# ---------------------------------------------------------------------------

def test_mv_file(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("move me")
    dest = tmp_path / "dest.txt"
    result = mv(src, dest)
    assert result == dest
    assert dest.read_text() == "move me"
    assert not src.exists()


def test_mv_creates_parent_dirs(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    dest = tmp_path / "deep" / "nested" / "out.txt"
    mv(src, dest)
    assert dest.read_text() == "data"


def test_mv_directory(tmp_path):
    src = tmp_path / "srcdir"
    src.mkdir()
    (src / "a.py").write_text("a")

    dest = tmp_path / "destdir"
    mv(src, dest)
    assert (dest / "a.py").read_text() == "a"
    assert not src.exists()


# ---------------------------------------------------------------------------
# glob
# ---------------------------------------------------------------------------

def test_glob_finds_files(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    (tmp_path / "c.txt").write_text("")

    results = glob("*.py", root=tmp_path)
    names = [p.name for p in results]
    assert "a.py" in names
    assert "b.py" in names
    assert "c.txt" not in names


def test_glob_recursive(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "root.py").write_text("")
    (sub / "nested.py").write_text("")

    results = glob("**/*.py", root=tmp_path)
    names = [p.name for p in results]
    assert "root.py" in names
    assert "nested.py" in names


def test_glob_no_match_returns_empty(tmp_path):
    results = glob("*.rs", root=tmp_path)
    assert results == []


def test_glob_returns_sorted(tmp_path):
    for name in ["c.py", "a.py", "b.py"]:
        (tmp_path / name).write_text("")
    results = glob("*.py", root=tmp_path)
    assert [p.name for p in results] == ["a.py", "b.py", "c.py"]
