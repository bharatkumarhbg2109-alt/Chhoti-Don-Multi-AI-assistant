"""
Chhoti Don - File Reader
Advanced file reading with multi-format support,
encoding detection, metadata extraction, and search.
Phase 2.2 - Full Upgrade
"""

import os
import json
import csv
import datetime
import hashlib
from typing import Dict, List, Optional, Any
# 🎯 SUPPORTED FORMATS
# ==================================================

SUPPORTED_TEXT_FORMATS = {
    ".txt", ".py", ".js", ".ts", ".html", ".htm", ".css",
    ".json", ".yaml", ".yml", ".xml", ".csv", ".tsv",
    ".md", ".rst", ".log", ".sh", ".bat", ".ps1",
    ".java", ".c", ".cpp", ".h", ".cs", ".go", ".rs",
    ".sql", ".r", ".rb", ".php", ".swift", ".kt",
    ".env", ".cfg", ".ini", ".conf", ".config",
    ".toml", ".dockerfile", "",
}

BINARY_FORMATS = {".pdf", ".docx", ".xlsx", ".pptx", ".zip", ".tar", ".gz"}

# Max file size for reading (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def read_file(data: Dict) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Advanced file reading with full metadata.
    """
    if not isinstance(data, dict):
        return {"status": "error", "message": "Input must be a dictionary"}

    path = data.get("path") or data.get("file_path") or data.get("input")

    if not path:
        return {"status": "error", "message": "Missing 'path' parameter"}

    reader = FileReader()
    return reader.read(
        path=path,
        encoding=data.get("encoding"),
        max_lines=data.get("max_lines"),
        search_term=data.get("search"),
        include_metadata=data.get("metadata", True),
    )


class FileReader:
    """
    Advanced File Reader.
    Handles multiple formats with smart encoding detection.
    """

    def read(
        self,
        path: str,
        encoding: str = None,
        max_lines: int = None,
        search_term: str = None,
        include_metadata: bool = True,
    ) -> Dict:
        """
        Read file with full analysis.
        """
        # Existence check
        if not os.path.exists(path):
            return {"status": "error", "message": f"File not found: {path}"}

        if not os.path.isfile(path):
            return {"status": "error", "message": f"Not a file: {path}"}

        # Size check
        file_size = os.path.getsize(path)
        if file_size > MAX_FILE_SIZE:
            return {
                "status": "error",
                "message": f"File too large ({self._format_size(file_size)}). Max: 10MB",
            }

        # File info
        ext = os.path.splitext(path)[1].lower()
        file_name = os.path.basename(path)

        # Route to format reader
        if ext == ".json":
            result = self._read_json(path)
        elif ext in (".yaml", ".yml"):
            result = self._read_yaml(path)
        elif ext == ".csv":
            result = self._read_csv(path, max_lines)
        elif ext in BINARY_FORMATS:
            result = self._read_binary_info(path)
        else:
            result = self._read_text(path, encoding, max_lines)

        if result.get("status") == "error":
            return result

        # Search within content
        if search_term and "content" in result:
            result["search_results"] = self._search_content(
                result["content"], search_term
            )

        # Metadata
        if include_metadata:
            result["metadata"] = self._get_metadata(path, file_size)

        result.update({
            "file_name": file_name,
            "file_path": path,
            "file_size": file_size,
            "file_size_human": self._format_size(file_size),
            "extension": ext,
        })

        return result

    # --------------------------------------------------
    # 📄 Text Reader
    # --------------------------------------------------
    def _read_text(
        self,
        path: str,
        encoding: str = None,
        max_lines: int = None,
    ) -> Dict:
        """Text file read karo with encoding detection."""
        encodings = [encoding] if encoding else ["utf-8", "utf-16", "latin-1", "ascii"]

        for enc in encodings:
            if not enc:
                continue
            try:
                with open(path, "r", encoding=enc, errors="strict") as f:
                    if max_lines:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= max_lines:
                                break
                            lines.append(line)
                        content = "".join(lines)
                        truncated = True
                    else:
                        content = f.read()
                        truncated = False

                line_count = content.count("\n") + 1

                return {
                    "status": "success",
                    "content": content,
                    "encoding": enc,
                    "line_count": line_count,
                    "char_count": len(content),
                    "word_count": len(content.split()),
                    "truncated": truncated,
                }
            except (UnicodeDecodeError, LookupError):
                continue
            except PermissionError:
                return {"status": "error", "message": "Permission denied"}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # Binary fallback
        return self._read_binary_info(path)

    # --------------------------------------------------
    # 📋 JSON Reader
    # --------------------------------------------------
    def _read_json(self, path: str) -> Dict:
        """JSON file read and parse karo."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                data = json.loads(content)

            return {
                "status": "success",
                "content": content,
                "parsed": data,
                "type": type(data).__name__,
                "keys": list(data.keys()) if isinstance(data, dict) else None,
                "length": len(data) if isinstance(data, (list, dict)) else None,
                "encoding": "utf-8",
            }
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # --------------------------------------------------
    # 📊 CSV Reader
    # --------------------------------------------------
    def _read_csv(self, path: str, max_rows: int = None) -> Dict:
        """CSV file read karo."""
        try:
            rows = []
            headers = []

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                for i, row in enumerate(reader):
                    if max_rows and i >= max_rows:
                        break
                    rows.append(dict(row))

            content = "\n".join(
                ",".join(str(v) for v in row.values()) for row in rows[:10]
            )

            return {
                "status": "success",
                "content": content,
                "headers": list(headers),
                "rows": rows,
                "total_rows": len(rows),
                "total_columns": len(headers),
                "encoding": "utf-8",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # --------------------------------------------------
    # 📦 YAML Reader
    # --------------------------------------------------
    def _read_yaml(self, path: str) -> Dict:
        """YAML file read karo."""
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                data = yaml.safe_load(content)

            return {
                "status": "success",
                "content": content,
                "parsed": data,
                "encoding": "utf-8",
            }
        except ImportError:
            # Fallback to text read
            return self._read_text(path)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # --------------------------------------------------
    # 📦 Binary Info
    # --------------------------------------------------
    def _read_binary_info(self, path: str) -> Dict:
        """Binary file info only."""
        try:
            with open(path, "rb") as f:
                header = f.read(16).hex()

            sha256 = self._hash_file(path)

            return {
                "status": "success",
                "content": f"[Binary file — hex header: {header}]",
                "binary": True,
                "sha256": sha256,
                "note": "Binary file — content not displayed",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # --------------------------------------------------
    # 🔍 Search
    # --------------------------------------------------
    def _search_content(self, content: str, term: str) -> Dict:
        """Content mein search karo."""
        lines = content.splitlines()
        matches = []

        for i, line in enumerate(lines, 1):
            if term.lower() in line.lower():
                matches.append({
                    "line_number": i,
                    "content": line.strip(),
                    "match_count": line.lower().count(term.lower()),
                })

        return {
            "search_term": term,
            "total_matches": len(matches),
            "matches": matches[:20],
        }

    # --------------------------------------------------
    # 📋 Metadata
    # --------------------------------------------------
    def _get_metadata(self, path: str, size: int) -> Dict:
        """File metadata lo."""
        try:
            stat = os.stat(path)
            return {
                "size_bytes": size,
                "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.datetime.fromtimestamp(stat.st_atime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
                "sha256": self._hash_file(path),
            }
        except Exception:
            return {}

    def _hash_file(self, path: str) -> str:
        """File SHA256 hash calculate karo."""
        try:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return "unknown"

    def _format_size(self, size: int) -> str:
        """Human readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# ==================================================
# 🔧 STANDALONE FUNCTIONS
# ==================================================

def read_directory(path: str, pattern: str = None) -> Dict:
    """Directory listing with file info."""
    if not os.path.exists(path):
        return {"status": "error", "message": "Directory not found"}
    if not os.path.isdir(path):
        return {"status": "error", "message": "Not a directory"}

    items = []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        is_dir = os.path.isdir(item_path)

        if pattern and pattern.lower() not in item.lower():
            continue

        try:
            size = os.path.getsize(item_path) if not is_dir else 0
            items.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "size": size,
                "extension": os.path.splitext(item)[1] if not is_dir else "",
            })
        except Exception:
            pass

    files = [i for i in items if i["type"] == "file"]
    dirs = [i for i in items if i["type"] == "directory"]

    return {
        "status": "success",
        "path": path,
        "total_items": len(items),
        "files": len(files),
        "directories": len(dirs),
        "items": items[:100],
    }
