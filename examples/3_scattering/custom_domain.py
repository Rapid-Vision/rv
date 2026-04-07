import math
import random

import rv


class CustomDomainScatterScene(rv.Scene):
    def generate(self, seed):
        self.world.set_params(sun_intensity=0.04, strength=0.25)
        self.objects.plane(name="Ground", size=120).set_location((0.0, 0.0, -6.0))
        target = self.objects.empty("Target").set_location((0.0, 0.0, 0.0))

        max_radius = 10.0
        max_height = 6.0

        def contains_point(point: rv.mathutils.Vector, margin: float) -> bool:
            v = point.x**2 + point.y**2
            z_abs = abs(point.z)
            return v <= z_abs - margin and z_abs <= max_height - margin

        def aabb(inset_margin: float) -> rv.AABB:
            radial_limit = max(0.0, max_radius - inset_margin)
            vertical_limit = max(0.0, max_height - inset_margin)
            return (
                rv.Vector((-radial_limit, -radial_limit, -vertical_limit)),
                rv.Vector((radial_limit, radial_limit, vertical_limit)),
            )

        domain = rv.Domain.custom(
            dimension=3,
            contains_point=contains_point,
            aabb=aabb,
            kind="double_cone_shell",
            data={"equation": "z^2 > x^2 + y^2"},
        )

        source = self.objects.cube(name="ScatterSourceCube", size=1.0).set_location(
            (0.0, 0.0, -1000.0)
        )
        placed = self.scatter(
            source=source.as_loader(),
            count=220,
            domain=domain,
            method="fast",
            gap=0.12,
            rotation="free",
            scale=(0.12, 0.35),
            seed=seed,
            unique_data=True,
        )
        rng = random.Random(seed)
        for idx, obj in enumerate(placed):
            height_ratio = 0.5 + 0.5 * (obj.get_location()[2] / max_height)
            obj.set_material(
                self.materials.basic(name=f"ConeMat_{idx}").set_params(
                    base_color=(
                        0.2 + 0.6 * rng.random(),
                        0.3 + 0.4 * max(0.0, height_ratio),
                        0.7 - 0.4 * max(0.0, height_ratio),
                    ),
                    roughness=0.35,
                )
            )
            obj.set_tags("custom_domain")

        self.camera.set_location((18.0, -18.0, 12.0)).point_at(target)
