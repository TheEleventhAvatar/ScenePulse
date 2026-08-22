"""Deterministic validation for TextSceneSpec.

This module validates a TextSceneSpec JSON document. It is the text-to-3D
counterpart of `forge/stage2_spec/validate_sculpt_spec.py` from the original
image-to-3D pipeline, but is a **separate** validator for the TextSceneSpec
schema.

The LLM generates the spec; this module validates it. The LLM is never asked
to perform mechanical validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .text_scene_spec import (
    ANIMATION_EASINGS,
    SCENE_SCHEMA_VERSION,
    VALID_ANIMATION_PROPERTIES,
    VALID_CAMERA_TYPES,
    VALID_LIGHT_TYPES,
    VALID_OBJECT_TYPES,
    VALID_TEXTURE_FILTERS,
    VALID_TEXTURE_WRAPPINGS,
    is_color,
    is_number,
    is_unit_interval,
    is_vec3,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_spec(spec: Any) -> tuple[list[str], list[str]]:
    """Validate a TextSceneSpec document.

    Returns a tuple of ``(errors, warnings)``. An empty ``errors`` list means
    the spec is structurally valid. Warnings are non-fatal quality hints.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(spec, dict):
        return [f"spec must be a JSON object, got {type(spec).__name__}"], []

    _validate_schema_version(spec, errors)
    _validate_scene_block(spec, errors)
    _validate_environment_block(spec, errors)
    _validate_camera_block(spec, errors)

    object_ids = _validate_objects(spec, errors)
    material_ids = _validate_materials(spec, errors)
    texture_ids = _validate_textures(spec, errors)
    _validate_lights(spec, errors)
    _validate_animations(spec, object_ids, errors)
    _validate_interactions(spec, object_ids, errors)
    _validate_constraints(spec, object_ids, errors)
    _validate_effects(spec, errors)
    _validate_metadata(spec, errors)

    _validate_material_references(spec, material_ids, errors)
    _validate_texture_references(spec, texture_ids, errors)

    return errors, warnings


def validate_spec_file(path: str | Path) -> tuple[list[str], list[str]]:
    """Load a TextSceneSpec from a JSON file and validate it."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_spec(payload)


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------


def _validate_schema_version(spec: dict[str, Any], errors: list[str]) -> None:
    version = spec.get("schemaVersion")
    if version is None:
        errors.append("missing required field: schemaVersion")
    elif not isinstance(version, str):
        errors.append("schemaVersion must be a string")
    elif version != SCENE_SCHEMA_VERSION:
        errors.append(
            f"unsupported schemaVersion {version!r}; expected {SCENE_SCHEMA_VERSION!r}"
        )


# ---------------------------------------------------------------------------
# Scene block
# ---------------------------------------------------------------------------


def _validate_scene_block(spec: dict[str, Any], errors: list[str]) -> None:
    scene = spec.get("scene")
    if scene is None:
        errors.append("missing required field: scene")
        return
    if not isinstance(scene, dict):
        errors.append("scene must be an object")
        return

    name = scene.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("scene.name must be a non-empty string")

    description = scene.get("description")
    if description is not None and not isinstance(description, str):
        errors.append("scene.description must be a string")

    background = scene.get("background")
    if background is not None and not is_color(background):
        errors.append(f"scene.background must be a #RGB or #RRGGBB color, got {background!r}")

    units = scene.get("units")
    if units is not None and not isinstance(units, str):
        errors.append("scene.units must be a string")

    up = scene.get("up")
    if up is not None and up not in {"x", "y", "z", "-x", "-y", "-z"}:
        errors.append(f"scene.up must be one of x, y, z, -x, -y, -z, got {up!r}")

    fog = scene.get("fog")
    if fog is not None:
        if not isinstance(fog, dict):
            errors.append("scene.fog must be an object")
        else:
            _validate_fog(fog, errors)

    environment = scene.get("environment")
    if environment is not None and not isinstance(environment, dict):
        errors.append("scene.environment must be an object")


def _validate_fog(fog: dict[str, Any], errors: list[str]) -> None:
    fog_type = fog.get("type")
    if fog_type not in {"fog", "fog-exp2"}:
        errors.append(f"scene.fog.type must be 'fog' or 'fog-exp2', got {fog_type!r}")
        return
    color = fog.get("color")
    if color is not None and not is_color(color):
        errors.append(f"scene.fog.color must be a #RGB or #RRGGBB color, got {color!r}")
    near = fog.get("near")
    if near is not None and not is_number(near):
        errors.append("scene.fog.near must be a number")
    far = fog.get("far")
    if far is not None and not is_number(far):
        errors.append("scene.fog.far must be a number")
    density = fog.get("density")
    if density is not None and not is_number(density):
        errors.append("scene.fog.density must be a number")


# ---------------------------------------------------------------------------
# Environment block
# ---------------------------------------------------------------------------


def _validate_environment_block(spec: dict[str, Any], errors: list[str]) -> None:
    env = spec.get("environment")
    if env is None:
        return
    if not isinstance(env, dict):
        errors.append("environment must be an object")
        return

    background = env.get("background")
    if background is not None and not is_color(background):
        errors.append(f"environment.background must be a #RGB or #RRGGBB color, got {background!r}")

    tone_mapping = env.get("toneMapping")
    if tone_mapping is not None and tone_mapping not in {
        "none", "linear", "reinhard", "cineon", "aces", "agx", "neutral", "custom",
    }:
        errors.append(f"environment.toneMapping must be a known tone mapping, got {tone_mapping!r}")

    exposure = env.get("toneMappingExposure")
    if exposure is not None and not is_number(exposure):
        errors.append("environment.toneMappingExposure must be a number")

    shadow_enabled = env.get("shadowMapEnabled")
    if shadow_enabled is not None and not isinstance(shadow_enabled, bool):
        errors.append("environment.shadowMapEnabled must be a boolean")

    shadow_type = env.get("shadowMapType")
    if shadow_type is not None and shadow_type not in {
        "basic", "pcf", "pcf-soft", "variance",
    }:
        errors.append(f"environment.shadowMapType must be a known shadow map type, got {shadow_type!r}")


# ---------------------------------------------------------------------------
# Camera block
# ---------------------------------------------------------------------------


def _validate_camera_block(spec: dict[str, Any], errors: list[str]) -> None:
    camera = spec.get("camera")
    if camera is None:
        return
    if not isinstance(camera, dict):
        errors.append("camera must be an object")
        return

    camera_type = camera.get("type")
    if camera_type is not None and camera_type not in VALID_CAMERA_TYPES:
        errors.append(
            f"camera.type must be one of {sorted(VALID_CAMERA_TYPES)}, got {camera_type!r}"
        )

    fov = camera.get("fov")
    if fov is not None and not is_number(fov):
        errors.append("camera.fov must be a number")

    near = camera.get("near")
    if near is not None and not is_number(near):
        errors.append("camera.near must be a number")

    far = camera.get("far")
    if far is not None and not is_number(far):
        errors.append("camera.far must be a number")

    position = camera.get("position")
    if position is not None and not is_vec3(position):
        errors.append("camera.position must be a [x, y, z] array of numbers")

    target = camera.get("target")
    if target is not None and not is_vec3(target):
        errors.append("camera.target must be a [x, y, z] array of numbers")


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------


def _validate_objects(spec: dict[str, Any], errors: list[str]) -> set[str]:
    objects = spec.get("objects")
    if objects is None:
        errors.append("missing required field: objects")
        return set()
    if not isinstance(objects, list):
        errors.append("objects must be an array")
        return set()

    object_ids: set[str] = set()
    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            errors.append(f"objects[{index}] must be an object")
            continue
        _validate_object(obj, index, object_ids, errors)

    return object_ids


def _validate_object(
    obj: dict[str, Any],
    index: int,
    object_ids: set[str],
    errors: list[str],
) -> None:
    prefix = f"objects[{index}]"

    object_id = obj.get("id")
    if not isinstance(object_id, str) or not object_id.strip():
        errors.append(f"{prefix}.id must be a non-empty string")
    else:
        if object_id in object_ids:
            errors.append(f"{prefix}.id {object_id!r} is a duplicate")
        object_ids.add(object_id)

    name = obj.get("name")
    if name is not None and not isinstance(name, str):
        errors.append(f"{prefix}.name must be a string")

    object_type = obj.get("type")
    if object_type is not None and object_type not in VALID_OBJECT_TYPES:
        errors.append(
            f"{prefix}.type must be one of {sorted(VALID_OBJECT_TYPES)}, got {object_type!r}"
        )

    parent = obj.get("parent")
    if parent is not None and not isinstance(parent, str):
        errors.append(f"{prefix}.parent must be a string or null")

    position = obj.get("position")
    if position is not None and not is_vec3(position):
        errors.append(f"{prefix}.position must be a [x, y, z] array of numbers")

    rotation = obj.get("rotation")
    if rotation is not None and not is_vec3(rotation):
        errors.append(f"{prefix}.rotation must be a [x, y, z] array of numbers")

    scale = obj.get("scale")
    if scale is not None and not is_vec3(scale):
        errors.append(f"{prefix}.scale must be a [x, y, z] array of numbers")

    dimensions = obj.get("dimensions")
    if dimensions is not None:
        if not isinstance(dimensions, dict):
            errors.append(f"{prefix}.dimensions must be an object")
        else:
            for dim in ("width", "height", "depth", "radius", "length"):
                value = dimensions.get(dim)
                if value is not None and not is_number(value):
                    errors.append(f"{prefix}.dimensions.{dim} must be a number")

    material = obj.get("material")
    if material is not None and not isinstance(material, str):
        errors.append(f"{prefix}.material must be a string or null")

    visible = obj.get("visible")
    if visible is not None and not isinstance(visible, bool):
        errors.append(f"{prefix}.visible must be a boolean")

    cast_shadow = obj.get("castShadow")
    if cast_shadow is not None and not isinstance(cast_shadow, bool):
        errors.append(f"{prefix}.castShadow must be a boolean")

    receive_shadow = obj.get("receiveShadow")
    if receive_shadow is not None and not isinstance(receive_shadow, bool):
        errors.append(f"{prefix}.receiveShadow must be a boolean")

    geometry = obj.get("geometry")
    if geometry is not None and not isinstance(geometry, dict):
        errors.append(f"{prefix}.geometry must be an object")

    interactions = obj.get("interactions")
    if interactions is not None and not isinstance(interactions, list):
        errors.append(f"{prefix}.interactions must be an array")

    tags = obj.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"{prefix}.tags must be an array")


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------


def _validate_materials(spec: dict[str, Any], errors: list[str]) -> set[str]:
    materials = spec.get("materials")
    if materials is None:
        return set()
    if not isinstance(materials, list):
        errors.append("materials must be an array")
        return set()

    material_ids: set[str] = set()
    for index, material in enumerate(materials):
        if not isinstance(material, dict):
            errors.append(f"materials[{index}] must be an object")
            continue
        prefix = f"materials[{index}]"

        material_id = material.get("id")
        if not isinstance(material_id, str) or not material_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        else:
            if material_id in material_ids:
                errors.append(f"{prefix}.id {material_id!r} is a duplicate")
            material_ids.add(material_id)

        shader_model = material.get("shaderModel")
        if shader_model is not None and not isinstance(shader_model, str):
            errors.append(f"{prefix}.shaderModel must be a string")

        color = material.get("color")
        if color is not None and not is_color(color):
            errors.append(f"{prefix}.color must be a #RGB or #RRGGBB color, got {color!r}")

        for field in ("roughness", "metalness", "opacity"):
            value = material.get(field)
            if value is not None and not is_unit_interval(value):
                errors.append(f"{prefix}.{field} must be a number in [0, 1]")

        transparent = material.get("transparent")
        if transparent is not None and not isinstance(transparent, bool):
            errors.append(f"{prefix}.transparent must be a boolean")

        emissive = material.get("emissive")
        if emissive is not None and not is_color(emissive):
            errors.append(f"{prefix}.emissive must be a #RGB or #RRGGBB color, got {emissive!r}")

        emissive_intensity = material.get("emissiveIntensity")
        if emissive_intensity is not None and not is_number(emissive_intensity):
            errors.append(f"{prefix}.emissiveIntensity must be a number")

        for field in ("doubleSided", "wireframe", "flatShading"):
            value = material.get(field)
            if value is not None and not isinstance(value, bool):
                errors.append(f"{prefix}.{field} must be a boolean")

        texture = material.get("texture")
        if texture is not None and not isinstance(texture, str):
            errors.append(f"{prefix}.texture must be a string or null")

        for field in (
            "clearcoat",
            "clearcoatRoughness",
            "transmission",
            "ior",
            "sheen",
            "iridescence",
            "anisotropy",
            "specularIntensity",
            "envMapIntensity",
        ):
            value = material.get(field)
            if value is not None and not is_number(value):
                errors.append(f"{prefix}.{field} must be a number")

    return material_ids


# ---------------------------------------------------------------------------
# Textures
# ---------------------------------------------------------------------------


def _validate_textures(spec: dict[str, Any], errors: list[str]) -> set[str]:
    textures = spec.get("textures")
    if textures is None:
        return set()
    if not isinstance(textures, list):
        errors.append("textures must be an array")
        return set()

    texture_ids: set[str] = set()
    for index, texture in enumerate(textures):
        if not isinstance(texture, dict):
            errors.append(f"textures[{index}] must be an object")
            continue
        prefix = f"textures[{index}]"

        texture_id = texture.get("id")
        if not isinstance(texture_id, str) or not texture_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        else:
            if texture_id in texture_ids:
                errors.append(f"{prefix}.id {texture_id!r} is a duplicate")
            texture_ids.add(texture_id)

        url = texture.get("url")
        if url is not None and not isinstance(url, str):
            errors.append(f"{prefix}.url must be a string or null")

        color = texture.get("color")
        if color is not None and not is_color(color):
            errors.append(f"{prefix}.color must be a #RGB or #RRGGBB color, got {color!r}")

        repeat = texture.get("repeat")
        if repeat is not None:
            if not isinstance(repeat, (list, tuple)) or len(repeat) != 2:
                errors.append(f"{prefix}.repeat must be a [u, v] array of 2 numbers")
            elif not all(is_number(item) for item in repeat):
                errors.append(f"{prefix}.repeat must be a [u, v] array of 2 numbers")

        offset = texture.get("offset")
        if offset is not None:
            if not isinstance(offset, (list, tuple)) or len(offset) != 2:
                errors.append(f"{prefix}.offset must be a [u, v] array of 2 numbers")
            elif not all(is_number(item) for item in offset):
                errors.append(f"{prefix}.offset must be a [u, v] array of 2 numbers")

        rotation = texture.get("rotation")
        if rotation is not None and not is_number(rotation):
            errors.append(f"{prefix}.rotation must be a number")

        wrap_s = texture.get("wrapS")
        if wrap_s is not None and wrap_s not in VALID_TEXTURE_WRAPPINGS:
            errors.append(
                f"{prefix}.wrapS must be one of {sorted(VALID_TEXTURE_WRAPPINGS)}, got {wrap_s!r}"
            )

        wrap_t = texture.get("wrapT")
        if wrap_t is not None and wrap_t not in VALID_TEXTURE_WRAPPINGS:
            errors.append(
                f"{prefix}.wrapT must be one of {sorted(VALID_TEXTURE_WRAPPINGS)}, got {wrap_t!r}"
            )

        min_filter = texture.get("minFilter")
        if min_filter is not None and min_filter not in VALID_TEXTURE_FILTERS:
            errors.append(
                f"{prefix}.minFilter must be one of {sorted(VALID_TEXTURE_FILTERS)}, got {min_filter!r}"
            )

        mag_filter = texture.get("magFilter")
        if mag_filter is not None and mag_filter not in VALID_TEXTURE_FILTERS:
            errors.append(
                f"{prefix}.magFilter must be one of {sorted(VALID_TEXTURE_FILTERS)}, got {mag_filter!r}"
            )

        anisotropy = texture.get("anisotropy")
        if anisotropy is not None and not is_number(anisotropy):
            errors.append(f"{prefix}.anisotropy must be a number")

        color_space = texture.get("colorSpace")
        if color_space is not None and not isinstance(color_space, str):
            errors.append(f"{prefix}.colorSpace must be a string")

    return texture_ids


# ---------------------------------------------------------------------------
# Lights
# ---------------------------------------------------------------------------


def _validate_lights(spec: dict[str, Any], errors: list[str]) -> None:
    lights = spec.get("lights")
    if lights is None:
        return
    if not isinstance(lights, list):
        errors.append("lights must be an array")
        return

    light_ids: set[str] = set()
    for index, light in enumerate(lights):
        if not isinstance(light, dict):
            errors.append(f"lights[{index}] must be an object")
            continue
        prefix = f"lights[{index}]"

        light_id = light.get("id")
        if not isinstance(light_id, str) or not light_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        else:
            if light_id in light_ids:
                errors.append(f"{prefix}.id {light_id!r} is a duplicate")
            light_ids.add(light_id)

        light_type = light.get("type")
        if light_type is not None and light_type not in VALID_LIGHT_TYPES:
            errors.append(
                f"{prefix}.type must be one of {sorted(VALID_LIGHT_TYPES)}, got {light_type!r}"
            )

        color = light.get("color")
        if color is not None and not is_color(color):
            errors.append(f"{prefix}.color must be a #RGB or #RRGGBB color, got {color!r}")

        intensity = light.get("intensity")
        if intensity is not None and not is_number(intensity):
            errors.append(f"{prefix}.intensity must be a number")

        position = light.get("position")
        if position is not None and not is_vec3(position):
            errors.append(f"{prefix}.position must be a [x, y, z] array of numbers")

        target = light.get("target")
        if target is not None and not is_vec3(target):
            errors.append(f"{prefix}.target must be a [x, y, z] array of numbers or null")

        for field in ("distance", "decay", "angle", "penumbra"):
            value = light.get(field)
            if value is not None and not is_number(value):
                errors.append(f"{prefix}.{field} must be a number")

        cast_shadow = light.get("castShadow")
        if cast_shadow is not None and not isinstance(cast_shadow, bool):
            errors.append(f"{prefix}.castShadow must be a boolean")

        shadow_map_size = light.get("shadowMapSize")
        if shadow_map_size is not None and not is_number(shadow_map_size):
            errors.append(f"{prefix}.shadowMapSize must be a number")

        for field in ("shadowBias", "shadowNormalBias"):
            value = light.get(field)
            if value is not None and not is_number(value):
                errors.append(f"{prefix}.{field} must be a number")

        visible = light.get("visible")
        if visible is not None and not isinstance(visible, bool):
            errors.append(f"{prefix}.visible must be a boolean")


# ---------------------------------------------------------------------------
# Animations
# ---------------------------------------------------------------------------


def _validate_animations(
    spec: dict[str, Any],
    object_ids: set[str],
    errors: list[str],
) -> None:
    animations = spec.get("animations")
    if animations is None:
        return
    if not isinstance(animations, list):
        errors.append("animations must be an array")
        return

    animation_ids: set[str] = set()
    for index, animation in enumerate(animations):
        if not isinstance(animation, dict):
            errors.append(f"animations[{index}] must be an object")
            continue
        prefix = f"animations[{index}]"

        animation_id = animation.get("id")
        if not isinstance(animation_id, str) or not animation_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        else:
            if animation_id in animation_ids:
                errors.append(f"{prefix}.id {animation_id!r} is a duplicate")
            animation_ids.add(animation_id)

        object_ref = animation.get("object")
        if object_ref is not None:
            if not isinstance(object_ref, str):
                errors.append(f"{prefix}.object must be a string")
            elif object_ids and object_ref not in object_ids:
                errors.append(f"{prefix}.object {object_ref!r} does not reference a known object")

        property_name = animation.get("property")
        if property_name is not None and property_name not in VALID_ANIMATION_PROPERTIES:
            errors.append(
                f"{prefix}.property must be one of {sorted(VALID_ANIMATION_PROPERTIES)}, "
                f"got {property_name!r}"
            )

        for field in ("from", "to"):
            if field not in animation:
                errors.append(f"{prefix}.{field} is required")

        duration = animation.get("duration")
        if duration is not None and not is_number(duration):
            errors.append(f"{prefix}.duration must be a number")
        elif duration is not None and float(duration) <= 0:
            errors.append(f"{prefix}.duration must be greater than 0")

        easing = animation.get("easing")
        if easing is not None and easing not in ANIMATION_EASINGS:
            errors.append(
                f"{prefix}.easing must be one of {sorted(ANIMATION_EASINGS)}, got {easing!r}"
            )

        delay = animation.get("delay")
        if delay is not None and not is_number(delay):
            errors.append(f"{prefix}.delay must be a number")

        for field in ("loop", "yoyo"):
            value = animation.get(field)
            if value is not None and not isinstance(value, bool):
                errors.append(f"{prefix}.{field} must be a boolean")


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------


def _validate_interactions(
    spec: dict[str, Any],
    object_ids: set[str],
    errors: list[str],
) -> None:
    interactions = spec.get("interactions")
    if interactions is None:
        return
    if not isinstance(interactions, list):
        errors.append("interactions must be an array")
        return

    for index, interaction in enumerate(interactions):
        if not isinstance(interaction, dict):
            errors.append(f"interactions[{index}] must be an object")
            continue
        prefix = f"interactions[{index}]"

        object_ref = interaction.get("object")
        if object_ref is not None:
            if not isinstance(object_ref, str):
                errors.append(f"{prefix}.object must be a string")
            elif object_ids and object_ref not in object_ids:
                errors.append(f"{prefix}.object {object_ref!r} does not reference a known object")

        interaction_type = interaction.get("type")
        if interaction_type is not None and not isinstance(interaction_type, str):
            errors.append(f"{prefix}.type must be a string")


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


def _validate_constraints(
    spec: dict[str, Any],
    object_ids: set[str],
    errors: list[str],
) -> None:
    constraints = spec.get("constraints")
    if constraints is None:
        return
    if not isinstance(constraints, list):
        errors.append("constraints must be an array")
        return

    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, dict):
            errors.append(f"constraints[{index}] must be an object")
            continue
        prefix = f"constraints[{index}]"

        object_ref = constraint.get("object")
        if object_ref is not None:
            if not isinstance(object_ref, str):
                errors.append(f"{prefix}.object must be a string")
            elif object_ids and object_ref not in object_ids:
                errors.append(f"{prefix}.object {object_ref!r} does not reference a known object")

        constraint_type = constraint.get("type")
        if constraint_type is not None and not isinstance(constraint_type, str):
            errors.append(f"{prefix}.type must be a string")


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------


def _validate_effects(spec: dict[str, Any], errors: list[str]) -> None:
    effects = spec.get("effects")
    if effects is None:
        return
    if not isinstance(effects, list):
        errors.append("effects must be an array")
        return

    for index, effect in enumerate(effects):
        if not isinstance(effect, dict):
            errors.append(f"effects[{index}] must be an object")
            continue
        prefix = f"effects[{index}]"

        effect_type = effect.get("type")
        if effect_type is not None and not isinstance(effect_type, str):
            errors.append(f"{prefix}.type must be a string")


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def _validate_metadata(spec: dict[str, Any], errors: list[str]) -> None:
    metadata = spec.get("metadata")
    if metadata is None:
        return
    if not isinstance(metadata, dict):
        errors.append("metadata must be an object")
        return

    source_prompt = metadata.get("sourcePrompt")
    if source_prompt is not None and not isinstance(source_prompt, str):
        errors.append("metadata.sourcePrompt must be a string")

    generated_by = metadata.get("generatedBy")
    if generated_by is not None and not isinstance(generated_by, str):
        errors.append("metadata.generatedBy must be a string")

    generated_at = metadata.get("generatedAt")
    if generated_at is not None and not isinstance(generated_at, str):
        errors.append("metadata.generatedAt must be a string")

    notes = metadata.get("notes")
    if notes is not None and not isinstance(notes, list):
        errors.append("metadata.notes must be an array")


# ---------------------------------------------------------------------------
# Cross-references
# ---------------------------------------------------------------------------


def _validate_material_references(
    spec: dict[str, Any],
    material_ids: set[str],
    errors: list[str],
) -> None:
    """Check that object.material references a declared material id."""
    if not material_ids:
        return
    objects = spec.get("objects")
    if not isinstance(objects, list):
        return
    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            continue
        material_ref = obj.get("material")
        if isinstance(material_ref, str) and material_ref not in material_ids:
            errors.append(
                f"objects[{index}].material {material_ref!r} does not reference a known material"
            )


def _validate_texture_references(
    spec: dict[str, Any],
    texture_ids: set[str],
    errors: list[str],
) -> None:
    """Check that material.texture references a declared texture id."""
    if not texture_ids:
        return
    materials = spec.get("materials")
    if not isinstance(materials, list):
        return
    for index, material in enumerate(materials):
        if not isinstance(material, dict):
            continue
        texture_ref = material.get("texture")
        if isinstance(texture_ref, str) and texture_ref not in texture_ids:
            errors.append(
                f"materials[{index}].texture {texture_ref!r} does not reference a known texture"
            )