"""Focused tests for the LLM interface and deterministic mock provider.

Covers:
  - mock provider determinism and fallback behavior
  - every demo prompt produces a *validated* TextSceneSpec
  - natural-language patch semantics (rotation / speed / camera / materials)
  - patches never destroy unrelated scene properties
  - the browser export payload is complete and valid

The existing validator tests live in ``test_text_scene_spec.py``; this module
does not duplicate them.
"""

from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from text2threejs.llm import MockLLM, SceneGenerationError  # noqa: E402
from text2threejs.llm.demo_prompts import DEMO_PROMPTS  # noqa: E402
from text2threejs.llm.export_demo_specs import build_export_payload  # noqa: E402
from text2threejs.spec.validate_text_scene_spec import validate_spec  # noqa: E402


class TestMockGeneration(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLM()

    def test_provider_name(self):
        self.assertEqual(self.llm.name, "mock")

    def test_generate_is_deterministic(self):
        first = self.llm.generate_scene("Create a cinematic product reveal for a watch")
        second = self.llm.generate_scene("Create a cinematic product reveal for a watch")
        self.assertEqual(first, second)

    def test_all_demo_prompts_validate(self):
        for key, prompt in DEMO_PROMPTS.items():
            with self.subTest(demo=key):
                result = self.llm.generate_scene_spec(prompt)
                errors, _ = validate_spec(result.spec)
                self.assertEqual(errors, [])
                self.assertEqual(result.provider, "mock")

    def test_unknown_prompt_falls_back_to_flagship(self):
        fallback = self.llm.generate_scene("something completely unheard of xyzzy")
        known = self.llm.generate_scene("cinematic product reveal")
        self.assertEqual(fallback, known)

    def test_keyword_routing(self):
        cyber = self.llm.generate_scene("neon cyberpunk city")
        hud = self.llm.generate_scene("futuristic hud holographic display")
        luxury = self.llm.generate_scene("luxury perfume bottle advertisement")
        self.assertNotEqual(cyber["scene"]["name"], hud["scene"]["name"])
        self.assertNotEqual(cyber["scene"]["name"], luxury["scene"]["name"])

    def test_specs_are_deep_copies(self):
        first = self.llm.generate_scene("watch product reveal")
        first["scene"]["name"] = "MUTATED"
        second = self.llm.generate_scene("watch product reveal")
        self.assertNotEqual(second["scene"]["name"], "MUTATED")


class TestMockPatching(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLM()
        self.base = self.llm.generate_scene(DEMO_PROMPTS["cinematic-product-reveal"])

    def test_patch_rotation_adds_animation(self):
        spec = copy.deepcopy(self.base)
        spec["animations"] = [
            a for a in spec.get("animations", [])
            if "rotation" not in a.get("property", "")
        ]
        patched = self.llm.patch_scene(spec, "make the watch rotate 360 degrees")
        rotation_anims = [
            a for a in patched["animations"]
            if "rotation" in a.get("property", "")
        ]
        self.assertEqual(len(rotation_anims), 1)
        self.assertAlmostEqual(rotation_anims[0]["to"], math.pi * 2, places=4)

    def test_patch_rotation_updates_existing(self):
        spec = copy.deepcopy(self.base)
        target_id = spec["animations"][0]["object"]
        patched = self.llm.patch_scene(spec, f"rotate the {target_id} fully around")
        matching = [
            a for a in patched["animations"]
            if a["object"] == target_id and "rotation" in a["property"]
        ]
        self.assertTrue(matching, "expected an updated rotation animation")
        self.assertTrue(
            any(math.isclose(a["to"], math.pi * 2, rel_tol=1e-5) for a in matching)
        )

    def test_patch_speed_scales_durations(self):
        spec = copy.deepcopy(self.base)
        original = [a["duration"] for a in spec["animations"]]
        patched = self.llm.patch_scene(spec, "slow the rotation down")
        scaled = [a["duration"] for a in patched["animations"]]
        for new, old in zip(scaled, original):
            self.assertAlmostEqual(new, old * 2.0)

    def test_patch_camera_closer(self):
        spec = copy.deepcopy(self.base)
        before = list(spec["camera"]["position"])
        target = spec["camera"].get("target", [0, 0, 0])
        patched = self.llm.patch_scene(spec, "move the camera closer to the watch")
        after = patched["camera"]["position"]
        self.assertLess(math.dist(after, target), math.dist(before, target))

    def test_patch_material_glossy_black(self):
        spec = copy.deepcopy(self.base)
        patched = self.llm.patch_scene(spec, "make the pedestal glossy black")
        mat = patched["materials"][0]
        self.assertEqual(mat["color"], "#0a0a0a")
        self.assertAlmostEqual(mat["roughness"], 0.05)
        self.assertAlmostEqual(mat["metalness"], 0.9)

    def test_patched_spec_validates(self):
        spec = copy.deepcopy(self.base)
        for instruction in (
            "rotate continuously",
            "slow down and move the camera closer",
            "make it glossy black",
        ):
            with self.subTest(instruction=instruction):
                patched = self.llm.patch_scene(spec, instruction)
                errors, _ = validate_spec(patched)
                self.assertEqual(errors, [])
                spec = patched

    def test_patch_preserves_unrelated_properties(self):
        """An edit must never silently destroy unrelated scene state."""
        snapshot = copy.deepcopy(self.base)
        patched = self.llm.patch_scene(copy.deepcopy(self.base), "make it glossy black")

        # Objects, lights, camera untouched by a material-only edit.
        self.assertEqual(patched["objects"], snapshot["objects"])
        self.assertEqual(patched["lights"], snapshot["lights"])
        self.assertEqual(patched["camera"], snapshot["camera"])
        self.assertEqual(patched["animations"], snapshot["animations"])
        # Materials keep their identity — only surface properties change.
        self.assertEqual(
            [m["id"] for m in patched["materials"]],
            [m["id"] for m in snapshot["materials"]],
        )

    def test_patch_scene_spec_returns_validated_result(self):
        result = self.llm.patch_scene_spec(copy.deepcopy(self.base), "rotate 360 degrees")
        self.assertEqual(result.provider, "mock")
        errors, _ = validate_spec(result.spec)
        self.assertEqual(errors, [])

    def test_patch_never_raises_on_empty_spec(self):
        minimal = {
            "schemaVersion": "1.0",
            "scene": {"name": "Empty"},
            "objects": [],
            "materials": [],
            "lights": [],
            "animations": [],
        }
        errors, _ = validate_spec(minimal)
        self.assertEqual(errors, [])
        patched = self.llm.patch_scene(minimal, "rotate everything fast")
        errors, _ = validate_spec(patched)
        self.assertEqual(errors, [])


class TestExportPayload(unittest.TestCase):
    def test_payload_contains_all_demos(self):
        payload = build_export_payload()
        self.assertEqual(set(payload.keys()), set(DEMO_PROMPTS.keys()))

    def test_payload_entries_are_valid_and_shaped(self):
        payload = build_export_payload()
        for key, entry in payload.items():
            with self.subTest(demo=key):
                self.assertEqual(entry["prompt"], DEMO_PROMPTS[key])
                self.assertEqual(entry["provider"], "mock")
                errors, _ = validate_spec(entry["spec"])
                self.assertEqual(errors, [])

    def test_payload_is_json_serializable(self):
        payload = build_export_payload()
        decoded = json.loads(json.dumps(payload))
        self.assertEqual(decoded, payload)


class TestValidationGuardrail(unittest.TestCase):
    """Invalid provider output must raise, never pass through silently."""

    def test_invalid_output_raises(self):
        class BadProvider(MockLLM):
            name = "bad"

            def generate_scene(self, prompt):
                return {"schemaVersion": "999", "scene": {}}

        with self.assertRaises(SceneGenerationError):
            BadProvider().generate_scene_spec("anything")


if __name__ == "__main__":
    unittest.main()