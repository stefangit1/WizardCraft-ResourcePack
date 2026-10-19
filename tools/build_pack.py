#!/usr/bin/env python3
"""Builds the WizardCraft resource pack from the folder pack/ and checks it.

    python3 tools/build_pack.py
        Local build into build/, to try the pack in your own client.
    python3 tools/build_pack.py --repository owner/repo --tag pack-main --version "build 5 (abc1234)"
        What the GitHub workflow does: also writes build/manifest.json for the server.

Writes build/WizardCraft-Pack-<first 12 characters of the SHA-1>.zip. The zip is deterministic: the same
files always give the same bytes, so a pack that did not change keeps its SHA-1 and players do not download
it again.
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "pack"
BUILD = ROOT / "build"
IGNORED = {".DS_Store", "Thumbs.db", "desktop.ini"}
MAX_SIZE = 250 * 1024 * 1024  # the largest pack Minecraft clients accept


def pack_files():
    """All files of pack/ as (path inside the zip, file), sorted so the zip is always the same."""
    entries = []
    for path in sorted(PACK.rglob("*")):
        relative = path.relative_to(PACK)
        if path.is_file() and path.name not in IGNORED and not any(part.startswith(".git") for part in relative.parts):
            entries.append((relative.as_posix(), path))
    return entries


def split(reference):
    """'wizardcraft:item/spell/x' -> ('wizardcraft', 'item/spell/x'); without namespace it is minecraft."""
    namespace, _, path = reference.rpartition(":")
    return namespace or "minecraft", path


def check(entries):
    """Returns a list of problems; an empty list means the pack is fine."""
    problems = []
    names = {name for name, _ in entries}

    if "pack.mcmeta" not in names:
        return ["pack/pack.mcmeta is missing (it must be a file, not a folder)"]

    documents = {}
    for name, path in entries:
        if name.endswith((".json", ".mcmeta")):
            try:
                documents[name] = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as error:
                problems.append(f"{name}: not valid JSON ({error})")

    meta = documents.get("pack.mcmeta", {}).get("pack", {})
    for key in ("description", "min_format", "max_format"):
        if key not in meta:
            problems.append(f"pack.mcmeta: pack.{key} is missing")

    def require(file_name, what):
        if file_name not in names:
            problems.append(f"{what} points to {file_name}, which does not exist")

    def own(reference):
        namespace, path = split(reference)
        return namespace != "minecraft", namespace, path

    def walk(node, name):
        if isinstance(node, dict):
            if node.get("type") == "minecraft:model" and isinstance(node.get("model"), str):
                is_own, namespace, path = own(node["model"])
                if is_own:
                    require(f"assets/{namespace}/models/{path}.json", f"{name}: model {node['model']}")
            for value in node.values():
                walk(value, name)
        elif isinstance(node, list):
            for value in node:
                walk(value, name)

    for name, document in documents.items():
        parts = name.split("/")
        if len(parts) > 3 and parts[0] == "assets" and parts[2] == "items":
            walk(document, name)
        if len(parts) > 3 and parts[0] == "assets" and parts[2] == "models" and isinstance(document, dict):
            parent = document.get("parent")
            if isinstance(parent, str):
                is_own, namespace, path = own(parent)
                if is_own:
                    require(f"assets/{namespace}/models/{path}.json", f"{name}: parent {parent}")
            for texture in (document.get("textures") or {}).values():
                if isinstance(texture, str) and not texture.startswith("#"):
                    is_own, namespace, path = own(texture)
                    if is_own:
                        require(f"assets/{namespace}/textures/{path}.png", f"{name}: texture {texture}")
    return problems


def write_zip(entries, target):
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repository", help="owner/name of the GitHub repository, for the download URL in the manifest")
    parser.add_argument("--tag", help="release tag the pack is published under, e.g. pack-main")
    parser.add_argument("--version", default="dev", help="text shown by /wizardcraft pack, e.g. 'build 5 (abc1234)'")
    args = parser.parse_args()

    entries = pack_files()
    problems = check(entries)
    if problems:
        print("The pack has problems:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    BUILD.mkdir(exist_ok=True)
    for old in BUILD.glob("WizardCraft-Pack-*.zip"):
        old.unlink()
    temporary = BUILD / "pack.tmp"
    write_zip(entries, temporary)
    data = temporary.read_bytes()
    if len(data) > MAX_SIZE:
        print(f"The pack is {len(data) // 1024 // 1024} MB, Minecraft accepts at most 250 MB", file=sys.stderr)
        temporary.unlink()
        return 1

    sha1 = hashlib.sha1(data).hexdigest()
    target = BUILD / f"WizardCraft-Pack-{sha1[:12]}.zip"
    temporary.replace(target)
    print(f"{target.name}: {len(entries)} files, {len(data) / 1024:.0f} KB, SHA-1 {sha1}")

    if args.repository and args.tag:
        manifest = {
            "url": f"https://github.com/{args.repository}/releases/download/{args.tag}/{target.name}",
            "sha1": sha1,
            "version": args.version,
        }
        (BUILD / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"manifest.json: {manifest['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
