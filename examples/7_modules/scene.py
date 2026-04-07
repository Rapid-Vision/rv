import rv
import grid


class BasicScene(rv.Scene):
    def generate(self, seed):
        self.world = rv.SkyWorld().set_params(strength=0.1, sun_intensity=0.03)

        grid.cubes_grid(self)

        plane = self.objects.plane(size=1000)
        empty = self.objects.empty().set_location((0, 0, 1))

        light = self.lights.point(power=10).set_location([0, 0, 2])

        cam = self.camera.set_location((5, 5, 2)).point_at(empty)
