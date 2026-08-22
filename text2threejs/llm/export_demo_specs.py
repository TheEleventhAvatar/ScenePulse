"""Export deterministic demo TextSceneSpecs to JSON for the browser frontend.

The Python MockLLM provider is the single source of truth for demo scenes.
This script runs every registered demo prompt through the provider *and* the
deterministic validator, then writes the validated specs to
``text2threejs/frontend/demo_specs.json`` where the browser app fetches them.

Usage::

    python -m text2threejs.llm.export_demo_specs

No API key required — the mock provider is fully deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .demo_prompts import DEMO_PROMPTS
from .mock import MockLLM

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "frontend" / "demo_specs.json"


def build_export_payload() -> dict[str, Any]:
    """Generate and validate every demo scene, returning the export payload."""
    llm = MockLLM()
    payload: dict[str, Any] = {}
    for key, prompt in DEMO_PROMPTS.items():
        result = llm.generate_scene_spec(prompt)
        payload[key] = {
            "prompt": prompt,
            "provider": result.provider,
            "spec": result.spec,
        }
    return payload


def export_demo_specs(output_path: str | Path | None = None) -> Path:
    """Write the validated demo specs to disk and return the output path."""
    path = Path(output_path) if output_path else DEFAULT_OUTPUT
    payload = build_export_payload()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    written = export_demo_specs()
    print(f"Wrote {len(DEMO_PROMPTS)} validated demo specs to {written}")