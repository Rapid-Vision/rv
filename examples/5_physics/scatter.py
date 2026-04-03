import math
import random

import mathutils
import rv


class PhysicsScatterScene(rv.Scene):
    def generate(self):
        self.set_passes([rv.RenderPass.Z])
        self.get_world().set_params(sun_intensity=0.05, strength=0.4)

        base_length = 5
        height = 1

        floor = self.create_plane(name="Floor", size=base_length).set_location(
            (0.0, 0.0, 0.0)
        )
        floor.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        floor.set_tags("box")

        box_center = self.create_empty("BoxCenter").set_location((0, 0, height / 2.0))

        wall = (
            self.create_plane(name="wall_1", size=1.0)
            .set_scale((base_length, 1.0, height))
            .set_location((0.0, base_length / 2.0, height / 2.0))
            .point_at(box_center)
            .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        )
        wall = (
            self.create_plane(name="wall_2", size=1.0)
            .set_scale((base_length, 1.0, height))
            .set_location((0.0, -base_length / 2.0, height / 2.0))
            .point_at(box_center)
            .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        )

        wall = (
            self.create_plane(name="wall_3", size=1.0)
            .set_scale((1.0, base_length, height))
            .set_location((base_length / 2.0, 0.0, height / 2.0))
            .point_at(box_center, 90)
            .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        )

        wall = (
            self.create_plane(name="wall_4", size=1.0)
            .set_scale((1.0, base_length, height))
            .set_location((-base_length / 2.0, 0.0, height / 2.0))
            .point_at(box_center, 90)
            .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        )

        rng = random.Random()

        for i in range(30):
            cube = self.create_cube(name=f"Cube_{i}", size=0.5)
            cube.set_location(
                (
                    rng.uniform(-base_length, base_length) / 2.0 * 0.5,
                    rng.uniform(-base_length, base_length) / 2.0 * 0.5,
                    height + i * 0.3,
                )
            )
            cube.set_rotation(
                mathutils.Euler(
                    (
                        rng.uniform(0.0, 2 * math.pi),
                        rng.uniform(0.0, 2 * math.pi),
                        rng.uniform(0.0, 2 * math.pi),
                    )
                ).to_quaternion()
            )
            cube.add_rigidbody(
                mode="box",
                body_type="ACTIVE",
                mass=0.2,
                friction=0.7,
                collision_margin=0.01,
                use_deactivation=True,
                deactivate_linear_velocity=0.15,
                deactivate_angular_velocity=0.2,
            )
            cube.set_tags("cube")

        rv.simulate_physics(
            frames=120,
            substeps=12,
            solver_iterations=30,
            use_split_impulse=True,
            split_impulse_penetration_threshold=0.04,
            time_scale=1.0,
        )

        look_at = self.create_empty("LookAt").set_location((0.0, 0.0, 0.9))
        self.get_camera().set_location((5.0, -5.0, 4.0)).point_at(look_at)
