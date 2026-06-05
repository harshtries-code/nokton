import os
import shutil
from pathlib import Path
from .registry import tool


@tool(category="file_read")
def list_dir(path: str = ".") -> str:
    """List files and directories at the given path.
    Args:
        path: Directory path to list. Defaults to current directory.
    Returns:
        Formatted listing of directory contents.
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"Error: path '{path}' does not exist"
    if not p.is_dir():
        return f"Error: '{path}' is not a directory"

    entries = []
    for entry in sorted(p.iterdir()):
        suffix = "/" if entry.is_dir() else ""
        size = entry.stat().st_size if entry.is_file() else 0
        if size > 0:
            entries.append(f"{entry.name}{suffix} ({_format_size(size)})")
        else:
            entries.append(f"{entry.name}{suffix}")
    return "\n".join(entries) if entries else "(empty directory)"


@tool(category="file_read")
def read_file(path: str) -> str:
    """Read the contents of a text file.
    Args:
        path: Path to the file to read.
    Returns:
        File contents as text.
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"Error: file '{path}' does not exist"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


@tool(category="file_write")
def write_file(path: str, content: str) -> str:
    """Write content to a file (creates or overwrites).
    Args:
        path: Path to the file to write.
        content: Text content to write to the file.
    Returns:
        Confirmation message.
    """
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written {len(content)} bytes to {path}"


@tool(category="file_read")
def search_files(query: str, folder: str = ".", max_results: int = 20) -> str:
    """Search for files matching a name pattern using glob.
    Args:
        query: File name pattern to search for (supports wildcards like *.py).
        folder: Directory to search in. Defaults to current directory.
        max_results: Maximum number of results to return. Defaults to 20.
    Returns:
        List of matching file paths.
    """
    results = []
    p = Path(folder).expanduser().resolve()
    for f in p.rglob(query):
        results.append(str(f.relative_to(p)))
        if len(results) >= max_results:
            break
    return "\n".join(results) if results else "No matches found"


@tool(category="file_write", requires_confirm=True)
def delete_file(path: str) -> str:
    """Permanently delete a file or empty directory.
    Args:
        path: Path to the file or directory to delete.
    Returns:
        Confirmation message.
    """
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return f"Error: '{path}' does not exist"
    if p.is_file():
        p.unlink()
        return f"Deleted file: {path}"
    if p.is_dir():
        p.rmdir()
        return f"Deleted empty directory: {path}"
    return f"Error: '{path}' is not a file or empty directory"


@tool(category="file_write")
def create_file(path: str, content: str = "") -> str:
    """Create a new file with optional content.
    Args:
        path: Path where to create the file.
        content: Optional content to write into the file.
    Returns:
        Confirmation message.
    """
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created file: {path} ({len(content)} bytes)"


@tool(category="file_write", requires_confirm=True)
def move_file(source: str, dest: str) -> str:
    """Move or rename a file or directory.
    Args:
        source: Current path of the file/directory.
        dest: Destination path.
    Returns:
        Confirmation message.
    """
    src = Path(source).expanduser().resolve()
    dst = Path(dest).expanduser().resolve()
    if not src.exists():
        return f"Error: source '{source}' does not exist"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"Moved: {source} -> {dest}"


@tool(category="file_write", requires_confirm=True)
def copy_file(source: str, dest: str) -> str:
    """Copy a file to a new location.
    Args:
        source: Path to the source file.
        dest: Destination path.
    Returns:
        Confirmation message.
    """
    src = Path(source).expanduser().resolve()
    dst = Path(dest).expanduser().resolve()
    if not src.exists():
        return f"Error: source '{source}' does not exist"
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        return f"Copied: {source} -> {dest}"
    return f"Error: '{source}' is not a file"


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"
