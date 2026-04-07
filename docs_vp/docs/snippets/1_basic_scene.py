import rv

class BasicScene(rv.Scene):
    def generate(self):
        self.world.set_params(sun_intensity=0.03)
        cube = (
            self.objects.cube()
            .set_location((1, 0, 0.5))
            .set_scale(0.5)
            .set_tags("cube")
        )
        sphere = (
            self.objects.sphere()
            .set_location((-1, 0, 1))
            .set_shading("smooth")
            .set_tags("sphere")
        )
        plane = self.objects.plane(size=1000)
        empty = self.objects.empty().set_location((0, 0, 1))

        cam = (
            self.camera
            .set_location((7, 7, 3))
            .point_at(empty)
        )
