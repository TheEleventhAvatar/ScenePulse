"""Provider-agnostic LLM interface for Text-to-Three.js.

The LLM produces TextSceneSpec data (structured JSON), never raw executable
JavaScript. All provider-specific code lives behind this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class SceneGenerationError(Exception):
    """Raised when the LLM fails to produce a valid scene spec."""


@dataclass
class LLMResult:
    """A validated TextSceneSpec produced by an LLM provider."""

    spec: dict[str, Any]
    raw_output: str = ""
    provider: str = "unknown"
    warnings: list[str] = field(default_factory=list)


class LLMProvider(ABC):
    """Base class for all LLM providers.

    Subclasses implement `generate_scene` and `patch_scene`. The base class
    provides `generate_scene_spec` which validates the output with the
    deterministic validator.
    """

    name: str = "base"

    @abstractmethod
    def generate_scene(self, prompt: str) -> dict[str, Any]:
        """Generate a TextSceneSpec dict from a natural-language prompt.

        Must return a dict that passes `validate_text_scene_spec.validate_spec`.
        """

    @abstractmethod
    def patch_scene(self, spec: dict[str, Any], instruction: str) -> dict[str, Any]:
        """Patch an existing TextSceneSpec with a natural-language instruction.

        Must return a dict that passes `validate_text_scene_spec.validate_spec`.
        """

    def generate_scene_spec(self, prompt: str) -> LLMResult:
        """Generate and validate a scene spec from a prompt."""
        from text2threejs.spec.validate_text_scene_spec import validate_spec

        spec = self.generate_scene(prompt)
        errors, warnings = validate_spec(spec)
        if errors:
            raise SceneGenerationError(
                f"LLM produced invalid spec: {'; '.join(errors)}"
            )
        return LLMResult(
            spec=spec,
            provider=self.name,
            warnings=list(warnings),
        )

    def patch_scene_spec(self, spec: dict[str, Any], instruction: str) -> LLMResult:
        """Patch and validate an existing scene spec."""
        from text2threejs.spec.validate_text_scene_spec import validate_spec

        patched = self.patch_scene(spec, instruction)
        errors, warnings = validate_spec(patched)
        if errors:
            raise SceneGenerationError(
                f"LLM produced invalid patched spec: {'; '.join(errors)}"
            )
        return LLMResult(
            spec=patched,
            provider=self.name,
            warnings=list(warnings),
        )