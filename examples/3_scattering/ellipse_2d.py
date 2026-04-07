import random
import rv


class EllipseScatterScene(rv.Scene):
    def generate(self, seed):
        self.world.set_params(sun_intensity=0.03)
        self.objects.plane(size=80).set_location((0, 0, 0))
        target = self.objects.empty().set_location((0, 0, 0.6))

        domain = rv.Domain.ellipse(center=(0.0, 0.0), radii=(12.0, 6.0), z=0.0)
        source_cube = self.objects.cube(name="ScatterSourceCube", size=1.0).set_location(
            (0, 0, -1000)
        )
        cubes = self.scatter(
            source=source_cube.as_loader(),
            count=350,
            domain=domain,
            method="fast",
            gap=0.15,
            scale=(0.1, 0.6),
            seed=seed,
            unique_data=True,
        )
        rng = random.Random(seed)
        for idx, cube in enumerate(cubes):
            material = self.materials.basic(name=f"CubeMat_{idx}").set_params(
                base_color=(rng.random(), rng.random(), rng.random()),
                roughness=0.4,
            )
            cube.set_material(material)
            cube.set_tags("cube")

        self.camera.set_location((18, -18, 14)).point_at(target)
