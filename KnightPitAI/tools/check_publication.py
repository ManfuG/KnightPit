from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
FRONTEND = PROJECT.parent
ALLOWED_ARTIFACT_ROOTS = {
    PROJECT / "checkpoints",
    PROJECT / "data" / "generated",
    PROJECT / "exports",
    PROJECT / ".campaign-smoke",
}
FORBIDDEN_SUFFIXES = {".pgn", ".bin", ".exe", ".dll", ".so", ".dylib", ".wasm", ".pyc", ".class", ".jar", ".nnue", ".7z", ".rar", ".tar", ".gz", ".zip"}
CHECKPOINT_SUFFIXES = {".npz", ".jsonl"}
MAX_CHECKPOINT_BYTES = 10 * 1024 * 1024
FORBIDDEN_SOURCE = re.compile(r"\bstockfish\b", re.IGNORECASE)
PRIVATE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]+Users[\\/]|/Users/|/home/)", re.IGNORECASE)
DOC_NAMES = {"readme.md", "third_party_notices.md", "license"}
PUBLIC_BINARY_ASSETS = {
    "public/fonts/syne-variable.ttf": "public/fonts/Syne-OFL.txt",
    "public/fonts/fraunces-latin.woff2": "public/fonts/Fraunces-OFL.txt",
    "public/fonts/fraunces-italic-latin.woff2": "public/fonts/Fraunces-OFL.txt",
    "media/knightpit-demo.webp": "README.md",
    "media/knightpit-demo.mp4": "README.md",
}
ENGINE_ROOT = FRONTEND / "public" / "engine" / "stockfish-19.0.1"
ENGINE_FILES = {
    "stockfish-19-lite-single.js", "stockfish-19-lite-single.wasm",
    "stockfish.js-v19.0.1-source.tgz", "nn-61e7af4bb97d.nnue",
    "COPYING.txt", "AUTHORS.txt", "NOTICE.txt", "SHA256SUMS",
}
WRAPPER = "android/gradle/wrapper/gradle-wrapper.jar"
WRAPPER_SHA256 = "7d3a4ac4de1c32b59bc6a4eb8ecb8e612ccd0cf1ae1e99f66902da64df296172"


def in_allowed_artifact_root(path: Path) -> bool:
    return any(root == path or root in path.parents for root in ALLOWED_ARTIFACT_ROOTS)


def iter_files() -> list[Path]:
    """Audit publishable source, not ignored local environments or training runs."""
    result = subprocess.run(
        ["git", "-C", str(FRONTEND), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True, stdout=subprocess.PIPE,
    )
    return sorted({
        FRONTEND / name.decode("utf-8")
        for name in result.stdout.split(b"\0")
        if name and (FRONTEND / name.decode("utf-8")).is_file()
    })


def main() -> int:
    findings: list[str] = []
    manifest = ENGINE_ROOT / "SHA256SUMS"
    if not manifest.is_file():
        findings.append("missing pinned engine digest manifest")
    else:
        listed = set()
        for line in manifest.read_text(encoding="utf-8").splitlines():
            expected, name = line.split(maxsplit=1)
            name = name.lstrip("*")
            listed.add(name)
            asset = ENGINE_ROOT / name
            if name not in ENGINE_FILES or not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest() != expected:
                findings.append(f"engine integrity mismatch: {name}")
        if listed != ENGINE_FILES - {"SHA256SUMS"}:
            findings.append("engine manifest must cover the complete approved distribution")
    for path in iter_files():
        lower_name = path.name.lower()
        suffix = path.suffix.lower()
        relative = path.relative_to(FRONTEND)
        if relative.as_posix() == WRAPPER:
            if hashlib.sha256(path.read_bytes()).hexdigest() != WRAPPER_SHA256:
                findings.append("unexpected Gradle wrapper binary")
            continue
        if ENGINE_ROOT in path.parents:
            if path.parent != ENGINE_ROOT or path.name not in ENGINE_FILES:
                findings.append(f"unexpected engine distribution asset: {relative}")
            continue
        asset_notice = PUBLIC_BINARY_ASSETS.get(relative.as_posix())
        if asset_notice:
            notice = FRONTEND / asset_notice
            if not notice.is_file():
                findings.append(f"missing attribution for binary asset: {relative}")
            elif relative.parts[0] == "public" and "SIL OPEN FONT LICENSE" not in notice.read_text(encoding="utf-8"):
                findings.append(f"invalid font attribution: {relative}")
            elif relative.parts[0] == "media" and relative.as_posix() not in notice.read_text(encoding="utf-8"):
                findings.append(f"undocumented demo asset: {relative}")
            continue
        if suffix in FORBIDDEN_SUFFIXES:
            findings.append(f"forbidden binary/archive: {relative}")
            continue
        if suffix in CHECKPOINT_SUFFIXES:
            if not in_allowed_artifact_root(path):
                findings.append(f"generated artifact outside ignored output: {relative}")
            if suffix == ".npz" and path.stat().st_size > MAX_CHECKPOINT_BYTES:
                findings.append(f"checkpoint exceeds {MAX_CHECKPOINT_BYTES} bytes: {relative}")
            continue
        if PROJECT in path.parents and FORBIDDEN_SOURCE.search(path.name):
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
        if PROJECT in path.parents and FORBIDDEN_SOURCE.search(text):
            findings.append(f"forbidden engine reference in source/config: {relative}")
    if findings:
        print("Publication audit failed:")
        print("\n".join(f"- {finding}" for finding in findings))
        return 1
    print("Publication audit passed: pinned offline engine/source, native wrapper, licensed fonts and demo assets verified; no unexpected binaries, personal paths or engine leaks into Python research.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
