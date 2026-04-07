import mathutils
import rv


class WallBreakPhysicsScene(rv.Scene):
    def generate(self, seed):
        self.set_passes([rv.RenderPass.Z])
        self.world.set_params(sun_intensity=0.05, strength=0.2)

        ground = self.objects.plane(name="Ground", size=20).set_location((0.0, 0.0, 0.0))
        ground.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        ground.set_tags("ground")

        ramp = (
            self.objects.plane(name="Ramp", size=6.0)
            .set_location((-2.4, 0.0, 0.9))
            .set_rotation(mathutils.Euler((0.0, 0.42, 0.0)).to_quaternion())
        )
        ramp.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.4)
        ramp.set_tags("ramp")

        cube_size = 0.4
        half = cube_size * 0.5
        wall_origin_x = 1.2
        wall: list[rv.Object] = []
        for row in range(3):
            for col in range(3):
                cube = self.objects.cube(name=f"WallCube_{row}_{col}", size=cube_size)
                cube.set_location(
                    (
                        wall_origin_x,
                        (col - 1) * cube_size,
                        half + row * cube_size,
                    )
                )
                cube.add_rigidbody(
                    mode="box",
                    body_type="ACTIVE",
                    mass=0.45,
                    friction=0.85,
                    restitution=0.02,
                    linear_damping=0.04,
                    angular_damping=0.08,
                )
                cube.set_tags("wall_cube")
                wall.append(cube)

        sphere = self.objects.sphere(name="Ball", radius=0.28).set_location(
            (-4.3, 0.0, 2)
        )
        sphere.add_rigidbody(
            mode="sphere",
            body_type="ACTIVE",
            mass=3.5,
            friction=0.15,
            restitution=0.12,
            linear_damping=0.01,
            angular_damping=0.02,
        )
        sphere.set_tags("sphere")

        rv.simulate_physics(frames=220, substeps=16, time_scale=1.0)

        sphere.remove_rigidbody(keep_transform=True)
        for cube in wall:
            cube.remove_rigidbody(keep_transform=True)
        ramp.remove_rigidbody(keep_transform=True)
        ground.remove_rigidbody(keep_transform=True)

        target = self.objects.empty("LookAt").set_location((0.8, 0.0, 0.8))
        self.camera.set_location((6.0, -5.0, 3.2)).point_at(target)
