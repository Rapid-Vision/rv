import rv


class ParametricScatterScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        self.create_plane(size=100).set_location((0, 0, -1))
        target = self.create_empty().set_location((0, 0, 0))

        loader = self.load_object("./../2_properties/cube.blend", "Cube")
        source = (
            rv.ParametricSource(loader)
            .set_sampler(lambda rng: {"count": rng.randint(2, 4)})
            .set_applier(lambda obj, params: obj.set_property("count", params["count"]))
        )

        domain = rv.Domain.ellipse(center=(0, 0), radii=(15, 9), z=0.0)
        placed = self.scatter_parametric(
            source=source,
            count=30,
            domain=domain,
            strategy="bvh",
            min_gap=0.2,
            scale_range=(0.1, 1.0),
            seed=11,
        )
        for obj in placed:
            obj.set_tags("parametric")

        self.get_camera().set_location((24, -24, 16)).point_at(target)
