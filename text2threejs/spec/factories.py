"""Factory helpers for building a valid TextSceneSpec from scratch.

These helpers mirror the `make_*` pattern used by `forge/stage2_spec/new_sculpt_spec.py`
but for the TextSceneSpec schema. They produce schema-valid blocks that pass
`validate_text_scene_spec.validate_spec()`.
"""

from __future__ import annotations

from typing import Any

from .text_scene_spec import (
    DEFAULT_ANIMATION_DURATION,
    DEFAULT_ANIMATION_EASING,
    DEFAULT_BACKGROUND,
    DEFAULT_CAMERA_FAR,
    DEFAULT_CAMERA_FOV,
    DEFAULT_CAMERA_NEAR,
    DEFAULT_CAMERA_POSITION,
    DEFAULT_CAMERA_TARGET,
    DEFAULT_LIGHT_COLOR,
    DEFAULT_LIGHT_INTENSITY,
    DEFAULT_MATERIAL_COLOR,
    DEFAULT_MATERIAL_METALNESS,
    DEFAULT_MATERIAL_ROUGHNESS,
    DEFAULT_OBJECT_POSITION,
    DEFAULT_OBJECT_ROTATION,
    DEFAULT_OBJECT_SCALE,
    SCENE_SCHEMA_VERSION,
)


def make_scene(
    name: str,
    *,
    description: str = "",
    background: str = DEFAULT_BACKGROUND,
    fog: dict[str, Any] | None = None,
    environment: dict[str, Any] | None = None,
    units: str = "meters",
    up: str = "y",
) -> dict[str, Any]:
    """Create a scene metadata block."""
    return {
        "name": name,
        "description": description,
        "background": background,
        "fog": fog,
        "environment": environment,
        "units": units,
        "up": up,
    }


def make_object(
    object_id: str,
    *,
    name: str | None = None,
    object_type: str = "box",
    parent: str | None = None,
    position: tuple[float, float, float] = DEFAULT_OBJECT_POSITION,
    rotation: tuple[float, float, float] = DEFAULT_OBJECT_ROTATION,
    scale: tuple[float, float, float] = DEFAULT_OBJECT_SCALE,
    dimensions: dict[str, Any] | None = None,
    material: str | None = None,
    visible: bool = True,
    cast_shadow: bool = True,
    receive_shadow: bool = True,
    geometry: dict[str, Any] | None = None,
    interactions: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create an object block."""
    return {
        "id": object_id,
        "name": name or object_id,
        "type": object_type,
        "parent": parent,
        "position": list(position),
        "rotation": list(rotation),
        "scale": list(scale),
        "dimensions": dimensions,
        "material": material,
        "visible": visible,
        "castShadow": cast_shadow,
        "receiveShadow": receive_shadow,
        "geometry": geometry,
        "interactions": interactions or [],
        "tags": tags or [],
    }


def make_material(
    material_id: str,
    *,
    color: str = DEFAULT_MATERIAL_COLOR,
    roughness: float = DEFAULT_MATERIAL_ROUGHNESS,
    metalness: float = DEFAULT_MATERIAL_METALNESS,
    opacity: float = 1.0,
    transparent: bool = False,
    emissive: str = "#000000",
    emissive_intensity: float = 0.0,
    double_sided: bool = False,
    wireframe: bool = False,
    flat_shading: bool = False,
    texture: dict[str, Any] | None = None,
    clearcoat: float = 0.0,
    clearcoat_roughness: float = 0.25,
    transmission: float = 0.0,
    ior: float = 1.5,
    sheen: float = 0.0,
    iridescence: float = 0.0,
    anisotropy: float = 0.0,
    specular_intensity: float = 1.0,
    env_map_intensity: float = 0.8,
    shader_model: str = "physical",
) -> dict[str, Any]:
    """Create a material block."""
    return {
        "id": material_id,
        "shaderModel": shader_model,
        "color": color,
        "roughness": roughness,
        "metalness": metalness,
        "opacity": opacity,
        "transparent": transparent,
        "emissive": emissive,
        "emissiveIntensity": emissive_intensity,
        "doubleSided": double_sided,
        "wireframe": wireframe,
        "flatShading": flat_shading,
        "texture": texture,
        "clearcoat": clearcoat,
        "clearcoatRoughness": clearcoat_roughness,
        "transmission": transmission,
        "ior": ior,
        "sheen": sheen,
        "iridescence": iridescence,
        "anisotropy": anisotropy,
        "specularIntensity": specular_intensity,
        "envMapIntensity": env_map_intensity,
    }


def make_texture(
    texture_id: str,
    *,
    url: str | None = None,
    color: str | None = None,
    repeat: tuple[float, float] = (1.0, 1.0),
    offset: tuple[float, float] = (0.0, 0.0),
    rotation: float = 0.0,
    wrap_s: str = "repeat",
    wrap_t: str = "repeat",
    min_filter: str = "linear",
    mag_filter: str = "linear",
    anisotropy: int = 1,
    color_space: str = "srgb",
) -> dict[str, Any]:
    """Create a texture block."""
    return {
        "id": texture_id,
        "url": url,
        "color": color,
        "repeat": list(repeat),
        "offset": list(offset),
        "rotation": rotation,
        "wrapS": wrap_s,
        "wrapT": wrap_t,
        "minFilter": min_filter,
        "magFilter": mag_filter,
        "anisotropy": anisotropy,
        "colorSpace": color_space,
    }


def make_light(
    light_id: str,
    *,
    light_type: str = "point",
    color: str = DEFAULT_LIGHT_COLOR,
    intensity: float = DEFAULT_LIGHT_INTENSITY,
    position: tuple[float, float, float] = (0.0, 3.0, 0.0),
    target: tuple[float, float, float] | None = None,
    distance: float = 0.0,
    decay: float = 2.0,
    angle: float = 0.5,
    penumbra: float = 0.0,
    cast_shadow: bool = True,
    shadow_map_size: int = 1024,
    shadow_bias: float = -0.0001,
    shadow_normal_bias: float = 0.0,
    visible: bool = True,
) -> dict[str, Any]:
    """Create a light block."""
    return {
        "id": light_id,
        "type": light_type,
        "color": color,
        "intensity": intensity,
        "position": list(position),
        "target": list(target) if target is not None else None,
        "distance": distance,
        "decay": decay,
        "angle": angle,
        "penumbra": penumbra,
        "castShadow": cast_shadow,
        "shadowMapSize": shadow_map_size,
        "shadowBias": shadow_bias,
        "shadowNormalBias": shadow_normal_bias,
        "visible": visible,
    }


def make_camera(
    *,
    camera_type: str = "perspective",
    fov: float = DEFAULT_CAMERA_FOV,
    near: float = DEFAULT_CAMERA_NEAR,
    far: float = DEFAULT_CAMERA_FAR,
    position: tuple[float, float, float] = DEFAULT_CAMERA_POSITION,
    target: tuple[float, float, float] = DEFAULT_CAMERA_TARGET,
    ortho_size: float = 5.0,
    ortho_left: float = -5.0,
    ortho_right: float = 5.0,
    ortho_top: float = 5.0,
    ortho_bottom: float = -5.0,
) -> dict[str, Any]:
    """Create a camera block."""
    return {
        "type": camera_type,
        "fov": fov,
        "near": near,
        "far": far,
        "position": list(position),
        "target": list(target),
        "orthoSize": ortho_size,
        "orthoLeft": ortho_left,
        "orthoRight": ortho_right,
        "orthoTop": ortho_top,
        "orthoBottom": ortho_bottom,
    }


def make_animation(
    animation_id: str,
    *,
    object_id: str,
    property_name: str,
    from_value: Any,
    to_value: Any,
    duration: float = DEFAULT_ANIMATION_DURATION,
    easing: str = DEFAULT_ANIMATION_EASING,
    delay: float = 0.0,
    loop: bool = True,
    yoyo: bool = False,
) -> dict[str, Any]:
    """Create an animation keyframe block."""
    return {
        "id": animation_id,
        "object": object_id,
        "property": property_name,
        "from": from_value,
        "to": to_value,
        "duration": duration,
        "easing": easing,
        "delay": delay,
        "loop": loop,
        "yoyo": yoyo,
    }


def new_scene(
    name: str,
    *,
    description: str = "",
    background: str = DEFAULT_BACKGROUND,
    units: str = "meters",
) -> dict[str, Any]:
    """Create a minimal, valid TextSceneSpec with sensible defaults.

    The returned spec passes `validate_text_scene_spec.validate_spec()`.
    """
    return {
        "schemaVersion": SCENE_SCHEMA_VERSION,
        "scene": make_scene(name, description=description, background=background, units=units),
        "objects": [],
        "materials": [],
        "textures": [],
        "lights": [],
        "camera": make_camera(),
        "environment": {
            "background": background,
            "fog": None,
            "toneMapping": "aces",
            "toneMappingExposure": 1.0,
            "shadowMapEnabled": True,
            "shadowMapType": "pcf-soft",
        },
        "animations": [],
        "interactions": [],
        "constraints": [],
        "effects": [],
        "metadata": {
            "sourcePrompt": "",
            "generatedBy": "text2threejs",
            "generatedAt": "",
            "notes": [],
        },
    }