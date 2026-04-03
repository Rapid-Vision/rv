import rv


class BasicScene(rv.Scene):
    def generate(self, seed):
        world = rv.SkyWorld()
        world.set_params(strength=0.1, sun_intensity=0.03)
        self.set_world(world)

        mat_cube = self.create_material().set_params(base_color=[1, 0, 0])
        cube = (
            self.create_cube()
            .set_location((1, 0, 0.5))
            .set_scale(0.5)
            .set_tags("cube")
            .set_material(mat_cube)
        )
        mat_sphere = self.create_material().set_params(metallic=1, roughness=0.2)
        sphere = (
            self.create_sphere()
            .set_location((-1, 0, 1))
            .set_shading("smooth")
            .set_tags("sphere")
            .set_material(mat_sphere)
        )
        plane = self.create_plane(size=1000)
        empty = self.create_empty().set_location((0, 0, 1))

        light = self.create_point_light(power=10).set_location([0, 0, 0.1])

        cam = self.get_camera().set_location((5, 5, 2)).point_at(empty)
