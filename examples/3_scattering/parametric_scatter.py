import random

import rv


class ParametricScatterScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        self.create_plane(size=100).set_location((0, 0, -1))
        target = self.create_empty().set_location((0, 0, 0))
        seed = 11

        source_cube = self.create_cube(name="ScatterSourceCube", size=1.0).set_location(
            (0, 0, -1000)
        )
        loader = rv.ObjectLoader(source_cube.obj, self)
        source = (
            rv.ParametricSource(loader)
            .set_sampler(lambda rng: {"count": rng.randint(2, 4)})
            .set_applier(
                lambda obj, params: obj.set_property("count", params["count"])
            )
        )

        domain = rv.Domain.ellipse(center=(0, 0), radii=(15, 9), z=0.0)
        placed = self.scatter_parametric(
            source=source,
            count=30,
            domain=domain,
            strategy="bvh",
            min_gap=0.2,
            scale_range=(0.1, 1.0),
            seed=seed,
        )
        rng = random.Random(seed)
        for idx, obj in enumerate(placed):
            obj.obj.data = obj.obj.data.copy()
            material = self.create_material(name=f"CubeMat_{idx}").set_params(
                base_color=(rng.random(), rng.random(), rng.random()),
                roughness=0.4,
            )
            obj.set_material(material)
            obj.set_tags("parametric")

        self.get_camera().set_location((24, -24, 16)).point_at(target)
