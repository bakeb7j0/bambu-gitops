"""Read-only Bambu Studio JSON preset archive conformance.

Checks *document-level* round trips: JSON decoding and re-encoding preserve
all values, types, Unicode, per-variant arrays, and embedded G-code bytes.
It deliberately does NOT claim slicer import/export or inheritance equivalence.

Only aggregate statistics are printed. Files, names, G-code and raw values
are never written to disk or included in report output.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

KIND = ("filament", "process", "printer", "system")
MAX_ENTRY = 8 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_FILES = 12000

class ArchiveError(ValueError):
    pass

def _members(path):
    """Yield (archive-relative path, raw bytes) without extracting to disk."""
    total = count = 0
    def check(name, size):
        nonlocal total, count
        parts = PurePosixPath(name).parts
        if not parts or name.startswith("/") or ".." in parts:
            raise ArchiveError("Unsafe archive path")
        if size > MAX_ENTRY or size < 0:
            raise ArchiveError("Archive member exceeds size limit")
        count += 1
        total += size
        if count > MAX_FILES or total > MAX_TOTAL:
            raise ArchiveError("Archive resource limit exceeded")
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                check(info.filename, info.file_size)
                with archive.open(info) as stream:
                    data = stream.read(MAX_ENTRY + 1)
                if len(data) != info.file_size:
                    raise ArchiveError("Archive member size mismatch")
                yield info.filename, data
    elif tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            for member in archive:
                if not member.isfile() or not member.name.lower().endswith(".json"):
                    continue
                check(member.name, member.size)
                stream = archive.extractfile(member)
                if stream is None:
                    raise ArchiveError("Unreadable archive entry")
                data = stream.read(MAX_ENTRY + 1)
                if len(data) != member.size:
                    raise ArchiveError("Archive member size mismatch")
                yield member.name, data
    else:
        raise ArchiveError("Not a supported ZIP or TAR archive")

def audit(path: Path, kind: str) -> dict:
    if kind not in KIND:
        raise ValueError("Unsupported preset kind")
    counts = {"json_documents": 0, "roundtrip_verified": 0, "parse_errors": 0,
              "documents_without_name": 0, "with_inherits": 0,
              "with_variant_arrays": 0, "with_gcode": 0,
              "duplicate_names": 0}
    names = set()
    for _, raw in _members(Path(path)):
        counts["json_documents"] += 1
        try:
            source = json.loads(raw.decode("utf-8"))
            if not isinstance(source, dict):
                raise ValueError("Document root is not an object")
            # do not print or write individual source data
            canonical = json.dumps(source, ensure_ascii=False, separators=(",", ":"))
            restored = json.loads(canonical)
            if type(source) is not type(restored) or source != restored:
                raise ValueError("JSON round trip changed document")
            counts["roundtrip_verified"] += 1
            name = source.get("name")
            if not isinstance(name, str) or not name:
                counts["documents_without_name"] += 1
            elif name in names:
                counts["duplicate_names"] += 1
            else:
                names.add(name)
            if source.get("inherits"):
                counts["with_inherits"] += 1
            if any(isinstance(v, list) and len(v) > 1 for v in source.values()):
                counts["with_variant_arrays"] += 1
            if any("gcode" in key.lower() and isinstance(v, (str, list)) for key,v in source.items()):
                counts["with_gcode"] += 1
        except (UnicodeError, json.JSONDecodeError, ValueError, TypeError, OverflowError):
            counts["parse_errors"] += 1
    return {"kind": kind, "format": "Bambu Studio JSON archive",
            "scope": "JSON semantic round-trip only; NOT slicer import compatibility",
            "ok": counts["json_documents"] > 0 and counts["parse_errors"] == 0,
            "counts": counts}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=KIND)
    parser.add_argument("archive", type=Path, help="Local ZIP, .tar, .tgz; never uploaded")
    args = parser.parse_args(argv)
    try:
        result = audit(args.archive, args.kind)
    except (OSError, tarfile.TarError, zipfile.BadZipFile, ArchiveError) as error:
        print(json.dumps({"ok": False, "kind": args.kind,
                          "error": type(error).__name__ + ": invalid/unreadable archive"}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
