"""Contract and conformance tests with fully synthetic data."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from bambu_gitops.conformance import report

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "example"


class ConformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "example"
        shutil.copytree(FIXTURE, self.root)

    def edit(self, relative, fn):
        path = self.root / relative
        document = json.loads(path.read_text())
        fn(document)
        path.write_text(json.dumps(document, indent=2) + "\n")

    def codes(self):
        return [f["code"] for f in report(self.root)["findings"]]

    def test_valid_example_has_no_findings(self):
        self.assertEqual(report(self.root), {"contract_version": "0.1", "ok": True, "findings": []})

    def test_missing_active_profile(self):
        self.edit("bambu-gitops.json", lambda d: d["profiles"]["filament"].append("not-found"))
        self.assertIn("PROFILE_NOT_FOUND", self.codes())

    def test_duplicate_profile_identity(self):
        shutil.copyfile(self.root / "profiles/filament/pla-basic.json",
                        self.root / "profiles/filament/duplicate.json")
        self.assertIn("DUPLICATE_PROFILE_ID", self.codes())

    def test_invalid_schema(self):
        self.edit("bambu-gitops.json", lambda d: d.update(schema_version="88"))
        self.assertIn("SCHEMA_INVALID", self.codes())

    def test_wrong_nozzle(self):
        self.edit("profiles/filament/pla-basic.json", lambda d: d.update(nozzle_diameter_mm=0.6))
        self.assertIn("NOZZLE_INCOMPATIBLE", self.codes())

    def test_cycle_detected(self):
        self.edit("profiles/filament/pla-basic.json", lambda d: d.update(inherits="pla-basic"))
        self.assertIn("INHERITANCE_CYCLE", self.codes())

    def test_absent_parent(self):
        self.edit("profiles/filament/pla-basic.json", lambda d: d.update(inherits="missing-parent"))
        self.assertIn("PARENT_NOT_FOUND", self.codes())

    def test_safe_machine_override_requires_review(self):
        self.edit("profiles/printer/example-printer.json",
                  lambda d: d["settings"].update(machine_start_gcode="G28"))
        result = report(self.root)
        self.assertTrue(result["ok"])  # warning, not silently approved
        self.assertIn("SAFETY_REVIEW_REQUIRED", self.codes())

    def test_unvalidated_flow_is_warning_not_global_hardcode(self):
        self.edit("profiles/filament/pla-basic.json",
                  lambda d: d["settings"].update(max_volumetric_speed_mm3_s=29))
        result = report(self.root)
        self.assertTrue(result["ok"])
        self.assertIn("UNVALIDATED_FLOW", self.codes())

    def test_calibration_wrong_nozzle_warning(self):
        self.edit("bambu-gitops.json",
                  lambda d: d["calibrations"][0].update(nozzle_mm=0.6))
        self.assertIn("CALIBRATION_NOZZLE_MISMATCH", self.codes())

    def test_unknown_calibration_filament(self):
        self.edit("bambu-gitops.json",
                  lambda d: d["calibrations"][0].update(filament_id="other-filament"))
        self.assertIn("CALIBRATION_FILAMENT_UNKNOWN", self.codes())

    def test_explicit_status_not_assumed_to_be_applied(self):
        self.edit("bambu-gitops.json",
                  lambda d: d["calibrations"][0].update(status="verified_applied"))
        self.assertIn("APPLIED_STATUS_REQUIRES_EVIDENCE", self.codes())

    def test_parent_wrong_kind(self):
        self.edit("profiles/filament/pla-basic.json",
                  lambda d: d.update(inherits="example-process"))
        self.assertIn("PARENT_KIND_MISMATCH", self.codes())

    def test_errors_change_cli_semantics(self):
        self.edit("profiles/filament/pla-basic.json",
                  lambda d: d.update(nozzle_diameter_mm=0.8))
        self.assertFalse(report(self.root)["ok"])


if __name__ == "__main__":
    unittest.main()
