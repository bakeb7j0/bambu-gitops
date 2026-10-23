"""Synthetic, no-hardware archive parsing / JSON semantic round-trip tests.

DO NOT RUN A PRINTER ON THESE SETTINGS. This suite contains deliberately
fictional data and makes no Bambu Studio import/print safety claims.
"""
from __future__ import annotations
import io
import json
import tarfile
import tempfile
from pathlib import Path
import unittest
import zipfile

from bambu_gitops.archive_compat import audit, ArchiveError

DOC = {
    "name": "SYNTHETIC DO NOT PRINT",
    "inherits": "FAKE PARENT",
    "filament_flow_ratio": ["1.02", "nil"],
    "filament_extruder_variant": ["Direct Drive Standard", "Direct Drive High Flow"],
    "machine_start_gcode": "G28 ; DUMMY – NOT SAFE TO PRINT\nG1 Z5\n",
    "print_settings_id": ["FAKE"],
    "nozzle_temperature": ["220", "nil"],
}

class ArchiveRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_zip(self, documents):
        path = self.root / "fictional.zip"
        with zipfile.ZipFile(path, "w") as z:
            for name, data in documents.items():
                z.writestr(name, data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False))
        return path

    def make_tar(self, documents):
        path = self.root / "fictional.tgz"
        with tarfile.open(path, "w:gz") as t:
            for name, data in documents.items():
                data = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
                item = tarfile.TarInfo(name)
                item.size = len(data)
                t.addfile(item, io.BytesIO(data))
        return path

    def test_zip_roundtrip_gcode_unicode_and_nil(self):
        result = audit(self.make_zip({"SYNTHETIC.json": DOC}), "printer")
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"]["roundtrip_verified"], 1)
        self.assertEqual(result["counts"]["with_gcode"], 1)
        self.assertEqual(result["counts"]["with_variant_arrays"], 1)
        self.assertEqual(result["counts"]["with_inherits"], 1)
        self.assertNotIn("G28", str(result))
        self.assertNotIn("1.02", str(result))

    def test_tar_roundtrip(self):
        result = audit(self.make_tar({"system/fake/filament/fake.json": DOC}), "system")
        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"]["json_documents"], 1)

    def test_duplicate_names_are_reported_only_as_counts(self):
        result = audit(self.make_zip({"first.json": DOC, "second.json": DOC}), "filament")
        self.assertEqual(result["counts"]["duplicate_names"], 1)
        self.assertNotIn(DOC["name"], str(result))

    def test_missing_name_is_counted(self):
        result = audit(self.make_zip({"fake.json": {"inherits": "fake"}}), "process")
        self.assertEqual(result["counts"]["documents_without_name"], 1)

    def test_malformed_json_produces_error(self):
        result = audit(self.make_zip({"fake.json": b'{"broken":'}), "filament")
        self.assertFalse(result["ok"])
        self.assertEqual(result["counts"]["parse_errors"], 1)

    def test_empty_archive_not_a_valid_preset_export(self):
        result = audit(self.make_zip({"readme.txt": b"none"}), "filament")
        self.assertFalse(result["ok"])

    def test_archive_traversal_is_rejected(self):
        with self.assertRaises(ArchiveError):
            audit(self.make_zip({"../outside.json": DOC}), "filament")

    def test_large_archive_entry_is_rejected(self):
        data = b"x" * (8 * 1024 * 1024 + 1)
        with self.assertRaises(ArchiveError):
            audit(self.make_zip({"massive.json": data}), "filament")

    def test_unexpected_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.make_zip({"a.json": DOC}), "gcode")

    def test_json_array_is_not_a_preset_document(self):
        result = audit(self.make_zip({"a.json": [1,2,3]}), "filament")
        self.assertFalse(result["ok"])

if __name__ == "__main__":
    unittest.main()
