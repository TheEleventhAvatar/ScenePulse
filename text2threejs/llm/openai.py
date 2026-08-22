"""OpenAI LLM provider for Text-to-Three.js.

Implements the provider-agnostic ``LLMProvider`` interface using the OpenAI
Chat Completions API. Uses only the Python standard library (``urllib``) so
the project has no third-party dependencies.

The model is asked to return a TextSceneSpec JSON document. Output is checked
by the deterministic validator in ``text2threejs.spec.validate_text_scene_spec``
via the base class; invalid output triggers a bounded repair round-trip where
the validation errors are fed back to the model.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .base import LLMProvider, SceneGenerationError
from .config import get_openai_api_key, get_openai_model

_API_URL = "https://api.openai.com/v1/chat/completions"
_MAX_REPAIR_ROUNDS = 2
_REQUEST_TIMEOUT_SECONDS = 120.0

_SYSTEM_PROMPT = """\
You are a scene generator for a Three.js pipeline. You convert natural-language
scene descriptions into a single JSON document conforming to the TextSceneSpec
schema version "1.0". Respond with ONLY the JSON document - no prose, no code
fences, no commentary.

Top-level fields:
- "schemaVersion": must be exactly "1.0".
- "scene": object with "name" (non-empty string), optional "description",
  optional "background" (#RRGGBB color), optional "units" string,
  optional "up" one of x/y/z/-x/-y/-z, optional "fog" {type: "fog"|"fog-exp2",
  color, near, far, density}.
- "environment": optional object with "background" color, "toneMapping"
  (none|linear|reinhard|cineon|aces|agx|neutral|custom),
  "toneMappingExposure" number, "shadowMapEnabled" bool,
  "shadowMapType" (basic|pcf|pcf-soft|variance).
- "camera": optional object with "type" (perspective|orthographic), "fov",
  "near", "far" numbers, "position" [x,y,z], "target" [x,y,z].
- "objects": REQUIRED array. Each object: "id" (unique non-empty string),
  optional "name", "type" one of: box, sphere, ellipsoid, cylinder, cone,
  capsule, torus, plane, ring, circle, tube, lathe, extrude, curve-sweep,
  ground-blade, instanced-cluster, group, text, sprite, points, line.
  Optional "parent" (id of another object), "position"/"rotation"/"scale"
  as [x,y,z] number arrays, "dimensions" {width,height,depth,radius,length}
  numbers, "material" (id referencing materials[]), "visible"/"castShadow"/
  "receiveShadow" booleans.
- "materials": optional array. Each: "id" (unique string), optional
  "shaderModel" string, "color" #RRGGBB, "roughness"/"metalness"/"opacity"
  numbers in [0,1], "transparent" bool, "emissive" #RRGGBB,
  "emissiveIntensity" number, "doubleSided"/"wireframe"/"flatShading" bools,
  "texture" (id referencing textures[]), plus numeric clearcoat,
  clearcoatRoughness, transmission, ior, sheen, iridescence, anisotropy,
  specularIntensity, envMapIntensity.
- "textures": optional array. Each: "id" (unique string), optional "url",
  "color" #RRGGBB, "repeat"/"offset" [u,v], "rotation" number, "wrapS"/"wrapT"
  (repeat|clamp|mirror), "minFilter"/"magFilter" (nearest|linear|mipmap),
  "anisotropy" number, "colorSpace" string.
- "lights": optional array. Each: "id" (unique string), "type" one of ambient,
  directional, point, spot, hemisphere, rect-area; "color" #RRGGBB,
  "intensity" number, "position"/"target" [x,y,z], numeric distance, decay,
  angle, penumbra, shadowMapSize, shadowBias, shadowNormalBias;
  "castShadow"/"visible" booleans.
- "animations": optional array. Each: "id" (unique string), "object" (must be
  an id from objects[]), "property" one of: position, position.x/y/z,
  rotation, rotation.x/y/z, scale, scale.x/y/z, opacity, material.color,
  material.emissive, material.emissiveIntensity, material.roughness,
  material.metalness, material.opacity, visible. Required "from" and "to"
  values (numbers, or hex color strings for material.color/material.emissive),
  "duration" > 0 seconds, "easing" one of: linear, easeIn, easeOut, easeInOut,
  easeInQuad, easeOutQuad, easeInOutQuad, easeInCubic, easeOutCubic,
  easeInOutCubic, easeInSine, easeOutSine, easeInOutSine, easeInExpo,
  easeOutExpo, easeInOutExpo, easeInBack, easeOutBack, easeInOutBack,
  easeInElastic, easeOutElastic, easeInOutElastic, easeInBounce, easeOutBounce,
  easeInOutBounce. Optional "delay" number, "loop"/"yoyo" booleans.
- "interactions": optional array of {object (valid id), type (string)}.
- "constraints": optional array of {object (valid id), type (string)}.
- "effects": optional array of {type (string)}.
- "metadata": optional object with "sourcePrompt", "generatedBy",
  "generatedAt" strings and "notes" array.

Rules:
1. Every animation/interaction/constraint "object" value MUST match an id in
   objects[]. Every object "material" MUST match an id in materials[]. Every
   material "texture" MUST match an id in textures[].
2. All colors are "#RGB" or "#RRGGBB" hex strings.
3. Design complete, visually appealing scenes: ground planes or backdrops when
   appropriate, key/fill/rim lighting, tasteful materials, and at least one
   animation unless the prompt asks for a still scene.
4. Keep coordinates sane: objects roughly within [-10, 10]; camera positioned
   to frame the subject.
"""


class OpenAIProvider(LLMProvider):
    """LLM provider backed by the OpenAI Chat Completions API."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or get_openai_api_key()
        if not self._api_key:
            raise SceneGenerationError(
                "OpenAI API key not configured. Set OPENAI_API_KEY in the "
                "environment or in a .env file at the repository root."
            )
        self.model = model or get_openai_model()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_scene(self, prompt: str) -> dict[str, Any]:
        """Generate a TextSceneSpec dict from a natural-language prompt."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"""Scene description:
{prompt}"""},
        ]
        return self._complete(messages)

    def patch_scene(self, spec: dict[str, Any], instruction: str) -> dict[str, Any]:
        """Patch an existing TextSceneSpec with a natural-language instruction."""
        existing = json.dumps(spec, indent=2)
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"""Here is an existing TextSceneSpec JSON document:

{existing}

Apply this edit instruction and return the FULL updated JSON document (only the JSON):
{instruction}"""},
        ]
        return self._complete(messages)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _complete(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Run a chat completion, parse JSON, and repair on validation errors."""
        spec = self._request_json(messages)
        errors, _warnings = self._validate(spec)
        rounds = 0
        while errors and rounds < _MAX_REPAIR_ROUNDS:
            rounds += 1
            messages.append({"role": "assistant", "content": json.dumps(spec)})
            error_list = "\n".join(f"- {error}" for error in errors)
            messages.append({
                "role": "user",
                "content": f"""The JSON document failed schema validation with these errors:
{error_list}

Return the corrected FULL JSON document only.""",
            })
            spec = self._request_json(messages)
            errors, _warnings = self._validate(spec)
        if errors:
            raise SceneGenerationError(
                f"OpenAI produced invalid spec after {_MAX_REPAIR_ROUNDS} "
                f"repair rounds: {'; '.join(errors)}"
            )
        return spec

    @staticmethod
    def _validate(spec: Any) -> tuple[list[str], list[str]]:
        from text2threejs.spec.validate_text_scene_spec import validate_spec

        return validate_spec(spec)

    def _request_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }
        request = urllib.request.Request(
            _API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=_REQUEST_TIMEOUT_SECONDS
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SceneGenerationError(
                f"OpenAI API error {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise SceneGenerationError(
                f"Could not reach OpenAI API: {exc.reason}"
            ) from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise SceneGenerationError(
                f"Unexpected OpenAI response shape: {body}"
            ) from exc
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SceneGenerationError(
                f"OpenAI returned non-JSON content: {content[:200]}"
            ) from exc
        if not isinstance(parsed, dict):
            raise SceneGenerationError("OpenAI returned JSON that is not an object")
        return parsed


def main() -> None:
    """CLI entry point: generate a scene spec from a prompt argument."""
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Generate a TextSceneSpec JSON file using OpenAI."
    )
    parser.add_argument("prompt", help="Natural-language scene description")
    parser.add_argument(
        "-o", "--output", default="generated_scene.json",
        help="Output JSON path (default: generated_scene.json)",
    )
    args = parser.parse_args()

    provider = OpenAIProvider()
    result = provider.generate_scene_spec(args.prompt)
    out_path = Path(args.output)
    out_path.write_text(json.dumps(result.spec, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote validated TextSceneSpec to {out_path}")
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)


if __name__ == "__main__":
    main()