"""Text-to-Three.js pipeline — a fork extension of img2threejs.

This package implements a structured, staged Text-to-Three.js pipeline that
converts natural-language prompts into validated TextSceneSpec JSON, then into
editable Three.js scenes. It is deliberately separate from the original
image-to-3D pipeline in `forge/` so the two can evolve independently.

Phase 2 (current): TextSceneSpec schema + deterministic validator.
"""

__version__ = "0.1.0"