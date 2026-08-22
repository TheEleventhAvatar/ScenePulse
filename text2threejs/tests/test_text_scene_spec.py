"""Tests for the TextSceneSpec schema and validator.

Covers:
- Schema constants (valid enums, defaults, version)
- Helper predicates (is_number, is_vec3, is_color, is_unit_interval)
- Valid spec passes validation (via factories)
- Malformed specs fail validation with appropriate error messages
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from text2threejs.spec import (  # noqa: E402
    ANIMATION_EASINGS,
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
    make_animation,
    make_camera,
    make_light,
    make_material,
    make_object,
    make_scene,
    make_texture,
    new_scene,
)
from text2threejs.spec.text_scene_spec import (  # noqa: E402
    DEFAULT_AMBIENT_INTENSITY,
    DEFAULT_FOG_COLOR,
)
from text2threejs.spec.validate_text_scene_spec import (  # noqa: E402
    validate_spec,
    validate_spec_file,
)


class SchemaConstantsTest(unittest.TestCase):
    """Test schema version, enums, and defaults."""

    def test_schema_version(self):
        self.assertEqual(SCENE_SCHEMA_VERSION, "1.0")

    def test_valid_object_types(self):
        expected = {
            "box", "sphere", "ellipsoid", "cylinder", "cone", "capsule",
            "torus", "plane", "ring", "circle", "tube", "lathe", "extrude",
            "curve-sweep", "ground-blade", "instanced-cluster", "group",
            "text", "sprite", "points", "line",
        }
        self.assertEqual(VALID_OBJECT_TYPES, expected)

    def test_valid_light_types(self):
        expected = {"ambient", "directional", "point", "spot", "hemisphere", "rect-area"}
        self.assertEqual(VALID_LIGHT_TYPES, expected)

    def test_valid_camera_types(self):
        expected = {"perspective", "orthographic"}
        self.assertEqual(VALID_CAMERA_TYPES, expected)

    def test_valid_animation_properties(self):
        self.assertIn("position", VALID_ANIMATION_PROPERTIES)
        self.assertIn("rotation.x", VALID_ANIMATION_PROPERTIES)
        self.assertIn("material.color", VALID_ANIMATION_PROPERTIES)
        self.assertIn("visible", VALID_ANIMATION_PROPERTIES)

    def test_animation_easings(self):
        self.assertIn("linear", ANIMATION_EASINGS)
        self.assertIn("easeInOutCubic", ANIMATION_EASINGS)
        self.assertIn("easeOutElastic", ANIMATION_EASINGS)

    def test_texture_wrappings_and_filters(self):
        self.assertEqual(VALID_TEXTURE_WRAPPINGS, {"repeat", "clamp", "mirror"})
        self.assertEqual(VALID_TEXTURE_FILTERS, {"nearest", "linear", "mipmap"})

    def test_defaults(self):
        self.assertEqual(DEFAULT_BACKGROUND, "#0a0a12")
        self.assertEqual(DEFAULT_FOG_COLOR, "#0a0a12")
        self.assertEqual(DEFAULT_AMBIENT_INTENSITY, 0.4)
        self.assertEqual(DEFAULT_CAMERA_FOV, 50.0)
        self.assertEqual(DEFAULT_CAMERA_NEAR, 0.1)
        self.assertEqual(DEFAULT_CAMERA_FAR, 1000.0)
        self.assertEqual(DEFAULT_CAMERA_POSITION, (0.0, 2.0, 8.0))
        self.assertEqual(DEFAULT_CAMERA_TARGET, (0.0, 0.0, 0.0))
        self.assertEqual(DEFAULT_OBJECT_POSITION, (0.0, 0.0, 0.0))
        self.assertEqual(DEFAULT_OBJECT_ROTATION, (0.0, 0.0, 0.0))
        self.assertEqual(DEFAULT_OBJECT_SCALE, (1.0, 1.0, 1.0))
        self.assertEqual(DEFAULT_MATERIAL_COLOR, "#8a7a5f")
        self.assertEqual(DEFAULT_MATERIAL_ROUGHNESS, 0.7)
        self.assertEqual(DEFAULT_MATERIAL_METALNESS, 0.0)
        self.assertEqual(DEFAULT_LIGHT_INTENSITY, 1.0)
        self.assertEqual(DEFAULT_LIGHT_COLOR, "#ffffff")


class HelperPredicatesTest(unittest.TestCase):
    """Test the helper predicates used by the validator."""

    def test_is_number(self):
        self.assertTrue(is_number(0))
        self.assertTrue(is_number(1.5))
        self.assertTrue(is_number(-3))
        self.assertFalse(is_number(True))
        self.assertFalse(is_number(False))
        self.assertFalse(is_number("1"))
        self.assertFalse(is_number(None))
        self.assertFalse(is_number([1]))

    def test_is_vec3(self):
        self.assertTrue(is_vec3([0, 0, 0]))
        self.assertTrue(is_vec3([1.5, -2, 3.0]))
        self.assertTrue(is_vec3((1, 2, 3)))
        self.assertFalse(is_vec3([1, 2]))
        self.assertFalse(is_vec3([1, 2, 3, 4]))
        self.assertFalse(is_vec3([1, 2, "3"]))
        self.assertFalse(is_vec3([True, 2, 3]))
        self.assertFalse(is_vec3("123"))

    def test_is_color(self):
        self.assertTrue(is_color("#fff"))
        self.assertTrue(is_color("#ffffff"))
        self.assertTrue(is_color("#0a0a12"))
        self.assertFalse(is_color("white"))
        self.assertFalse(is_color("#ffff"))
        self.assertFalse(is_color("#fffffff"))
        self.assertFalse(is_color(123))
        self.assertFalse(is_color(None))

    def test_is_unit_interval(self):
        self.assertTrue(is_unit_interval(0.0))
        self.assertTrue(is_unit_interval(0.5))
        self.assertTrue(is_unit_interval(1.0))
        self.assertFalse(is_unit_interval(-0.1))
        self.assertFalse(is_unit_interval(1.1))
        self.assertFalse(is_unit_interval(True))
        self.assertFalse(is_unit_interval("0.5"))


class ValidSpecTest(unittest.TestCase):
    """Test that valid specs pass validation."""

    def test_minimal_scene_passes(self):
        spec = new_scene("test scene")
        errors, warnings = validate_spec(spec)
        self.assertEqual(errors, [], f"expected no errors, got: {errors}")
        self.assertEqual(warnings, [])

    def test_full_scene_passes(self):
        spec = new_scene(
            "full scene",
            description="A complete scene with all block types",
            background="#112233",
        )
        spec["objects"] = [
            make_object("ground", object_type="plane", position=(0, 0, 0)),
            make_object(
                "cube",
                object_type="box",
                parent="ground",
                position=(0, 1, 0),
                dimensions={"width": 1, "height": 1, "depth": 1},
                material="mat_red",
            ),
        ]
        spec["materials"] = [
            make_material("mat_red", color="#ff0000", roughness=0.5, metalness=0.2),
            make_material("mat_blue", color="#0000ff", texture="tex_checker"),
        ]
        spec["textures"] = [
            make_texture("tex_checker", url="checker.png", repeat=(2, 2)),
        ]
        spec["lights"] = [
            make_light("sun", light_type="directional", position=(5, 10, 5)),
            make_light("fill", light_type="point", position=(-3, 2, 4)),
        ]
        spec["camera"] = make_camera(
            camera_type="perspective",
            fov=60,
            position=(0, 3, 10),
            target=(0, 1, 0),
        )
        spec["animations"] = [
            make_animation(
                "spin",
                object_id="cube",
                property_name="rotation.y",
                from_value=0,
                to_value=6.28,
                duration=2.0,
                easing="easeInOutCubic",
            ),
        ]
        spec["interactions"] = [
            {"object": "cube", "type": "click"},
        ]
        spec["constraints"] = [
            {"object": "cube", "type": "lookAt"},
        ]
        spec["effects"] = [
            {"type": "bloom"},
        ]
        spec["metadata"] = {
            "sourcePrompt": "a red cube on a ground plane with a sun light",
            "generatedBy": "test",
            "generatedAt": "2026-01-01T00:00:00Z",
            "notes": ["test note"],
        }

        errors, warnings = validate_spec(spec)
        self.assertEqual(errors, [], f"expected no errors, got: {errors}")

    def test_factory_blocks_are_valid(self):
        """Each factory block individually should be schema-valid."""
        spec = new_scene("factory test")
        spec["objects"] = [make_object("obj1")]
        spec["materials"] = [make_material("mat1")]
        spec["textures"] = [make_texture("tex1")]
        spec["lights"] = [make_light("light1")]
        spec["camera"] = make_camera()
        spec["animations"] = [
            make_animation("anim1", object_id="obj1", property_name="position.y",
                           from_value=0, to_value=1)
        ]
        errors, warnings = validate_spec(spec)
        self.assertEqual(errors, [], f"expected no errors, got: {errors}")


class MalformedSpecTest(unittest.TestCase):
    """Test that malformed specs fail validation."""

    def test_non_dict_spec_fails(self):
        errors, _ = validate_spec("not a dict")
        self.assertTrue(any("must be a JSON object" in e for e in errors))

        errors, _ = validate_spec([1, 2, 3])
        self.assertTrue(any("must be a JSON object" in e for e in errors))

        errors, _ = validate_spec(None)
        self.assertTrue(any("must be a JSON object" in e for e in errors))

    def test_missing_schema_version_fails(self):
        spec = new_scene("test")
        del spec["schemaVersion"]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("schemaVersion" in e for e in errors))

    def test_wrong_schema_version_fails(self):
        spec = new_scene("test")
        spec["schemaVersion"] = "9.9"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("unsupported schemaVersion" in e for e in errors))

    def test_missing_scene_block_fails(self):
        spec = new_scene("test")
        del spec["scene"]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("missing required field: scene" in e for e in errors))

    def test_missing_objects_fails(self):
        spec = new_scene("test")
        del spec["objects"]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("missing required field: objects" in e for e in errors))

    def test_invalid_scene_name_fails(self):
        spec = new_scene("test")
        spec["scene"]["name"] = ""
        errors, _ = validate_spec(spec)
        self.assertTrue(any("scene.name must be a non-empty string" in e for e in errors))

        spec = new_scene("test")
        spec["scene"]["name"] = 123
        errors, _ = validate_spec(spec)
        self.assertTrue(any("scene.name must be a non-empty string" in e for e in errors))

    def test_invalid_background_color_fails(self):
        spec = new_scene("test")
        spec["scene"]["background"] = "not-a-color"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("scene.background" in e for e in errors))

    def test_invalid_up_vector_fails(self):
        spec = new_scene("test")
        spec["scene"]["up"] = "diagonal"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("scene.up" in e for e in errors))

    def test_invalid_fog_fails(self):
        spec = new_scene("test")
        spec["scene"]["fog"] = {"type": "invalid-fog-type"}
        errors, _ = validate_spec(spec)
        self.assertTrue(any("scene.fog.type" in e for e in errors))

        spec = new_scene("test")
        spec["scene"]["fog"] = {"type": "fog", "color": "red"}
        errors, _ = validate_spec(spec)
        self.assertTrue(any("scene.fog.color" in e for e in errors))

    def test_invalid_environment_fails(self):
        spec = new_scene("test")
        spec["environment"]["toneMapping"] = "invalid-tone"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("environment.toneMapping" in e for e in errors))

        spec = new_scene("test")
        spec["environment"]["shadowMapEnabled"] = "yes"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("environment.shadowMapEnabled" in e for e in errors))

    def test_invalid_camera_fails(self):
        spec = new_scene("test")
        spec["camera"]["type"] = "fisheye"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("camera.type" in e for e in errors))

        spec = new_scene("test")
        spec["camera"]["position"] = [0, 0]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("camera.position" in e for e in errors))

        spec = new_scene("test")
        spec["camera"]["fov"] = "wide"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("camera.fov" in e for e in errors))

    def test_invalid_object_type_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1", object_type="pyramid")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("objects[0].type" in e for e in errors))

    def test_duplicate_object_ids_fail(self):
        spec = new_scene("test")
        spec["objects"] = [
            make_object("dup"),
            make_object("dup"),
        ]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_invalid_object_position_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1", position=(0, 0))]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("objects[0].position" in e for e in errors))

    def test_invalid_object_dimensions_fails(self):
        spec = new_scene("test")
        spec["objects"] = [
            make_object("obj1", dimensions={"width": "wide", "height": 1, "depth": 1})
        ]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("objects[0].dimensions.width" in e for e in errors))

    def test_invalid_material_fails(self):
        spec = new_scene("test")
        spec["materials"] = [make_material("mat1", color="red")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("materials[0].color" in e for e in errors))

        spec = new_scene("test")
        spec["materials"] = [make_material("mat1", roughness=1.5)]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("materials[0].roughness" in e for e in errors))

        spec = new_scene("test")
        spec["materials"] = [make_material("mat1", metalness=-0.5)]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("materials[0].metalness" in e for e in errors))

    def test_duplicate_material_ids_fail(self):
        spec = new_scene("test")
        spec["materials"] = [
            make_material("dup"),
            make_material("dup"),
        ]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_invalid_texture_fails(self):
        spec = new_scene("test")
        spec["textures"] = [make_texture("tex1", wrap_s="invalid-wrap")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("textures[0].wrapS" in e for e in errors))

        spec = new_scene("test")
        spec["textures"] = [make_texture("tex1", min_filter="invalid-filter")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("textures[0].minFilter" in e for e in errors))

        spec = new_scene("test")
        spec["textures"] = [make_texture("tex1", repeat=(1, 2, 3))]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("textures[0].repeat" in e for e in errors))

    def test_invalid_light_fails(self):
        spec = new_scene("test")
        spec["lights"] = [make_light("light1", light_type="candle")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("lights[0].type" in e for e in errors))

        spec = new_scene("test")
        spec["lights"] = [make_light("light1", color="blue")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("lights[0].color" in e for e in errors))

        spec = new_scene("test")
        spec["lights"] = [make_light("light1", position=(0, 0))]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("lights[0].position" in e for e in errors))

    def test_invalid_animation_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1")]
        spec["animations"] = [
            make_animation("anim1", object_id="obj1", property_name="position.y",
                           from_value=0, to_value=1)
        ]
        spec["animations"][0]["property"] = "invalid.property"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("animations[0].property" in e for e in errors))

        spec = new_scene("test")
        spec["objects"] = [make_object("obj1")]
        spec["animations"] = [
            make_animation("anim1", object_id="obj1", property_name="position.y",
                           from_value=0, to_value=1)
        ]
        spec["animations"][0]["duration"] = 0
        errors, _ = validate_spec(spec)
        self.assertTrue(any("animations[0].duration" in e for e in errors))

        spec = new_scene("test")
        spec["objects"] = [make_object("obj1")]
        spec["animations"] = [
            make_animation("anim1", object_id="obj1", property_name="position.y",
                           from_value=0, to_value=1)
        ]
        spec["animations"][0]["easing"] = "invalid-easing"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("animations[0].easing" in e for e in errors))

    def test_animation_missing_from_to_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1")]
        spec["animations"] = [
            {
                "id": "anim1",
                "object": "obj1",
                "property": "position.y",
                "duration": 1.0,
            }
        ]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("animations[0].from is required" in e for e in errors))
        self.assertTrue(any("animations[0].to is required" in e for e in errors))

    def test_animation_unknown_object_reference_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1")]
        spec["animations"] = [
            make_animation("anim1", object_id="nonexistent", property_name="position.y",
                           from_value=0, to_value=1)
        ]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("does not reference a known object" in e for e in errors))

    def test_invalid_interaction_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1")]
        spec["interactions"] = [{"object": "nonexistent", "type": "click"}]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("does not reference a known object" in e for e in errors))

    def test_invalid_constraint_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1")]
        spec["constraints"] = [{"object": "nonexistent", "type": "lookAt"}]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("does not reference a known object" in e for e in errors))

    def test_invalid_metadata_fails(self):
        spec = new_scene("test")
        spec["metadata"]["sourcePrompt"] = 123
        errors, _ = validate_spec(spec)
        self.assertTrue(any("metadata.sourcePrompt" in e for e in errors))

        spec = new_scene("test")
        spec["metadata"]["notes"] = "not a list"
        errors, _ = validate_spec(spec)
        self.assertTrue(any("metadata.notes" in e for e in errors))

    def test_unknown_material_reference_fails(self):
        spec = new_scene("test")
        spec["objects"] = [make_object("obj1", material="nonexistent-material")]
        spec["materials"] = [make_material("mat1")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("does not reference a known material" in e for e in errors))

    def test_unknown_texture_reference_fails(self):
        spec = new_scene("test")
        spec["materials"] = [make_material("mat1", texture="nonexistent-texture")]
        spec["textures"] = [make_texture("tex1")]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("does not reference a known texture" in e for e in errors))

    def test_multiple_errors_reported(self):
        """A badly malformed spec should report multiple errors, not just the first."""
        spec = new_scene("test")
        spec["schemaVersion"] = "9.9"
        spec["scene"]["name"] = ""
        spec["objects"] = [
            make_object("obj1", object_type="pyramid", position=(0, 0)),
        ]
        spec["materials"] = [make_material("mat1", color="red")]
        errors, _ = validate_spec(spec)
        self.assertGreaterEqual(len(errors), 4)


class ValidateSpecFileTest(unittest.TestCase):
    """Test the file-based validation entry point."""

    def test_validate_spec_file_valid(self):
        import json
        import tempfile

        spec = new_scene("file test")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(spec, f)
            path = f.name

        try:
            errors, warnings = validate_spec_file(path)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
        finally:
            Path(path).unlink(missing_ok=True)

    def test_validate_spec_file_invalid(self):
        import json
        import tempfile

        spec = new_scene("file test")
        spec["schemaVersion"] = "9.9"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(spec, f)
            path = f.name

        try:
            errors, _ = validate_spec_file(path)
            self.assertTrue(any("unsupported schemaVersion" in e for e in errors))
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()