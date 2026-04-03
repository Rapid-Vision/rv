import pathlib
import random
import unittest

import bpy
import mathutils
import rv
import rv.internal as rvi
from mathutils import Vector


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ROCK_BLEND = REPO_ROOT / "examples" / "2_properties" / "rock.blend"
RUSTY_BLEND = REPO_ROOT / "examples" / "4_semantic_aov" / "rusty_metal.blend"
EXPORTED_BLEND = REPO_ROOT / "examples" / "6_export" / "exported.blend"
HDRI_IMAGE = REPO_ROOT / "examples" / "1_primitives" / "1_res.png"


class _SmokeScene(rv.Scene):
    def generate(self):
        pass


def _supported_render_passes():
    layer = bpy.context.view_layer
    return {
        render_pass
        for render_pass, attr in rv.PASS_MAP.items()
        if hasattr(layer, attr)
    }


def _add_geometry_nodes_modifier(rv_obj: rv.Object, input_name: str = "ScaleInput") -> str:
    modifier = rv_obj.obj.modifiers.new(name="SmokeNodes", type="NODES")
    group = bpy.data.node_groups.new("SmokeNodeGroup", "GeometryNodeTree")
    group.interface.new_socket(
        name="Geometry",
        in_out="INPUT",
        socket_type="NodeSocketGeometry",
    )
    group.interface.new_socket(
        name=input_name,
        in_out="INPUT",
        socket_type="NodeSocketFloat",
    )
    group.interface.new_socket(
        name="Geometry",
        in_out="OUTPUT",
        socket_type="NodeSocketGeometry",
    )
    node_input = group.nodes.new("NodeGroupInput")
    node_output = group.nodes.new("NodeGroupOutput")
    group.links.new(node_input.outputs["Geometry"], node_output.inputs["Geometry"])
    modifier.node_group = group
    return modifier.name


class ApiSmokeTest(unittest.TestCase):
    def setUp(self):
        rvi._internal_begin_run(purge_orphans=True)
        self.scene = _SmokeScene()

    def tearDown(self):
        rvi._internal_end_run()

    def test_public_api_smoke(self):
        self.assertIsInstance(rvi._ACTIVE_RUN_ID, str)

        rect = rv.Domain.rect(center=(0.0, 0.0), size=(8.0, 8.0), z=0.5)
        ellipse = rv.Domain.ellipse(center=(0.0, 0.0), radii=(4.0, 2.0), z=0.5)
        polygon = rv.Domain.polygon(
            [(-2.0, -2.0), (2.0, -2.0), (2.0, 2.0), (-2.0, 2.0)],
            z=0.5,
        )
        concave_polygon = rv.Domain.polygon(
            [(-3.0, -2.0), (3.0, -2.0), (3.0, 2.0), (0.0, 0.0), (-3.0, 2.0)],
            z=0.5,
        )
        convex_polygon = rv.Domain.convex_polygon(
            [(-2.0, -2.0), (2.0, -2.0), (2.0, 2.0), (-2.0, 2.0)],
            z=0.5,
        )
        box = rv.Domain.box(center=(0.0, 0.0, 1.5), size=(6.0, 6.0, 4.0))
        cylinder = rv.Domain.cylinder(center=(0.0, 0.0, 1.5), radius=2.0, height=4.0)
        ellipsoid = rv.Domain.ellipsoid(center=(0.0, 0.0, 1.5), radii=(2.5, 2.0, 1.5))
        inset_rect = rect.inset(0.25)
        rng = random.Random(123)
        sampled_rect = rect.sample_point(rng)
        sampled_ellipse = ellipse.sample_point(rng)
        sampled_polygon = polygon.sample_point(rng)
        sampled_concave_polygon = concave_polygon.sample_point(rng)
        sampled_box = box.sample_point(rng)
        sampled_cylinder = cylinder.sample_point(rng)
        sampled_ellipsoid = ellipsoid.sample_point(rng)
        self.assertTrue(rect.contains_point(sampled_rect))
        self.assertTrue(ellipse.contains_point(sampled_ellipse))
        self.assertTrue(polygon.contains_point(sampled_polygon))
        self.assertTrue(concave_polygon.contains_point(sampled_concave_polygon))
        self.assertFalse(concave_polygon.contains_point(Vector((0.0, 1.5, 0.5))))
        self.assertTrue(convex_polygon.contains_point(Vector((0.0, 0.0, 0.5))))
        with self.assertRaises(ValueError):
            rv.Domain.convex_polygon([(-1.0, -1.0), (1.0, -1.0), (0.0, 0.0), (1.0, 1.0)])
        self.assertTrue(box.contains_point(sampled_box))
        self.assertTrue(cylinder.contains_point(sampled_cylinder))
        self.assertTrue(ellipsoid.contains_point(sampled_ellipsoid))
        self.assertIsNotNone(inset_rect.aabb())

        self.scene.set_rendering_time_limit(1.5)
        self.scene.set_passes(*sorted(_supported_render_passes(), key=lambda item: item.value))
        self.scene.enable_semantic_channels("Mask", "Rust")
        self.scene.set_semantic_mask_threshold(0.4)
        self.scene.set_tags("scene")
        self.scene.add_tags("smoke")

        empty = self.scene.create_empty("Target").set_location((0.0, 0.0, 1.0))
        sphere = self.scene.create_sphere("Sphere", radius=0.5).set_location(
            (-1.0, 0.0, 1.0)
        )
        cube = self.scene.create_cube("Cube", size=1.0).set_location((0.0, 0.0, 1.0))
        plane = self.scene.create_plane("Plane", size=8.0).set_location((0.0, 0.0, 0.0))

        basic_world = rv.BasicWorld()
        self.assertIs(
            basic_world.set_params(color=(0.1, 0.2, 0.3, 1.0), strength=0.5),
            basic_world,
        )
        self.scene.set_world(basic_world)
        self.assertIs(self.scene.get_world(), basic_world)
        basic_world._internal_post_gen()

        sky_world = rv.SkyWorld()
        self.assertIs(
            sky_world.set_params(
            strength=0.3,
            sun_size=12.0,
            sun_intensity=0.5,
            sun_elevation=23.0,
            rotation_z=34.0,
            air=1.0,
            aerosol_density=0.2,
            ozone=0.3,
            ),
            sky_world,
        )
        self.scene.set_world(sky_world)
        sky_world._internal_post_gen()

        hdri_world = rv.HDRIWorld(str(HDRI_IMAGE))
        self.assertIs(
            hdri_world.set_params(
                hdri_path=str(HDRI_IMAGE), strength=0.7, rotation_z=15.0
            ),
            hdri_world,
        )
        self.scene.set_world(hdri_world)
        hdri_world._internal_post_gen()

        imported_world = rv.ImportedWorld(str(ROCK_BLEND), world_name="World")
        self.assertIs(imported_world.set_params(smoke_world=True), imported_world)
        self.scene.set_world(imported_world)
        imported_world._internal_post_gen()

        material = self.scene.create_material("SmokeMaterial")
        material.set_params(
            base_color=(0.8, 0.2, 0.1, 1.0),
            roughness=0.4,
            metallic=0.1,
            specular=0.5,
            emission_color=(0.1, 0.1, 0.1, 1.0),
            emission_strength=0.2,
            alpha=0.95,
            transmission=0.05,
            ior=1.45,
        ).set_property("tag", "basic")

        imported_material = self.scene.import_material(
            str(RUSTY_BLEND), material_name="RustyMetal"
        )
        imported_material.set_params(smoke_material=True)

        modifier_name = _add_geometry_nodes_modifier(cube)
        cube.set_location((0.0, 0.0, 1.0))
        cube.set_rotation(mathutils.Euler((0.1, 0.2, 0.3)))
        cube.set_scale(1.1)
        cube.set_property("custom", 7)
        cube.set_modifier_input("ScaleInput", 1.25, modifier_name=modifier_name)
        cube.set_material(material)
        cube.add_material(imported_material)
        cube.clear_materials()
        cube.set_material(material)
        cube.set_tags("cube")
        cube.add_tags("smoke")
        cube.point_at(empty, angle=15.0)
        cube.rotate_around_axis(mathutils.Vector((0.0, 0.0, 1.0)), 20.0)
        cube.set_shading("smooth")
        cube.show_debug_axes(True)
        cube.show_debug_name(True)
        self.assertEqual(len(cube.get_dimensions("world")), 3)
        self.assertEqual(len(cube.get_dimensions("local")), 3)
        self.assertIn("min", cube.get_bounds("world"))
        self.assertIn("min", cube.get_bounds("local"))

        cube_stats = cube.inspect(applied_scale=True)
        self.assertIn("dimensions_world", cube_stats.to_dict())
        loader_stats = self.scene.inspect_object(cube, applied_scale=False)
        self.assertIn("dimensions_local", loader_stats.to_dict())

        hull3d = rv.Domain.convex_hull_3d(cube)
        hull2d = rv.Domain.convex_hull_2d(cube)
        self.assertTrue(hull3d.contains_object(cube, mode="mesh"))
        self.assertTrue(box.contains_object(cube, mode="aabb"))
        self.assertTrue(hull2d.contains_point(hull2d.sample_point(rng)))

        cube.add_rigidbody(
            mode="box",
            mesh_source="FINAL",
            body_type="ACTIVE",
            mass=1.0,
            friction=0.6,
            restitution=0.05,
            linear_damping=0.1,
            angular_damping=0.2,
            use_margin=True,
            collision_margin=0.02,
            use_deactivation=True,
            deactivate_linear_velocity=0.1,
            deactivate_angular_velocity=0.1,
            start_deactivated=False,
        )
        plane.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        rv.simulate_physics(
            frames=1,
            substeps=4,
            time_scale=1.0,
            solver_iterations=8,
            use_split_impulse=True,
        )
        cube.remove_rigidbody(keep_transform=True)
        plane.remove_rigidbody(keep_transform=True)
        cube.hide("wireframe")

        camera = self.scene.get_camera()
        camera.set_location((3.0, -3.0, 2.0)).point_at(empty).set_fov(60.0)

        point = self.scene.create_point_light("Point", power=50.0)
        self.assertIs(point.light_data, point.obj.data)
        point.set_color((1.0, 0.9, 0.8))
        point.set_power(25.0)
        point.set_cast_shadow(True)
        point.set_specular_factor(0.5)
        point.set_softness(0.1)
        point.set_params(diffuse_factor=0.7, smoke_flag=True)
        point.set_radius(0.2)

        sun = self.scene.create_sun_light("Sun", power=1.0)
        sun.set_angle(0.2)
        sun.set_softness(0.05)

        area = self.scene.create_area_light("Area", power=20.0)
        area.set_shape("RECTANGLE")
        area.set_size(1.5)
        area.set_size_xy(1.5, 0.75)

        spot = self.scene.create_spot_light("Spot", power=35.0)
        spot.set_spot_size(0.6)
        spot.set_blend(0.3)
        spot.set_show_cone(True)

        rock_loader = self.scene.load_object(str(ROCK_BLEND), import_name="Rock")
        exported_loaders = self.scene.load_objects(
            str(EXPORTED_BLEND), import_names=["Cube_0", "Cube_1"]
        )
        cube_loader = cube.as_loader()
        self.assertIs(cube_loader.obj, cube.obj)
        loader_instance = rock_loader.create_instance(name="RockInstance")
        rock_loader.set_source(cube)
        remapped_instance = rock_loader.create_instance(
            name="CubeClone", register_object=False, linked_data=False
        )
        self.assertEqual(remapped_instance.obj.name, "CubeClone")
        self.assertIsNot(remapped_instance.obj.data, cube.obj.data)
        copied_cube = cube.copy(
            name="CubeCopy", register_object=False, linked_data=False
        ).move(dx=1.0, dy=2.0, dz=3.0)
        self.assertEqual(copied_cube.get_location(), (1.0, 2.0, 4.0))
        self.assertEqual(copied_cube.tags, cube.tags)
        inspect_loader = self.scene.inspect_object(exported_loaders[0], applied_scale=True)
        self.assertIn("bounds_world", inspect_loader.to_dict())

        sphere_domain = rv.Domain.rect(center=(0.0, 0.0), size=(10.0, 10.0), z=0.5)
        fast_scattered = self.scene.scatter(
            source=exported_loaders,
            count=2,
            domain=sphere_domain,
            method="fast",
            gap=0.1,
            seed=1,
            unique_data=True,
        )
        self.assertGreaterEqual(len(fast_scattered), 1)
        exact_scattered = self.scene.scatter(
            source=exported_loaders[0],
            count=1,
            domain=sphere_domain,
            method="exact",
            gap=0.0,
            seed=2,
            unique_data=True,
        )
        self.assertGreaterEqual(len(exact_scattered), 1)

        callback_calls: list[tuple[int, float]] = []
        parametric = self.scene.scatter(
            source=exported_loaders[0],
            count=1,
            domain=rv.Domain.box(center=(0.0, 0.0, 1.0), size=(6.0, 6.0, 4.0)),
            method="fast",
            seed=3,
            unique_data=True,
            on_create=lambda obj, local_rng, index: (
                callback_calls.append((index, local_rng.random())),
                obj.set_scale(0.7).set_property("scale_seed", index + 1),
            )[-1],
        )
        self.assertGreaterEqual(len(parametric), 1)
        self.assertEqual(callback_calls[0][0], 0)
        self.assertEqual(parametric[0].properties["scale_seed"], 1)

        self.assertTrue(box.contains_object(loader_instance, mode="mesh"))

        rvi._internal_end_run()


if __name__ == "__main__":
    unittest.main()
