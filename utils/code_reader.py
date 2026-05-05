import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".rb", ".php", ".cpp", ".c", ".cs", ".swift", ".kt",
    ".html", ".css", ".sql", ".sh", ".yaml", ".yml", ".json",
    ".env.example", ".toml"
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist",
    "build", "venv", ".venv", "env", ".env", "coverage",
    ".pytest_cache", "vendor"
}

MAX_FILE_SIZE_BYTES = 500 * 1024


def read_pasted_code(code: str) -> dict:
    return {
        "source": "paste",
        "files": [{"name": "pasted_code", "content": code, "language": detect_language(code)}],
        "total_lines": len(code.splitlines()),
        "total_chars": len(code)
    }


def read_single_file(file_path: str) -> dict:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if p.suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {p.suffix}")
    if p.stat().st_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File too large: {p.stat().st_size // 1024} KB. Max 500 KB.")

    content = p.read_text(encoding="utf-8", errors="replace")
    return {
        "source": "file",
        "files": [{"name": p.name, "content": content, "language": p.suffix.lstrip(".")}],
        "total_lines": len(content.splitlines()),
        "total_chars": len(content)
    }


def read_folder(folder_path: str, max_files: int = 20) -> dict:
    p = Path(folder_path)
    if not p.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    if not p.is_dir():
        raise ValueError(f"Path is not a folder: {folder_path}")

    collected = []

    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for fname in files:
            if len(collected) >= max_files:
                break
            fpath = Path(root) / fname
            if fpath.suffix not in SUPPORTED_EXTENSIONS:
                continue
            if fpath.stat().st_size > MAX_FILE_SIZE_BYTES:
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                relative_name = str(fpath.relative_to(p))
                collected.append({
                    "name": relative_name,
                    "content": content,
                    "language": fpath.suffix.lstrip(".")
                })
            except Exception:
                continue

    total_lines = sum(len(f["content"].splitlines()) for f in collected)
    total_chars = sum(len(f["content"]) for f in collected)

    return {
        "source": "folder",
        "files": collected,
        "total_lines": total_lines,
        "total_chars": total_chars,
        "truncated": len(collected) == max_files
    }


def detect_language(code: str) -> str:
    code_lower = code.lower()
    if "import react" in code_lower or "usestate" in code_lower or "jsx" in code_lower:
        return "javascript"
    if "def " in code and "import " in code:
        return "python"
    if "function " in code and ("const " in code or "let " in code or "var " in code):
        return "javascript"
    if "package main" in code or "func " in code:
        return "go"
    if "fn " in code and "let mut" in code:
        return "rust"
    if "SELECT " in code_lower or "FROM " in code_lower:
        return "sql"
    return "unknown"


def build_review_payload(code_data: dict, max_chars: int = 12000) -> str:
    parts = []
    total = 0
    for f in code_data["files"]:
        header = f"\n--- FILE: {f['name']} ---\n"
        content = f["content"]
        if total + len(content) > max_chars:
            remaining = max_chars - total
            if remaining > 500:
                content = content[:remaining] + "\n... [truncated for context window]"
            else:
                break
        parts.append(header + content)
        total += len(content)
    return "\n".join(parts)