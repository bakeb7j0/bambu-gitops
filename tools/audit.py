#!/usr/bin/env python3
"""Read-only Bambu Studio filament preset audit; never alters input files.

Usage: python3 tools/audit.py filaments-20261018.tgz [--json]
Accepts .tar/.tgz archives or an extracted config folder.
Only includes filament/*.json entries and reports names, override *key names*,
parent resolution and exact-override duplicates (not raw personal data).
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

IDENTITY = {"name", "filament_settings_id", "setting_id", "from", "version", "inherits", "instantiation"}
SENSITIVE = re.compile(r"(?i)(token|secret|password|cookie|credential|auth|api.?key|access.?code)")

def inputs(source: Path):
    if source.is_dir():
        for path in sorted(source.rglob("*.json")):
            rel = path.relative_to(source).as_posix()
            if "filament" in PurePosixPath(rel).parts:
                yield rel, path.read_bytes()
    elif tarfile.is_tarfile(source):
        with tarfile.open(source, "r:*") as archive:
            for item in archive:
                posix = PurePosixPath(item.name)
                if not item.isfile() or posix.suffix != ".json" or "filament" not in posix.parts:
                    continue
                if posix.is_absolute() or ".." in posix.parts or item.size > 1024 * 1024:
                    continue
                f = archive.extractfile(item)
                if f:
                    yield item.name, f.read()
    else:
        raise ValueError("Source must be an extracted folder or tar archive")

def audit(source: Path) -> dict:
    presets, invalid, groups = [], [], collections.defaultdict(list)
    for rel, raw in inputs(source):
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
        except (ValueError, UnicodeError):
            invalid.append(PurePosixPath(rel).name)
            continue
        name = str(data.get("name", PurePosixPath(rel).stem))
        parent = str(data["inherits"]) if data.get("inherits") else None
        overrides = {k: v for k, v in data.items() if k not in IDENTITY}
        signature = (parent, json.dumps(overrides, sort_keys=True, ensure_ascii=False))
        groups[signature].append(name)
        presets.append({
            "name": name, "parent": parent,
            "section": "base" if "/base/" in "/" + rel else "user",
            "override_keys": sorted(overrides),
            "override_count": len(overrides),
            "possibly_sensitive_key_names": sorted(k for k in data if SENSITIVE.search(k)),
        })
    names = {p["name"] for p in presets}
    missing = sorted({p["parent"] for p in presets if p["parent"] and p["parent"] not in names})
    for p in presets:
        p["parent_available_in_archive"] = not p["parent"] or p["parent"] in names
    dupes = sorted(sorted(v) for v in groups.values() if len(v) > 1)
    return {
        "summary": {
            "total_json_presets": len(presets),
            "by_section": dict(collections.Counter(p["section"] for p in presets)),
            "presets_with_unresolved_parent": sum(not p["parent_available_in_archive"] for p in presets),
            "missing_unique_parent_names": len(missing),
            "exact_explicit_override_duplicate_groups": len(dupes),
            "invalid_json_filenames": invalid,
        },
        "missing_parents": missing, "duplicate_groups": dupes,
        "presets": sorted(presets, key=lambda p: p["name"].casefold()),
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit sanitized JSON report")
    args = parser.parse_args()
    try:
        r = audit(args.source)
    except (OSError, ValueError, tarfile.TarError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        s = r["summary"]
        print(f"Presets: {s['total_json_presets']} ({s['by_section']})")
        print(f"Unresolved parents: {s['presets_with_unresolved_parent']} / {s['missing_unique_parent_names']} unique")
        print(f"Duplicate parent/override groups: {s['exact_explicit_override_duplicate_groups']}")
        for names in r["duplicate_groups"]:
            print("  " + " == ".join(names))
        print("Missing parent names:")
        for parent in r["missing_parents"]:
            print("  - " + parent)
    return 0

if __name__ == "__main__":
    sys.exit(main())
