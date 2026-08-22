"""TextSceneSpec — a structured intermediate representation for Text-to-Three.js.

This schema is deliberately adapted from the existing `ObjectSculptSpec` used by
the image-to-3D pipeline in `forge/`, but is a **separate** schema for scene
composition. It represents a full Three.js scene (objects, hierarchy, geometry,
materials, lights, camera, environment, animation, interactions) rather than a
single sculpted object.

The schema is deterministic and validated by `validate_text_scene_spec.py`.
The LLM generates the spec; Python code validates it. The LLM is never asked to
perform mechanical validation.
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

SCENE_SCHEMA_VERSION: Final[str] = "1.0"

# ---------------------------------------------------------------------------
# Valid enum values
# ---------------------------------------------------------------------------

VALID_OBJECT_TYPES: Final[frozenset[str]] = frozenset({
    "box", "sphere", "ellipsoid", "cylinder", "cone", "capsule", "torus",
    "plane", "ring", "circle", "tube", "lathe", "extrude", "curve-sweep",
    "ground-blade", "instanced-cluster", "group", "text", "sprite", "points",
    "line",
})

VALID_LIGHT_TYPES: Final[frozenset[str]] = frozenset({
    "ambient", "directional", "point", "spot", "hemisphere", "rect-area",
})

VALID_CAMERA_TYPES: Final[frozenset[str]] = frozenset({
    "perspective", "orthographic",
})

VALID_ANIMATION_PROPERTIES: Final[frozenset[str]] = frozenset({
    "position", "position.x", "position.y", "position.z",
    "rotation", "rotation.x", "rotation.y", "rotation.z",
    "scale", "scale.x", "scale.y", "scale.z",
    "opacity", "material.color", "material.emissive",
    "material.emissiveIntensity", "material.roughness", "material.metalness",
    "material.opacity", "visible",
})

ANIMATION_EASINGS: Final[frozenset[str]] = frozenset({
    "linear", "easeIn", "easeOut", "easeInOut",
    "easeInQuad", "easeOutQuad", "easeInOutQuad",
    "easeInCubic", "easeOutCubic", "easeInOutCubic",
    "easeInSine", "easeOutSine", "easeInOutSine",
    "easeInExpo", "easeOutExpo", "easeInOutExpo",
    "easeInBack", "easeOutBack", "easeInOutBack",
    "easeInElastic", "easeOutElastic", "easeInOutElastic",
    "easeInBounce", "easeOutBounce", "easeInOutBounce",
})

VALID_TEXTURE_WRAPPINGS: Final[frozenset[str]] = frozenset({
    "repeat", "clamp", "mirror",
})

VALID_TEXTURE_FILTERS: Final[frozenset[str]] = frozenset({
    "nearest", "linear", "mipmap",
})

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_BACKGROUND: Final[str] = "#0a0a12"
DEFAULT_FOG_COLOR: Final[str] = "#0a0a12"
DEFAULT_AMBIENT_INTENSITY: Final[float] = 0.4
DEFAULT_CAMERA_FOV: Final[float] = 50.0
DEFAULT_CAMERA_NEAR: Final[float] = 0.1
DEFAULT_CAMERA_FAR: Final[float] = 1000.0
DEFAULT_CAMERA_POSITION: Final[tuple[float, float, float]] = (0.0, 2.0, 8.0)
DEFAULT_CAMERA_TARGET: Final[tuple[float, float, float]] = (0.0, 0.0, 0.0)
DEFAULT_OBJECT_POSITION: Final[tuple[float, float, float]] = (0.0, 0.0, 0.0)
DEFAULT_OBJECT_ROTATION: Final[tuple[float, float, float]] = (0.0, 0.0, 0.0)
DEFAULT_OBJECT_SCALE: Final[tuple[float, float, float]] = (1.0, 1.0, 1.0)
DEFAULT_MATERIAL_COLOR: Final[str] = "#8a7a5f"
DEFAULT_MATERIAL_ROUGHNESS: Final[float] = 0.7
DEFAULT_MATERIAL_METALNESS: Final[float] = 0.0
DEFAULT_LIGHT_INTENSITY: Final[float] = 1.0
DEFAULT_LIGHT_COLOR: Final[str] = "#ffffff"
DEFAULT_ANIMATION_DURATION: Final[float] = 1.0
DEFAULT_ANIMATION_EASING: Final[str] = "linear"

# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------


def is_number(value: Any) -> bool:
    """True for int/float (not bool)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_vec3(value: Any) -> bool:
    """True for a list/tuple of exactly 3 numbers."""
    return (
        isinstance(value, (list, tuple))
        and len(value) == 3
        and all(is_number(item) for item in value)
    )


def is_color(value: Any) -> bool:
    """True for #RGB or #RRGGBB hex strings."""
    if not isinstance(value, str):
        return False
    return value.startswith("#") and len(value) in {4, 7}


def is_unit_interval(value: Any) -> bool:
    return is_number(value) and 0.0 <= float(value) <= 1.0