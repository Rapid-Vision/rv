import random

import rv


class HullScatterScene(rv.Scene):
    def generate(self, seed):
        self.world.set_params(sun_intensity=0.03)
        self.objects.plane(size=120).set_location((0, 0, -6))
        target = self.objects.empty().set_location((0, 0, 0))

        container = (
            self.objects.cube(name="Container", size=14)
            .set_scale((1.2, 0.8, 0.6))
            .hide(view="wireframe")
        )
        domain = rv.Domain.convex_hull_3d(container)

        source_cube = self.objects.cube(
            name="ScatterSourceCube", size=1.0
        ).set_location((0, 0, -1000))
        sphere_loader = source_cube.as_loader()
        placed = self.scatter(
            source=sphere_loader,
            count=300,
            domain=domain,
            method="exact",
            gap=0.2,
            rotation="free",
            scale=(0.25, 0.45),
            margin=0.2,
            seed=seed,
            unique_data=True,
        )
        rng = random.Random(seed)
        for idx, obj in enumerate(placed):
            material = self.materials.basic(name=f"CubeMat_{idx}").set_params(
                base_color=(rng.random(), rng.random(), rng.random()),
                roughness=0.4,
            )
            obj.set_material(material)
            obj.set_tags("inside_hull")

        container.show_debug_name(True).show_debug_axes(True)
        self.camera.set_location((24, -24, 18)).point_at(target)
