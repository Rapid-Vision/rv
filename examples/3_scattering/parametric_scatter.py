import random

import rv


class ParametricScatterScene(rv.Scene):
    def generate(self, seed):
        self.get_world().set_params(sun_intensity=0.03)
        self.create_plane(size=100).set_location((0, 0, -1))
        target = self.create_empty().set_location((0, 0, 0))
        seed = 11

        source_cube = self.create_cube(name="ScatterSourceCube", size=1.0).set_location(
            (0, 0, -1000)
        )
        domain = rv.Domain.ellipse(center=(0, 0), radii=(15, 9), z=0.0)
        rng = random.Random(seed)
        self.scatter(
            source=source_cube,
            count=30,
            domain=domain,
            method="exact",
            gap=0.2,
            scale=(0.1, 1.0),
            seed=seed,
            unique_data=True,
            on_create=lambda obj, local_rng, index: (
                obj.set_material(
                    self.create_material(name=f"CubeMat_{index}").set_params(
                        base_color=(rng.random(), rng.random(), rng.random()),
                        roughness=0.4,
                    )
                ).set_tags("parametric")
            ),
        )

        self.get_camera().set_location((24, -24, 16)).point_at(target)
