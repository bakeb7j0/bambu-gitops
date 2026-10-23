"""Tests for read-only override semantics (run with python3 -m unittest discover -s tests)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from resolve import overlay, resolve, variant


class TestInheritance(unittest.TestCase):
    def test_nil_inherits_only_matching_variant(self):
        parent = {"filament_flow_ratio": ["0.98", "0.985"]}
        child = {"filament_flow_ratio": ["1.02", "nil"]}
        self.assertEqual(overlay(parent, child)["filament_flow_ratio"], ["1.02", "0.985"])

    def test_hf_override_preserves_standard(self):
        parent = {"filament_max_volumetric_speed": ["21", "29"]}
        self.assertEqual(
            overlay(parent, {"filament_max_volumetric_speed": ["nil", "12"]})[
                "filament_max_volumetric_speed"
            ], ["21", "12"]
        )

    def test_nested_inheritance(self):
        docs = {
            "base": {"name": "base", "nozzle_temperature": ["220", "220"]},
            "child": {"name": "child", "inherits": "base", "nozzle_temperature": ["230", "nil"]},
        }
        values, missing = resolve(docs)
        self.assertEqual(missing, [])
        self.assertEqual(values["child"]["nozzle_temperature"], ["230", "220"])

    def test_unknown_parent_is_reported(self):
        _, missing = resolve({"child": {"name": "child", "inherits": "nope"}})
        self.assertEqual(missing, [("child", "nope")])

    def test_cycle_is_rejected(self):
        docs = {"a": {"inherits": "b"}, "b": {"inherits": "a"}}
        with self.assertRaises(ValueError):
            resolve(docs)

    def test_single_variant_fallback_is_explicit(self):
        self.assertEqual(variant(["220"], 1), "220")
        self.assertIsNone(variant(["220", None], 2))


if __name__ == "__main__":
    unittest.main()
