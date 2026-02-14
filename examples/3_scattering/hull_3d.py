import rv


class HullScatterScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        self.create_plane(size=120).set_location((0, 0, -6))
        target = self.create_empty().set_location((0, 0, 0))

        container = self.create_cube(name="Container", size=14).set_scale(
            (1.2, 0.8, 0.6)
        )
        domain = rv.Domain.convex_hull(container, project_2d=False)

        sphere_loader = self.load_object("./../2_properties/cube.blend", "Cube")
        placed = self.scatter_by_bvh(
            source=sphere_loader,
            count=300,
            domain=domain,
            min_gap=0.2,
            rotation_mode="free",
            scale_range=(0.25, 0.45),
            boundary_margin=0.2,
            seed=7,
        )
        for obj in placed:
            obj.set_tags("inside_hull")

        container.show_debug_name(True).show_debug_axes(True)
        self.get_camera().set_location((24, -24, 18)).point_at(target)
