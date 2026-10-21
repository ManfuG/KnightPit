"""Check source assets and the complete current web build against an offline APK."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def fail(message):
    raise SystemExit(message)


def digest(data):
    return hashlib.sha256(data).digest()


if len(sys.argv) != 2:
    fail("Usage: python3 scripts/check-android.py path/to/app.apk")

root = Path(__file__).resolve().parents[1]
public = root / "public"
dist = root / "dist"
if not (dist / "index.html").is_file():
    fail("Missing current web build. Run npm run android:sync first.")

with zipfile.ZipFile(sys.argv[1]) as archive:
    members = archive.namelist()
    names = set(members)
    if len(members) != len(names):
        fail("APK contains duplicate ZIP members.")
    checked_source = 0
    for source in public.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(public)
        built = dist / relative
        if not built.is_file() or digest(source.read_bytes()) != digest(built.read_bytes()):
            fail(f"Source asset missing or changed in current build: {relative}")
        checked_source += 1

    expected = set()
    checked_build = 0
    for source in dist.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(dist).as_posix()
        member = f"assets/public/{relative}"
        expected.add(member)
        if source.suffix == ".map" or any(part.startswith(".") for part in source.relative_to(dist).parts):
            fail(f"Unexpected development asset: {relative}")
        if member not in names:
            fail(f"Missing bundled build asset: {member}")
        if digest(source.read_bytes()) != digest(archive.read(member)):
            fail(f"Changed bundled build asset: {member}")
        checked_build += 1

    # Capacitor's empty Cordova compatibility entries are generated during sync.
    compatibility = {"assets/public/cordova.js", "assets/public/cordova_plugins.js"}
    for member in names:
        if not member.startswith("assets/public/") or member.endswith("/") or member in expected:
            continue
        if member not in compatibility or archive.read(member) != b"":
            fail(f"Unexpected bundled runtime asset: {member}")

    config_member = "assets/capacitor.config.json"
    if config_member not in names:
        fail("Missing bundled Capacitor configuration.")
    config = json.loads(archive.read(config_member))
    if config.get("appId") != "io.github.manfug.knightpit" or config.get("appName") != "KnightPit":
        fail("Unexpected native app identity.")
    if config.get("webDir") != "dist":
        fail("Unexpected bundled web directory.")
    if config.get("server") != {"hostname": "localhost", "androidScheme": "https"}:
        fail("APK must use the stable offline https://localhost origin without server.url.")
    if config.get("android", {}).get("minWebViewVersion") != 119:
        fail("APK must require System WebView 119 or newer.")
    if config.get("plugins", {}).get("SystemBars") != {"insetsHandling": "disable", "style": "DARK"}:
        fail("Native insets must be applied once with dark-surface system bars.")

print(f"APK offline integrity verified: {checked_source} public source files and {checked_build} build files match exactly.")
