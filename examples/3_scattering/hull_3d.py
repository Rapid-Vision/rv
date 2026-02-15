import random

import rv


class HullScatterScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        self.create_plane(size=120).set_location((0, 0, -6))
        target = self.create_empty().set_location((0, 0, 0))
        seed = 7

        container = self.create_cube(name="Container", size=14).set_scale(
            (1.2, 0.8, 0.6)
        )
        domain = rv.Domain.convex_hull(container, project_2d=False)

        source_cube = self.create_cube(name="ScatterSourceCube", size=1.0).set_location(
            (0, 0, -1000)
        )
        sphere_loader = rv.ObjectLoader(source_cube.obj, self)
        placed = self.scatter_by_bvh(
            source=sphere_loader,
            count=300,
            domain=domain,
            min_gap=0.2,
            rotation_mode="free",
            scale_range=(0.25, 0.45),
            boundary_margin=0.2,
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
            obj.set_tags("inside_hull")

        container.show_debug_name(True).show_debug_axes(True)
        self.get_camera().set_location((24, -24, 18)).point_at(target)
