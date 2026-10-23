#!/usr/bin/env python3
"""Read-only Bambu Studio filament preset inheritance inspector.

Accepts tar/tgz snapshots of user and system filament definitions. No writes to
Bambu Studio or to source archives. Output contains selected technical settings.
This is a *provisional analytical resolver*, not a preset exporter.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path, PurePosixPath
import tarfile

IDENTITY = {"name", "inherits", "from", "version", "type", "setting_id",
            "filament_settings_id", "instantiation", "include"}
FIELDS = ["filament_type", "filament_vendor", "nozzle_temperature",
          "nozzle_temperature_initial_layer", "filament_flow_ratio",
          "filament_max_volumetric_speed", "fan_min_speed", "fan_max_speed",
          "additional_cooling_fan_speed", "textured_plate_temp",
          "textured_plate_temp_initial_layer", "compatible_printers"]


def load(source: Path) -> dict:
    result = {}
    with tarfile.open(source, "r:*") as archive:
        for entry in archive:
            parts = PurePosixPath(entry.name).parts
            if (not entry.isfile() or "filament" not in parts
                    or not entry.name.endswith(".json") or entry.size > 1048576
                    or ".." in parts):
                continue
            stream = archive.extractfile(entry)
            if stream is None:
                continue
            try:
                doc = json.load(stream)
            except (UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(doc, dict) or not doc.get("name"):
                continue
            if doc["name"] in result:
                raise ValueError("Duplicate name in archive: " + doc["name"])
            result[doc["name"]] = doc
    return result


def overlay(parent: dict, child: dict) -> dict:
    """Apply explicit child overrides, retaining inherited slots for 'nil'."""
    merged = dict(parent)
    for key, value in child.items():
        if key in IDENTITY:
            continue
        inherited = merged.get(key)
        if isinstance(value, list) and isinstance(inherited, list):
            new = list(inherited)
            for position, item in enumerate(value):
                if position >= len(new):
                    new.append(None if item == "nil" else item)
                elif item != "nil":
                    new[position] = item
            merged[key] = new
        elif isinstance(value, list):
            merged[key] = [None if x == "nil" else x for x in value]
        else:
            merged[key] = value
    return merged


def resolve(definitions: dict) -> tuple[dict, list]:
    cache, missing, pending = {}, [], set()

    def one(name):
        if name in cache:
            return cache[name]
        if name in pending:
            raise ValueError("Inheritance cycle: " + name)
        pending.add(name)
        doc = definitions[name]
        parent = doc.get("inherits")
        base = {}
        if parent:
            if parent not in definitions:
                missing.append((name, parent))
            else:
                base = one(parent)
        result = overlay(base, doc)
        pending.remove(name)
        cache[name] = result
        return result

    for name in definitions:
        one(name)
    return cache, missing


def variant(value, index):
    if not isinstance(value, list):
        return value
    if index < len(value):
        return value[index]
    return value[0] if len(value) == 1 else None


def review(user: dict, resolved: dict) -> dict:
    records = []
    for name, doc in sorted(user.items()):
        values = resolved[name]
        records.append({
            "name": name,
            "inherits": doc.get("inherits"),
            "include_templates": doc.get("include", []),
            "explicit_override_keys": sorted(set(doc) - IDENTITY),
            "standard": {key: variant(values.get(key), 0) for key in FIELDS},
            "high_flow": {key: variant(values.get(key), 1) for key in FIELDS},
        })
    return {"presets": records}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--user", type=Path, required=True)
    p.add_argument("--system", type=Path, required=True)
    p.add_argument("--output", type=Path, help="Local JSON report destination")
    args = p.parse_args()
    user, system = load(args.user), load(args.system)
    overlaps = set(user) & set(system)
    if overlaps:
        p.error("Ambiguous user/system name(s): " + ", ".join(sorted(overlaps)))
    resolved, missing = resolve({**system, **user})
    result = review(user, resolved)
    result["summary"] = {
        "user_presets": len(user), "system_definitions": len(system),
        "missing_named_parent_links": len(missing),
        "note": "Provisional: include templates and Bambu Studio runtime rules require verification",
    }
    result["unresolved_parent_links"] = missing
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
