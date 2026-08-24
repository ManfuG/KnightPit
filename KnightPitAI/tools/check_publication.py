from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
FRONTEND = PROJECT.parent
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    ".mypy_cache",
    "graphify-out",
}
ALLOWED_ARTIFACT_ROOTS = {
    PROJECT / "checkpoints",
    PROJECT / "data" / "generated",
    PROJECT / "exports",
    PROJECT / ".campaign-smoke",
}
FORBIDDEN_SUFFIXES = {".pgn", ".bin", ".exe", ".dll", ".so", ".dylib", ".wasm", ".pyc", ".class", ".7z", ".rar", ".tar", ".gz", ".zip"}
CHECKPOINT_SUFFIXES = {".npz", ".jsonl"}
MAX_CHECKPOINT_BYTES = 10 * 1024 * 1024
FORBIDDEN_SOURCE = re.compile(r"\bstockfish\b", re.IGNORECASE)
PRIVATE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]+Users[\\/]|/Users/|/home/)", re.IGNORECASE)
DOC_NAMES = {"readme.md", "third_party_notices.md", "license"}



def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def in_allowed_artifact_root(path: Path) -> bool:
    return any(root == path or root in path.parents for root in ALLOWED_ARTIFACT_ROOTS)


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in (PROJECT, FRONTEND):
        for path in root.rglob("*"):
            if path.is_file() and not is_skipped(path) and path not in files:
                files.append(path)
    return sorted(files)


def main() -> int:
    findings: list[str] = []
    for path in iter_files():
        lower_name = path.name.lower()
        suffix = path.suffix.lower()
        relative = path.relative_to(FRONTEND)
        if suffix in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden binary/archive: {relative}")
            continue
        if suffix in CHECKPOINT_SUFFIXES:
            if not in_allowed_artifact_root(path):
                findings.append(f"generated artifact outside ignored output: {relative}")
            if suffix == ".npz" and path.stat().st_size > MAX_CHECKPOINT_BYTES:
                findings.append(f"checkpoint exceeds {MAX_CHECKPOINT_BYTES} bytes: {relative}")
            continue
        if FORBIDDEN_SOURCE.search(path.name):
            findings.append(f"forbidden engine artifact name: {relative}")
        if path.resolve() == Path(__file__).resolve():
            continue
        if lower_name in DOC_NAMES:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                findings.append(f"unreadable/non-text publication file: {relative}")
                continue
            if PRIVATE_PATH.search(text):
                findings.append(f"personal path found in publication file: {relative}")
            continue
        if lower_name.endswith(".lock"):
            continue
        try:
            if path.stat().st_size <= 2_000_000:
                text = path.read_text(encoding="utf-8")
            else:
                text = ""
        except (OSError, UnicodeDecodeError):
            findings.append(f"unreadable/non-text publication file: {relative}")
            continue
        if PRIVATE_PATH.search(text):
            findings.append(f"personal path found in publication file: {relative}")
        if FORBIDDEN_SOURCE.search(text):
            findings.append(f"forbidden engine reference in source/config: {relative}")
    if findings:
        print("Publication audit failed:")
        print("\n".join(f"- {finding}" for finding in findings))
        return 1
    print("Publication audit passed: no forbidden engines, datasets, binaries, or misplaced artifacts found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
