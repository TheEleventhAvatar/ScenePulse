"""Deterministic mock LLM provider for Text-to-Three.js.

Returns pre-built TextSceneSpec documents for known demo prompts.
This allows the application to run without an API key.
"""

from __future__ import annotations

import copy
from typing import Any

from .base import LLMProvider
from .demo_prompts import DEMO_SCENE_BUILDERS


class MockLLM(LLMProvider):
    """Deterministic mock provider that returns pre-built scene specs.

    Matches prompts to known demo scenes by keyword. Unknown prompts
    fall back to the cinematic product reveal scene.
    """

    name = "mock"

    def __init__(self) -> None:
        self._prompt_to_key: list[tuple[str, str]] = [
            ("watch", "cinematic-product-reveal"),
            ("product reveal", "cinematic-product-reveal"),
            ("cinematic", "cinematic-product-reveal"),
            ("cyberpunk", "neon-cyberpunk"),
            ("neon", "neon-cyberpunk"),
            ("abstract", "abstract-motion"),
            ("motion", "abstract-motion"),
            ("hud", "futuristic-hud"),
            ("holographic", "futuristic-hud"),
            ("luxury", "luxury-product"),
            ("perfume", "luxury-product"),
            ("bottle", "luxury-product"),
        ]

    def _match_key(self, prompt: str) -> str:
        lowered = prompt.lower()
        for keyword, key in self._prompt_to_key:
            if keyword in lowered:
                return key
        return "cinematic-product-reveal"

    def generate_scene(self, prompt: str) -> dict[str, Any]:
        """Return a deterministic TextSceneSpec for a prompt."""
        key = self._match_key(prompt)
        builder = DEMO_SCENE_BUILDERS[key]
        return copy.deepcopy(builder())

    def patch_scene(self, spec: dict[str, Any], instruction: str) -> dict[str, Any]:
        """Patch an existing scene spec with a natural-language instruction.

        This is a deterministic mock that handles common edit patterns.
        """
        patched = copy.deepcopy(spec)
        lowered = instruction.lower()

        if "rotate" in lowered or "spin" in lowered:
            self._patch_rotation(patched, lowered)

        if "slow" in lowered or "slower" in lowered:
            self._patch_speed(patched, 2.0)
        elif "fast" in lowered or "faster" in lowered:
            self._patch_speed(patched, 0.5)

        if "camera closer" in lowered or "move camera" in lowered:
            self._patch_camera_distance(patched, 0.7)
        elif "camera farther" in lowered or "camera further" in lowered:
            self._patch_camera_distance(patched, 1.3)

        # Specific surface phrases win over generic color words.
        material_edited = False
        if "glossy black" in lowered or "shiny black" in lowered:
            self._patch_material_color(patched, "#0a0a0a", roughness=0.05, metalness=0.9)
            material_edited = True
        elif "glossy" in lowered or "shiny" in lowered or "reflective" in lowered:
            self._patch_material_roughness(patched, 0.1)
            material_edited = True
        elif "matte" in lowered:
            self._patch_material_roughness(patched, 0.8)
            material_edited = True

        if not material_edited:
            if "red" in lowered:
                self._patch_material_color(patched, "#ff0000")
            elif "blue" in lowered:
                self._patch_material_color(patched, "#0000ff")
            elif "green" in lowered:
                self._patch_material_color(patched, "#00ff00")
            elif "gold" in lowered:
                self._patch_material_color(patched, "#d4af37", metalness=1.0)
            elif "black" in lowered:
                self._patch_material_color(patched, "#111111")

        return patched

    def _patch_rotation(self, spec: dict[str, Any], instruction: str) -> None:
        """Add or update a rotation animation on the first object."""
        objects = spec.get("objects", [])
        if not objects:
            return
        target_id = objects[0].get("id", "object")
        animations = spec.get("animations", [])
        for anim in animations:
            if anim.get("object") == target_id and "rotation" in anim.get("property", ""):
                if "360" in instruction or "full" in instruction:
                    anim["to"] = 6.283185
                return
        animations.append({
            "id": f"{target_id}_rotate",
            "object": target_id,
            "property": "rotation.y",
            "from": 0,
            "to": 6.283185,
            "duration": 4.0,
            "easing": "linear",
            "loop": True,
            "yoyo": False,
        })
        spec["animations"] = animations

    def _patch_speed(self, spec: dict[str, Any], factor: float) -> None:
        """Scale animation durations by a factor."""
        for anim in spec.get("animations", []):
            if isinstance(anim.get("duration"), (int, float)):
                anim["duration"] = float(anim["duration"]) * factor

    def _patch_camera_distance(self, spec: dict[str, Any], factor: float) -> None:
        """Scale camera distance from target."""
        camera = spec.get("camera", {})
        position = camera.get("position")
        target = camera.get("target", [0, 0, 0])
        if isinstance(position, list) and len(position) == 3:
            dx = position[0] - target[0]
            dy = position[1] - target[1]
            dz = position[2] - target[2]
            camera["position"] = [
                target[0] + dx * factor,
                target[1] + dy * factor,
                target[2] + dz * factor,
            ]

    def _patch_material_color(
        self,
        spec: dict[str, Any],
        color: str,
        roughness: float | None = None,
        metalness: float | None = None,
    ) -> None:
        """Update the first material's color."""
        materials = spec.get("materials", [])
        if not materials:
            return
        material = materials[0]
        material["color"] = color
        if roughness is not None:
            material["roughness"] = roughness
        if metalness is not None:
            material["metalness"] = metalness

    def _patch_material_roughness(self, spec: dict[str, Any], roughness: float) -> None:
        """Update the first material's roughness."""
        materials = spec.get("materials", [])
        if materials:
            materials[0]["roughness"] = roughness