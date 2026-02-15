import rv
import random


class BasicScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.1)
        cube_loader = self.load_object("./rock.blend", "Rock")
        cube1 = cube_loader.create_instance()
        cube1.set_property("geo_seed", random.uniform(0, 1000))

        plane = self.create_plane(size=100).set_location([0, 0, 0])
        empty = self.create_empty().set_location((0, 0, 0))

        cam = self.get_camera().set_location((2, 0, 0.7)).point_at(empty)
