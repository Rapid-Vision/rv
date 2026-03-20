import math
import random

import mathutils
import rv


class ExportScatteredBoxesScene(rv.Scene):
    def generate(self):
        self.set_passes([rv.RenderPass.Z])
        self.get_world().set_params(sun_intensity=0.05, strength=0.4)

        base_length = 5
        height = 1

        floor = self.create_plane(name="Floor", size=base_length).set_location(
            (0.0, 0.0, 0.0)
        )
        floor.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        floor.set_tags("floor")

        rng = random.Random(7)

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
            cube.add_rigidbody(mode="box", body_type="ACTIVE", mass=0.2, friction=0.7)
            cube.set_tags("cube", "exported_cluster")

        rv.simulate_physics(frames=120, substeps=10, time_scale=1.0)

        look_at = self.create_empty("LookAt").set_location((1.5, 0.0, 0.9))
        self.get_camera().set_location((7.0, -8.0, 5.0)).point_at(look_at)
