import rv
import grid


class BasicScene(rv.Scene):
    def generate(self, seed):
        world = rv.SkyWorld()
        world.set_params(strength=0.1, sun_intensity=0.03)
        self.set_world(world)

        grid.cubes_grid(self)

        plane = self.create_plane(size=1000)
        empty = self.create_empty().set_location((0, 0, 1))

        light = self.create_point_light(power=10).set_location([0, 0, 2])

        cam = self.get_camera().set_location((5, 5, 2)).point_at(empty)
