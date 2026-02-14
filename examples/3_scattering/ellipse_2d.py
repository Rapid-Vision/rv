import rv


class EllipseScatterScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        self.create_plane(size=80).set_location((0, 0, 0))
        target = self.create_empty().set_location((0, 0, 0.6))

        domain = rv.Domain.ellipse(center=(0.0, 0.0), radii=(12.0, 6.0), z=0.0)
        cubes = self.scatter_by_sphere(
            source=self.load_object("./../2_properties/cube.blend", "Cube"),
            count=350,
            domain=domain,
            min_gap=0.15,
            scale_range=(0.1, 0.6),
            seed=42,
        )
        for cube in cubes:
            cube.set_tags("cube")

        self.get_camera().set_location((18, -18, 14)).point_at(target)
