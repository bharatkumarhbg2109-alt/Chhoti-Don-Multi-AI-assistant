"""
Chhoti Don - Hands Layer :: File System Hand

Read / write / organise files and folders using pathlib, os and shutil.
Destructive actions (delete file / delete folder) require confirmation.
"""

from __future__ import annotations

import fnmatch
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseHand, Permission


class FileSystemHand(BaseHand):
    name = "filesystem"
    description = "Read, write, move, copy, zip and inspect files and folders."

    def __init__(self) -> None:
        super().__init__()
        R, W, D = Permission.READ_ONLY, Permission.WRITE, Permission.DANGEROUS
        self.register("read_file", self.read_file, permission=R, doc="Read a text file.")
        self.register("write_file", self.write_file, permission=W, doc="Write (overwrite) a text file.")
        self.register("append_file", self.append_file, permission=W, doc="Append to a text file.")
        self.register("rename", self.rename, permission=W, doc="Rename a file or folder.")
        self.register("move", self.move, permission=W, doc="Move a file or folder.")
        self.register("copy", self.copy, permission=W, doc="Copy a file or folder.")
        self.register("delete", self.delete, permission=D, destructive=True, doc="Delete a file.")
        self.register("create_folder", self.create_folder, permission=W, doc="Create a folder.")
        self.register("delete_folder", self.delete_folder, permission=D, destructive=True, doc="Delete a folder (recursive).")
        self.register("list_directory", self.list_directory, permission=R, doc="List a directory.")
        self.register("search_files", self.search_files, permission=R, doc="Search files by glob pattern.")
        self.register("zip", self.zip_path, permission=W, doc="Zip a file or folder.")
        self.register("unzip", self.unzip, permission=W, doc="Extract a zip archive.")
        self.register("file_info", self.file_info, permission=R, doc="Stat a file or folder.")

    # ── Read / write ─────────────────────────────────────────
    def read_file(self, path: str, encoding: str = "utf-8", max_bytes: int = 2_000_000) -> Dict[str, Any]:
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        data = p.read_bytes()[:max_bytes]
        return {"path": str(p), "text": data.decode(encoding, errors="replace"), "bytes": len(data)}

    def write_file(self, path: str, content: str = "", encoding: str = "utf-8") -> Dict[str, Any]:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding=encoding)
        return {"path": str(p), "written": len(content)}

    def append_file(self, path: str, content: str = "", encoding: str = "utf-8") -> Dict[str, Any]:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding=encoding) as fh:
            fh.write(content)
        return {"path": str(p), "appended": len(content)}

    # ── Organise ─────────────────────────────────────────────
    def rename(self, path: str, new_name: str) -> Dict[str, Any]:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {p}")
        target = p.with_name(new_name)
        p.rename(target)
        return {"from": str(p), "to": str(target)}

    def move(self, src: str, dst: str) -> Dict[str, Any]:
        s = Path(src).expanduser()
        if not s.exists():
            raise FileNotFoundError(f"Source not found: {s}")
        out = shutil.move(str(s), str(Path(dst).expanduser()))
        return {"from": str(s), "to": str(out)}

    def copy(self, src: str, dst: str) -> Dict[str, Any]:
        s = Path(src).expanduser()
        d = Path(dst).expanduser()
        if not s.exists():
            raise FileNotFoundError(f"Source not found: {s}")
        if s.is_dir():
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
        return {"from": str(s), "to": str(d)}

    def delete(self, path: str) -> Dict[str, Any]:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        if p.is_dir():
            raise IsADirectoryError("Use delete_folder for directories.")
        p.unlink()
        return {"deleted": str(p)}

    def create_folder(self, path: str) -> Dict[str, Any]:
        p = Path(path).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return {"created": str(p)}

    def delete_folder(self, path: str) -> Dict[str, Any]:
        p = Path(path).expanduser()
        if not p.is_dir():
            raise NotADirectoryError(f"Folder not found: {p}")
        shutil.rmtree(p)
        return {"deleted_folder": str(p)}

    # ── Inspect ──────────────────────────────────────────────
    def list_directory(self, path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
        p = Path(path).expanduser()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        entries = []
        for child in sorted(p.iterdir()):
            if not show_hidden and child.name.startswith("."):
                continue
            entries.append({
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            })
        return {"path": str(p), "count": len(entries), "entries": entries}

    def search_files(self, path: str = ".", pattern: str = "*", recursive: bool = True, limit: int = 500) -> Dict[str, Any]:
        p = Path(path).expanduser()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {p}")
        matches: List[str] = []
        walker = os.walk(p) if recursive else [(str(p), [], [c.name for c in p.iterdir()])]
        for root, _dirs, files in walker:
            for f in files:
                if fnmatch.fnmatch(f, pattern):
                    matches.append(os.path.join(root, f))
                    if len(matches) >= limit:
                        return {"pattern": pattern, "count": len(matches), "matches": matches, "truncated": True}
        return {"pattern": pattern, "count": len(matches), "matches": matches, "truncated": False}

    def file_info(self, path: str) -> Dict[str, Any]:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {p}")
        st = p.stat()
        return {
            "path": str(p),
            "type": "dir" if p.is_dir() else "file",
            "size": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
            "created": datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat(),
        }

    # ── Archive ──────────────────────────────────────────────
    def zip_path(self, src: str, dst: Optional[str] = None) -> Dict[str, Any]:
        s = Path(src).expanduser()
        if not s.exists():
            raise FileNotFoundError(f"Source not found: {s}")
        out = Path(dst).expanduser() if dst else s.with_suffix(s.suffix + ".zip") if s.is_file() else s.with_suffix(".zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            if s.is_dir():
                for root, _dirs, files in os.walk(s):
                    for f in files:
                        fp = Path(root) / f
                        zf.write(fp, fp.relative_to(s.parent))
            else:
                zf.write(s, s.name)
        return {"zipped": str(s), "archive": str(out)}

    def unzip(self, src: str, dst: Optional[str] = None) -> Dict[str, Any]:
        s = Path(src).expanduser()
        if not s.is_file():
            raise FileNotFoundError(f"Archive not found: {s}")
        out = Path(dst).expanduser() if dst else s.with_suffix("")
        out.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(s, "r") as zf:
            zf.extractall(out)
            names = zf.namelist()
        return {"archive": str(s), "extracted_to": str(out), "files": len(names)}
