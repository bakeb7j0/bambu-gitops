"""Version 0.1 reference configuration validation. Never touches printers or presets."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"
KINDS = ("printer", "process", "filament")
SENSITIVE = {"machine_start_gcode", "machine_end_gcode", "change_filament_gcode",
             "bed_exclude_area", "nozzle_diameter", "nozzle_type", "printable_area",
             "machine_max_acceleration_x", "machine_max_acceleration_y",
             "nozzle_temperature_range_high", "nozzle_temperature_range_low"}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    path: str
    message: str

    def to_dict(self):
        return asdict(self)


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _schema(name):
    return _load_json(SCHEMA_DIR / name)


def _schema_findings(data, schema_file, path):
    validator = Draft202012Validator(_schema(schema_file))
    result = []
    for error in sorted(validator.iter_errors(data), key=lambda e: (str(list(e.absolute_path)), e.message)):
        loc = ".".join(map(str, error.absolute_path)) or "<root>"
        result.append(Finding("SCHEMA_INVALID", "error", f"{path}:{loc}", error.message))
    return result


def validate_repository(root: Path) -> list[Finding]:
    """Read a synthetic/curated desired-state repo and report deterministic findings."""
    root = Path(root)
    findings: list[Finding] = []
    manifest_path = root / "bambu-gitops.json"
    try:
        manifest = _load_json(manifest_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [Finding("MANIFEST_UNREADABLE", "error", "bambu-gitops.json", str(exc))]
    findings += _schema_findings(manifest, "config-v0.1.schema.json", "bambu-gitops.json")
    if findings:
        return findings

    by_id: dict[str, tuple[str, dict]] = {}
    for kind in KINDS:
        folder = root / "profiles" / kind
        for file in sorted(folder.glob("*.json")):
            try:
                doc = _load_json(file)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                findings.append(Finding("PROFILE_UNREADABLE", "error", str(file.relative_to(root)), str(exc)))
                continue
            rel = file.relative_to(root).as_posix()
            issues = _schema_findings(doc, "profile-v0.1.schema.json", rel)
            findings.extend(issues)
            if issues:
                continue
            if doc["kind"] != kind:
                findings.append(Finding("PROFILE_WRONG_DIRECTORY", "error", rel, f"kind={doc['kind']} but directory={kind}"))
            if doc["id"] in by_id:
                findings.append(Finding("DUPLICATE_PROFILE_ID", "error", rel, f"Also declared in {by_id[doc['id']][0]}"))
            else:
                by_id[doc["id"]] = (rel, doc)

    active = []
    for kind in KINDS:
        for id_ in manifest["profiles"][kind]:
            if id_ not in by_id:
                findings.append(Finding("PROFILE_NOT_FOUND", "error", f"bambu-gitops.json:profiles.{kind}", id_))
            elif by_id[id_][1]["kind"] != kind:
                findings.append(Finding("PROFILE_KIND_MISMATCH", "error", f"bambu-gitops.json:profiles.{kind}", id_))
            else:
                active.append(id_)

    for id_, (rel, doc) in sorted(by_id.items()):
        parent = doc.get("inherits")
        if parent and parent not in by_id:
            findings.append(Finding("PARENT_NOT_FOUND", "error", rel, parent))
        elif parent and by_id[parent][1]["kind"] != doc["kind"]:
            findings.append(Finding("PARENT_KIND_MISMATCH", "error", rel, parent))
        for key in sorted(set(doc["settings"]) & SENSITIVE):
            findings.append(Finding("SAFETY_REVIEW_REQUIRED", "warning", f"{rel}:settings.{key}",
                                    "Machine-sensitive override needs explicit review"))
        if doc.get("nozzle_diameter_mm") and doc["nozzle_diameter_mm"] != manifest["hardware"]["nozzle"]["diameter_mm"] and id_ in active:
            findings.append(Finding("NOZZLE_INCOMPATIBLE", "error", rel, "Active profile nozzle diameter differs from installed hardware"))
        limit = manifest["hardware"].get("capabilities", {}).get("validated_mvs_mm3_s")
        mvs = doc["settings"].get("max_volumetric_speed_mm3_s")
        if id_ in active and limit is not None and isinstance(mvs, (int, float)) and mvs > limit:
            findings.append(Finding("UNVALIDATED_FLOW", "warning", rel, f"{mvs} exceeds declared validated MVS {limit}"))

    for id_ in sorted(by_id):
        visited, here = set(), id_
        while here in by_id and here not in visited:
            visited.add(here)
            here = by_id[here][1].get("inherits")
            if not here:
                break
        if here in visited and here:
            findings.append(Finding("INHERITANCE_CYCLE", "error", by_id[id_][0], f"cycle includes {here}"))

    for idx, cal in enumerate(manifest.get("calibrations", [])):
        rel = f"bambu-gitops.json:calibrations.{idx}"
        if cal["filament_id"] not in by_id or by_id[cal["filament_id"]][1]["kind"] != "filament":
            findings.append(Finding("CALIBRATION_FILAMENT_UNKNOWN", "error", rel, cal["filament_id"]))
        if cal["nozzle_mm"] != manifest["hardware"]["nozzle"]["diameter_mm"]:
            findings.append(Finding("CALIBRATION_NOZZLE_MISMATCH", "warning", rel, "Calibration measured using a different nozzle"))
        if cal["status"] == "verified_applied":
            findings.append(Finding("APPLIED_STATUS_REQUIRES_EVIDENCE", "warning", rel, "Validate recorded runtime evidence outside schema"))
    return sorted(findings, key=lambda f: (f.path, f.code, f.message))


def report(root: Path):
    findings = validate_repository(root)
    return {"contract_version": "0.1", "ok": not any(f.severity == "error" for f in findings),
            "findings": [f.to_dict() for f in findings]}
