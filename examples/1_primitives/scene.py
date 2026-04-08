import rv


class BasicScene(rv.Scene):
    def generate(self, seed):
        self.world = rv.SkyWorld().set_params(strength=0.1, sun_intensity=0.03)

        mat_cube = self.materials.basic().set_params(base_color=[1, 0, 0])
        cube = (
            self.objects.cube()
            .set_location((1, 0, 0.5))
            .set_scale(0.5)
            .set_tags("cube")
            .set_material(mat_cube)
        )
        mat_sphere = self.materials.basic().set_params(metallic=1, roughness=0.2)
        sphere = (
            self.objects.sphere()
            .set_location((-1, 0, 1))
            .set_shading("smooth")
            .set_tags("sphere")
            .set_material(mat_sphere)
        )
        plane = self.objects.plane(size=1000)
        empty = self.objects.empty().set_location((0, 0, 1))

        light = self.lights.point(power=10).set_location([0, 0, 0.1])

        cam = self.camera.set_location((5, 5, 2)).point_at(empty)
