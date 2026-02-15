import random
import rv


class EllipseScatterScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        self.create_plane(size=80).set_location((0, 0, 0))
        target = self.create_empty().set_location((0, 0, 0.6))
        seed = 42

        domain = rv.Domain.ellipse(center=(0.0, 0.0), radii=(12.0, 6.0), z=0.0)
        source_cube = self.create_cube(name="ScatterSourceCube", size=1.0).set_location(
            (0, 0, -1000)
        )
        cubes = self.scatter_by_sphere(
            source=rv.ObjectLoader(source_cube.obj, self),
            count=350,
            domain=domain,
            min_gap=0.15,
            scale_range=(0.1, 0.6),
            seed=seed,
        )
        rng = random.Random(seed)
        for idx, cube in enumerate(cubes):
            cube.obj.data = cube.obj.data.copy()
            material = self.create_material(name=f"CubeMat_{idx}").set_params(
                base_color=(rng.random(), rng.random(), rng.random()),
                roughness=0.4,
            )
            cube.set_material(material)
            cube.set_tags("cube")

        self.get_camera().set_location((18, -18, 14)).point_at(target)
