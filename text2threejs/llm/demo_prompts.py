"""Deterministic demo prompts for the Text-to-Three.js pipeline.

Each prompt maps to a deterministic TextSceneSpec via the mock provider.
These are used for demos and tests without requiring an API key.
"""

from __future__ import annotations

from typing import Any

from text2threejs.spec.factories import (
    make_animation,
    make_camera,
    make_light,
    make_material,
    make_object,
    new_scene,
)

# ---------------------------------------------------------------------------
# Demo prompt registry
# ---------------------------------------------------------------------------

DEMO_PROMPTS: dict[str, str] = {
    "cinematic-product-reveal": (
        "Create a cinematic product reveal for a futuristic watch. "
        "Put the watch on a dark reflective pedestal, use dramatic rim lighting, "
        "slowly rotate the watch, and move the camera toward it."
    ),
    "neon-cyberpunk": (
        "Create a neon cyberpunk city scene at night. "
        "Include glowing buildings, a neon sign, fog, and a flying drone."
    ),
    "abstract-motion": (
        "Create an abstract motion-graphics scene with floating geometric shapes, "
        "a gradient background, and smooth looping animations."
    ),
    "futuristic-hud": (
        "Create a futuristic UI/HUD scene with a holographic display, "
        "glowing wireframe elements, and a rotating central core."
    ),
    "luxury-product": (
        "Create a minimal luxury product advertisement for a perfume bottle. "
        "Use a clean studio background, soft lighting, and a slow camera orbit."
    ),
}

# ---------------------------------------------------------------------------
# Deterministic scene builders
# ---------------------------------------------------------------------------


def _cinematic_product_reveal() -> dict[str, Any]:
    """Futuristic watch on a reflective pedestal with dramatic lighting."""
    spec = new_scene(
        "Cinematic Product Reveal",
        description="A futuristic watch on a dark reflective pedestal with dramatic rim lighting.",
        background="#050508",
    )

    # Environment: dark, moody, with fog
    spec["environment"] = {
        "background": "#050508",
        "fog": {"type": "fog", "color": "#050508", "near": 8, "far": 25},
        "toneMapping": "aces",
        "toneMappingExposure": 1.2,
        "shadowMapEnabled": True,
        "shadowMapType": "pcf-soft",
    }

    # Camera: cinematic push-in
    spec["camera"] = make_camera(
        camera_type="perspective",
        fov=45,
        near=0.1,
        far=50,
        position=(0, 2.5, 10),
        target=(0, 1.2, 0),
    )

    # Reflective pedestal
    spec["objects"] = [
        make_object(
            "pedestal",
            object_type="cylinder",
            position=(0, 0.15, 0),
            dimensions={"radius": 1.2, "height": 0.3},
            material="mat_pedestal",
            cast_shadow=True,
            receive_shadow=True,
        ),
        make_object(
            "pedestal_top",
            object_type="cylinder",
            position=(0, 0.3, 0),
            dimensions={"radius": 0.8, "height": 0.05},
            material="mat_pedestal_top",
            cast_shadow=True,
            receive_shadow=True,
        ),
        # Watch body
        make_object(
            "watch_body",
            object_type="cylinder",
            parent="pedestal_top",
            position=(0, 0.15, 0),
            dimensions={"radius": 0.35, "height": 0.08},
            material="mat_watch_body",
            cast_shadow=True,
            receive_shadow=True,
        ),
        # Watch face
        make_object(
            "watch_face",
            object_type="cylinder",
            parent="watch_body",
            position=(0, 0.05, 0),
            dimensions={"radius": 0.3, "height": 0.01},
            material="mat_watch_face",
            cast_shadow=False,
            receive_shadow=True,
        ),
        # Watch crown
        make_object(
            "watch_crown",
            object_type="cylinder",
            parent="watch_body",
            position=(0.35, 0, 0),
            rotation=(0, 0, 1.5708),
            dimensions={"radius": 0.06, "height": 0.1},
            material="mat_watch_body",
            cast_shadow=True,
            receive_shadow=True,
        ),
        # Watch band
        make_object(
            "watch_band",
            object_type="box",
            parent="watch_body",
            position=(0, -0.1, 0),
            dimensions={"width": 0.2, "height": 0.2, "depth": 0.5},
            material="mat_band",
            cast_shadow=True,
            receive_shadow=True,
        ),
    ]

    # Materials
    spec["materials"] = [
        make_material(
            "mat_pedestal",
            color="#1a1a24",
            roughness=0.15,
            metalness=0.9,
            clearcoat=1.0,
            clearcoat_roughness=0.1,
            env_map_intensity=1.5,
        ),
        make_material(
            "mat_pedestal_top",
            color="#222233",
            roughness=0.1,
            metalness=0.95,
            clearcoat=1.0,
            clearcoat_roughness=0.05,
            env_map_intensity=1.8,
        ),
        make_material(
            "mat_watch_body",
            color="#2a2a35",
            roughness=0.2,
            metalness=0.85,
            clearcoat=0.8,
            clearcoat_roughness=0.15,
            env_map_intensity=1.2,
        ),
        make_material(
            "mat_watch_face",
            color="#0a0a12",
            roughness=0.05,
            metalness=0.3,
            emissive="#1a2a4a",
            emissive_intensity=0.3,
            clearcoat=1.0,
            clearcoat_roughness=0.05,
            env_map_intensity=1.5,
        ),
        make_material(
            "mat_band",
            color="#1a1a22",
            roughness=0.4,
            metalness=0.6,
            env_map_intensity=0.8,
        ),
    ]

    # Dramatic lighting: key, rim, fill
    spec["lights"] = [
        make_light(
            "key_light",
            light_type="directional",
            color="#fff4e0",
            intensity=2.5,
            position=(4, 6, 3),
            cast_shadow=True,
            shadow_map_size=2048,
        ),
        make_light(
            "rim_light",
            light_type="directional",
            color="#4a8aff",
            intensity=3.0,
            position=(-3, 4, -5),
            cast_shadow=False,
        ),
        make_light(
            "fill_light",
            light_type="directional",
            color="#8899bb",
            intensity=0.5,
            position=(-2, 2, 4),
            cast_shadow=False,
        ),
        make_light(
            "ambient_glow",
            light_type="ambient",
            color="#223344",
            intensity=0.3,
        ),
    ]

    # Animation: watch rotation
    spec["animations"] = [
        make_animation(
            "watch_rotate",
            object_id="watch_body",
            property_name="rotation.y",
            from_value=0,
            to_value=6.283185,
            duration=8.0,
            easing="easeInOutCubic",
            loop=True,
        ),
    ]

    # Interactions
    spec["interactions"] = [
        {"object": "watch_body", "type": "click"},
        {"object": "pedestal", "type": "hover"},
    ]

    # Effects
    spec["effects"] = [
        {"type": "bloom", "strength": 0.6},
        {"type": "vignette"},
    ]

    return spec


def _neon_cyberpunk() -> dict[str, Any]:
    """Neon cyberpunk city scene at night."""
    spec = new_scene(
        "Neon Cyberpunk City",
        description="A neon cyberpunk city at night with glowing buildings and fog.",
        background="#050510",
    )

    spec["environment"] = {
        "background": "#050510",
        "fog": {"type": "fog-exp2", "color": "#050510", "density": 0.04},
        "toneMapping": "aces",
        "toneMappingExposure": 1.1,
        "shadowMapEnabled": True,
        "shadowMapType": "pcf-soft",
    }

    spec["camera"] = make_camera(
        camera_type="perspective",
        fov=60,
        position=(0, 3, 12),
        target=(0, 2, 0),
    )

    # Ground plane
    spec["objects"] = [
        make_object(
            "ground",
            object_type="plane",
            position=(0, 0, 0),
            dimensions={"width": 20, "height": 20},
            material="mat_ground",
            receive_shadow=True,
        ),
        # Buildings
        make_object(
            "building_1",
            object_type="box",
            position=(-3, 2, -2),
            dimensions={"width": 2, "height": 4, "depth": 2},
            material="mat_building",
            cast_shadow=True,
        ),
        make_object(
            "building_2",
            object_type="box",
            position=(2, 3, -4),
            dimensions={"width": 2, "height": 6, "depth": 2},
            material="mat_building",
            cast_shadow=True,
        ),
        make_object(
            "building_3",
            object_type="box",
            position=(-1, 1.5, -6),
            dimensions={"width": 3, "height": 3, "depth": 2},
            material="mat_building",
            cast_shadow=True,
        ),
        make_object(
            "building_4",
            object_type="box",
            position=(4, 2.5, -1),
            dimensions={"width": 1.5, "height": 5, "depth": 1.5},
            material="mat_building",
            cast_shadow=True,
        ),
        # Neon sign
        make_object(
            "neon_sign",
            object_type="box",
            position=(-3, 4.5, -1.5),
            dimensions={"width": 1.5, "height": 0.3, "depth": 0.1},
            material="mat_neon",
            cast_shadow=False,
        ),
        # Drone
        make_object(
            "drone",
            object_type="sphere",
            position=(0, 5, 2),
            dimensions={"radius": 0.2},
            material="mat_drone",
            cast_shadow=False,
        ),
    ]

    spec["materials"] = [
        make_material(
            "mat_ground",
            color="#0a0a18",
            roughness=0.8,
            metalness=0.1,
        ),
        make_material(
            "mat_building",
            color="#111122",
            roughness=0.6,
            metalness=0.3,
            emissive="#0a0a22",
            emissive_intensity=0.2,
        ),
        make_material(
            "mat_neon",
            color="#ff00ff",
            roughness=0.2,
            metalness=0.1,
            emissive="#ff00ff",
            emissive_intensity=3.0,
        ),
        make_material(
            "mat_drone",
            color="#00ffaa",
            roughness=0.3,
            metalness=0.5,
            emissive="#00ffaa",
            emissive_intensity=1.5,
        ),
    ]

    spec["lights"] = [
        make_light(
            "moon",
            light_type="directional",
            color="#4466aa",
            intensity=0.5,
            position=(5, 10, 5),
            cast_shadow=True,
        ),
        make_light(
            "neon_glow",
            light_type="point",
            color="#ff00ff",
            intensity=2.0,
            position=(-3, 4.5, -1.5),
            distance=8,
        ),
        make_light(
            "cyan_glow",
            light_type="point",
            color="#00ffff",
            intensity=1.5,
            position=(2, 3, -4),
            distance=6,
        ),
    ]

    spec["animations"] = [
        make_animation(
            "drone_fly",
            object_id="drone",
            property_name="position",
            from_value=[0, 5, 2],
            to_value=[3, 6, -2],
            duration=4.0,
            easing="easeInOutSine",
            loop=True,
            yoyo=True,
        ),
        make_animation(
            "neon_pulse",
            object_id="neon_sign",
            property_name="material.emissiveIntensity",
            from_value=2.0,
            to_value=4.0,
            duration=1.5,
            easing="easeInOutSine",
            loop=True,
            yoyo=True,
        ),
    ]

    spec["effects"] = [
        {"type": "bloom", "strength": 1.2},
        {"type": "chromatic-aberration"},
    ]

    return spec


def _abstract_motion() -> dict[str, Any]:
    """Abstract motion-graphics scene with floating geometric shapes."""
    spec = new_scene(
        "Abstract Motion",
        description="Floating geometric shapes with smooth looping animations.",
        background="#0a0a1a",
    )

    spec["environment"] = {
        "background": "#0a0a1a",
        "toneMapping": "aces",
        "toneMappingExposure": 1.0,
        "shadowMapEnabled": False,
    }

    spec["camera"] = make_camera(
        camera_type="perspective",
        fov=55,
        position=(0, 2, 10),
        target=(0, 0, 0),
    )

    spec["objects"] = [
        make_object(
            "sphere_1",
            object_type="sphere",
            position=(-2, 1, 0),
            dimensions={"radius": 0.6},
            material="mat_gradient",
        ),
        make_object(
            "torus_1",
            object_type="torus",
            position=(2, 0.5, 0),
            dimensions={"radius": 0.5},
            material="mat_glow",
        ),
        make_object(
            "box_1",
            object_type="box",
            position=(0, -1, -1),
            dimensions={"width": 0.8, "height": 0.8, "depth": 0.8},
            material="mat_wire",
        ),
        make_object(
            "cone_1",
            object_type="cone",
            position=(-1, -0.5, 2),
            dimensions={"radius": 0.4, "height": 0.8},
            material="mat_gradient",
        ),
        make_object(
            "ring_1",
            object_type="ring",
            position=(1, 1.5, -1),
            dimensions={"radius": 0.4},
            material="mat_glow",
        ),
    ]

    spec["materials"] = [
        make_material(
            "mat_gradient",
            color="#ff6b6b",
            roughness=0.3,
            metalness=0.2,
            emissive="#ff6b6b",
            emissive_intensity=0.5,
        ),
        make_material(
            "mat_glow",
            color="#4ecdc4",
            roughness=0.2,
            metalness=0.1,
            emissive="#4ecdc4",
            emissive_intensity=1.5,
        ),
        make_material(
            "mat_wire",
            color="#ffe66d",
            roughness=0.4,
            metalness=0.3,
            emissive="#ffe66d",
            emissive_intensity=0.8,
            wireframe=True,
        ),
    ]

    spec["lights"] = [
        make_light(
            "ambient",
            light_type="ambient",
            color="#ffffff",
            intensity=0.4,
        ),
        make_light(
            "key",
            light_type="directional",
            color="#ffffff",
            intensity=1.5,
            position=(3, 5, 4),
        ),
    ]

    spec["animations"] = [
        make_animation(
            "sphere_bounce",
            object_id="sphere_1",
            property_name="position.y",
            from_value=1,
            to_value=2.5,
            duration=2.0,
            easing="easeInOutBounce",
            loop=True,
            yoyo=True,
        ),
        make_animation(
            "torus_spin",
            object_id="torus_1",
            property_name="rotation.x",
            from_value=0,
            to_value=6.283185,
            duration=3.0,
            easing="linear",
            loop=True,
        ),
        make_animation(
            "box_float",
            object_id="box_1",
            property_name="position.y",
            from_value=-1,
            to_value=0.5,
            duration=2.5,
            easing="easeInOutSine",
            loop=True,
            yoyo=True,
        ),
        make_animation(
            "cone_rotate",
            object_id="cone_1",
            property_name="rotation.y",
            from_value=0,
            to_value=6.283185,
            duration=4.0,
            easing="linear",
            loop=True,
        ),
        make_animation(
            "ring_pulse",
            object_id="ring_1",
            property_name="scale",
            from_value=[1, 1, 1],
            to_value=[1.5, 1.5, 1.5],
            duration=1.5,
            easing="easeInOutQuad",
            loop=True,
            yoyo=True,
        ),
    ]

    spec["effects"] = [
        {"type": "bloom", "strength": 0.8},
    ]

    return spec


def _futuristic_hud() -> dict[str, Any]:
    """Futuristic UI/HUD scene with holographic display."""
    spec = new_scene(
        "Futuristic HUD",
        description="A holographic display with glowing wireframe elements and a rotating core.",
        background="#000510",
    )

    spec["environment"] = {
        "background": "#000510",
        "toneMapping": "aces",
        "toneMappingExposure": 1.0,
        "shadowMapEnabled": False,
    }

    spec["camera"] = make_camera(
        camera_type="perspective",
        fov=50,
        position=(0, 1, 8),
        target=(0, 0, 0),
    )

    spec["objects"] = [
        make_object(
            "core",
            object_type="sphere",
            position=(0, 0, 0),
            dimensions={"radius": 0.5},
            material="mat_core",
        ),
        make_object(
            "ring_outer",
            object_type="torus",
            position=(0, 0, 0),
            dimensions={"radius": 1.2},
            material="mat_hologram",
        ),
        make_object(
            "ring_inner",
            object_type="torus",
            position=(0, 0, 0),
            rotation=(1.5708, 0, 0),
            dimensions={"radius": 0.8},
            material="mat_hologram",
        ),
        make_object(
            "hud_panel",
            object_type="plane",
            position=(2, 1, -1),
            rotation=(0, -0.5, 0),
            dimensions={"width": 1.5, "height": 1},
            material="mat_panel",
        ),
        make_object(
            "hud_panel_2",
            object_type="plane",
            position=(-2, 0.5, -0.5),
            rotation=(0, 0.5, 0),
            dimensions={"width": 1, "height": 0.8},
            material="mat_panel",
        ),
    ]

    spec["materials"] = [
        make_material(
            "mat_core",
            color="#00ccff",
            roughness=0.1,
            metalness=0.5,
            emissive="#00ccff",
            emissive_intensity=2.0,
        ),
        make_material(
            "mat_hologram",
            color="#00ff88",
            roughness=0.2,
            metalness=0.1,
            emissive="#00ff88",
            emissive_intensity=1.5,
            transparent=True,
            opacity=0.6,
        ),
        make_material(
            "mat_panel",
            color="#001122",
            roughness=0.3,
            metalness=0.2,
            emissive="#00aaff",
            emissive_intensity=0.8,
            transparent=True,
            opacity=0.7,
        ),
    ]

    spec["lights"] = [
        make_light(
            "ambient",
            light_type="ambient",
            color="#001122",
            intensity=0.5,
        ),
        make_light(
            "core_light",
            light_type="point",
            color="#00ccff",
            intensity=2.0,
            position=(0, 0, 0),
            distance=6,
        ),
    ]

    spec["animations"] = [
        make_animation(
            "core_rotate",
            object_id="core",
            property_name="rotation.y",
            from_value=0,
            to_value=6.283185,
            duration=4.0,
            easing="linear",
            loop=True,
        ),
        make_animation(
            "ring_outer_spin",
            object_id="ring_outer",
            property_name="rotation.z",
            from_value=0,
            to_value=6.283185,
            duration=6.0,
            easing="linear",
            loop=True,
        ),
        make_animation(
            "ring_inner_spin",
            object_id="ring_inner",
            property_name="rotation.y",
            from_value=0,
            to_value=6.283185,
            duration=3.0,
            easing="linear",
            loop=True,
        ),
        make_animation(
            "panel_pulse",
            object_id="hud_panel",
            property_name="material.opacity",
            from_value=0.4,
            to_value=0.8,
            duration=2.0,
            easing="easeInOutSine",
            loop=True,
            yoyo=True,
        ),
    ]

    spec["effects"] = [
        {"type": "bloom", "strength": 1.5},
        {"type": "scanlines"},
    ]

    return spec


def _luxury_product() -> dict[str, Any]:
    """Minimal luxury product advertisement for a perfume bottle."""
    spec = new_scene(
        "Luxury Perfume",
        description="A minimal luxury perfume bottle with soft studio lighting.",
        background="#f5f5f0",
    )

    spec["environment"] = {
        "background": "#f5f5f0",
        "toneMapping": "aces",
        "toneMappingExposure": 1.0,
        "shadowMapEnabled": True,
        "shadowMapType": "pcf-soft",
    }

    spec["camera"] = make_camera(
        camera_type="perspective",
        fov=40,
        position=(0, 2, 8),
        target=(0, 1, 0),
    )

    spec["objects"] = [
        make_object(
            "bottle_body",
            object_type="cylinder",
            position=(0, 0.8, 0),
            dimensions={"radius": 0.5, "height": 1.2},
            material="mat_glass",
            cast_shadow=True,
        ),
        make_object(
            "bottle_cap",
            object_type="cylinder",
            position=(0, 1.6, 0),
            dimensions={"radius": 0.2, "height": 0.4},
            material="mat_gold",
            cast_shadow=True,
        ),
        make_object(
            "bottle_label",
            object_type="cylinder",
            position=(0, 0.8, 0),
            dimensions={"radius": 0.52, "height": 0.3},
            material="mat_label",
            cast_shadow=False,
        ),
        make_object(
            "table",
            object_type="box",
            position=(0, -0.1, 0),
            dimensions={"width": 6, "height": 0.2, "depth": 4},
            material="mat_table",
            receive_shadow=True,
        ),
    ]

    spec["materials"] = [
        make_material(
            "mat_glass",
            color="#ddeeff",
            roughness=0.05,
            metalness=0.0,
            transmission=0.9,
            ior=1.5,
            clearcoat=1.0,
            clearcoat_roughness=0.05,
            transparent=True,
            opacity=0.3,
        ),
        make_material(
            "mat_gold",
            color="#d4af37",
            roughness=0.15,
            metalness=1.0,
            clearcoat=0.5,
            clearcoat_roughness=0.2,
        ),
        make_material(
            "mat_label",
            color="#f5f5f0",
            roughness=0.6,
            metalness=0.0,
        ),
        make_material(
            "mat_table",
            color="#e8e4dc",
            roughness=0.3,
            metalness=0.1,
        ),
    ]

    spec["lights"] = [
        make_light(
            "soft_key",
            light_type="directional",
            color="#fff8f0",
            intensity=1.5,
            position=(3, 5, 4),
            cast_shadow=True,
        ),
        make_light(
            "fill",
            light_type="directional",
            color="#e8f0ff",
            intensity=0.5,
            position=(-3, 2, 3),
        ),
        make_light(
            "rim",
            light_type="directional",
            color="#ffffff",
            intensity=0.8,
            position=(0, 3, -4),
        ),
    ]

    spec["animations"] = [
        make_animation(
            "bottle_rotate",
            object_id="bottle_body",
            property_name="rotation.y",
            from_value=0,
            to_value=6.283185,
            duration=10.0,
            easing="linear",
            loop=True,
        ),
    ]

    spec["effects"] = [
        {"type": "bloom", "strength": 0.3},
    ]

    return spec


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

DEMO_SCENE_BUILDERS: dict[str, Any] = {
    "cinematic-product-reveal": _cinematic_product_reveal,
    "neon-cyberpunk": _neon_cyberpunk,
    "abstract-motion": _abstract_motion,
    "futuristic-hud": _futuristic_hud,
    "luxury-product": _luxury_product,
}