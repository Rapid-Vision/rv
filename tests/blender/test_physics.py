import unittest
from unittest import mock

import rv


class _TestScene(rv.Scene):
    def generate(self):
        pass


class PhysicsApiTest(unittest.TestCase):
    def setUp(self):
        rv._internal_begin_run(purge_orphans=True)
        self.scene = _TestScene()

    def test_add_rigidbody_applies_explicit_margin(self):
        cube = self.scene.create_cube(size=2.0)
        cube.add_rigidbody(use_margin=False, collision_margin=0.125)

        rb = cube.obj.rigid_body
        self.assertIsNotNone(rb)
        if hasattr(rb, "use_margin"):
            self.assertFalse(rb.use_margin)
        if hasattr(rb, "collision_margin"):
            self.assertAlmostEqual(rb.collision_margin, 0.125, places=6)

    def test_add_rigidbody_uses_auto_margin_by_default(self):
        cube = self.scene.create_cube(size=2.0)
        cube.add_rigidbody(collision_margin=None)

        rb = cube.obj.rigid_body
        self.assertIsNotNone(rb)
        if hasattr(rb, "collision_margin"):
            self.assertAlmostEqual(rb.collision_margin, 0.02, places=6)

    def test_add_rigidbody_applies_deactivation_controls_when_supported(self):
        cube = self.scene.create_cube(size=1.0)
        cube.add_rigidbody(
            use_deactivation=True,
            deactivate_linear_velocity=0.15,
            deactivate_angular_velocity=0.2,
            start_deactivated=True,
        )

        rb = cube.obj.rigid_body
        self.assertIsNotNone(rb)
        if hasattr(rb, "use_deactivation"):
            self.assertTrue(rb.use_deactivation)
        if hasattr(rb, "deactivate_linear_velocity"):
            self.assertAlmostEqual(rb.deactivate_linear_velocity, 0.15, places=6)
        if hasattr(rb, "deactivate_angular_velocity"):
            self.assertAlmostEqual(rb.deactivate_angular_velocity, 0.2, places=6)
        if hasattr(rb, "use_start_deactivated"):
            self.assertTrue(rb.use_start_deactivated)

    def test_simulate_physics_applies_world_settings_when_supported(self):
        cube = self.scene.create_cube(size=1.0).set_location((0.0, 0.0, 1.0))
        cube.add_rigidbody()
        rbw = rv.bpy.context.scene.rigidbody_world
        kwargs = {
            "frames": 1,
            "substeps": 5,
            "time_scale": 0.75,
            "solver_iterations": 13,
            "use_split_impulse": True,
        }
        expects_threshold = hasattr(rbw, "split_impulse_penetration_threshold")
        if expects_threshold:
            kwargs["split_impulse_penetration_threshold"] = 0.04

        rv.simulate_physics(**kwargs)

        rbw = rv.bpy.context.scene.rigidbody_world
        self.assertIsNotNone(rbw)
        if hasattr(rbw, "time_scale"):
            self.assertAlmostEqual(rbw.time_scale, 0.75, places=6)
        if hasattr(rbw, "substeps_per_frame"):
            self.assertEqual(rbw.substeps_per_frame, 5)
        if hasattr(rbw, "solver_iterations"):
            self.assertEqual(rbw.solver_iterations, 13)
        if hasattr(rbw, "use_split_impulse"):
            self.assertTrue(rbw.use_split_impulse)
        if expects_threshold:
            self.assertAlmostEqual(
                rbw.split_impulse_penetration_threshold, 0.04, places=6
            )

    def test_add_rigidbody_rejects_negative_margin(self):
        cube = self.scene.create_cube(size=1.0)
        with self.assertRaisesRegex(ValueError, "collision_margin must be >= 0."):
            cube.add_rigidbody(collision_margin=-0.01)

    def test_add_rigidbody_rejects_negative_deactivation_thresholds(self):
        cube = self.scene.create_cube(size=1.0)
        with self.assertRaisesRegex(
            ValueError, "deactivate_linear_velocity must be >= 0."
        ):
            cube.add_rigidbody(deactivate_linear_velocity=-0.01)
        with self.assertRaisesRegex(
            ValueError, "deactivate_angular_velocity must be >= 0."
        ):
            cube.add_rigidbody(deactivate_angular_velocity=-0.01)

    def test_simulate_physics_rejects_invalid_stability_settings(self):
        with self.assertRaisesRegex(ValueError, "solver_iterations must be > 0."):
            rv.simulate_physics(solver_iterations=0)
        with self.assertRaisesRegex(
            ValueError, "split_impulse_penetration_threshold must be >= 0."
        ):
            rv.simulate_physics(split_impulse_penetration_threshold=-0.01)

    def test_add_rigidbody_raises_when_requested_feature_is_unsupported(self):
        cube = self.scene.create_cube(size=1.0)
        original = rv._require_blender_attr

        def require_with_missing(target, attr, feature):
            if attr == "use_deactivation":
                raise RuntimeError("Blender does not support rigid body deactivation.")
            return original(target, attr, feature)

        with mock.patch.object(rv, "_require_blender_attr", require_with_missing):
            with self.assertRaisesRegex(
                RuntimeError, "Blender does not support rigid body deactivation."
            ):
                cube.add_rigidbody(use_deactivation=True)

    def test_simulate_physics_raises_when_requested_world_feature_is_unsupported(self):
        cube = self.scene.create_cube(size=1.0).set_location((0.0, 0.0, 1.0))
        cube.add_rigidbody()
        original = rv._require_blender_attr

        def require_with_missing(target, attr, feature):
            if attr == "use_split_impulse":
                raise RuntimeError(
                    "Blender does not support rigid body world split impulse."
                )
            return original(target, attr, feature)

        with mock.patch.object(rv, "_require_blender_attr", require_with_missing):
            with self.assertRaisesRegex(
                RuntimeError,
                "Blender does not support rigid body world split impulse.",
            ):
                rv.simulate_physics(frames=1, use_split_impulse=True)

    def test_configure_passes_raises_when_requested_pass_is_unsupported(self):
        original = rv._require_blender_attr

        def require_with_missing(target, attr, feature):
            if attr == "use_pass_z":
                raise RuntimeError("Blender does not support render pass Z.")
            return original(target, attr, feature)

        with mock.patch.object(rv, "_require_blender_attr", require_with_missing):
            with self.assertRaisesRegex(
                RuntimeError, "Blender does not support render pass Z."
            ):
                rv._configure_passes({rv.RenderPass.Z})

    def test_configure_semantic_aovs_raises_when_aovs_are_unsupported(self):
        original = rv._require_blender_attr

        def require_with_missing(target, attr, feature):
            if attr == "aovs":
                raise RuntimeError("Blender does not support semantic AOV channels.")
            return original(target, attr, feature)

        with mock.patch.object(rv, "_require_blender_attr", require_with_missing):
            with self.assertRaisesRegex(
                RuntimeError, "Blender does not support semantic AOV channels."
            ):
                rv._configure_semantic_aovs(rv.bpy.context.view_layer, {"mask"})


if __name__ == "__main__":
    unittest.main()
