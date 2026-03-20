import rv
from random import uniform # [!code ++]

class BasicScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        cube = (
            self.create_cube()
            .set_location((1, 0, 0.5))
            .set_scale(0.5)
            .set_tags("cube")
        )
        cube.rotate_around_axis(            # [!code ++]
            rv.mathutils.Vector((0, 0, 1)), # [!code ++]
            uniform(0, 360),                # [!code ++]
        )                                   # [!code ++]
        sphere = (
            self.create_sphere()
            .set_location((-1, 0, 1))
            .set_shading("smooth")
            .set_tags("sphere")
        )
        plane = self.create_plane(size=1000)
        empty = self.create_empty().set_location((0, 0, 1))

        cam = (
            self.get_camera()
            .set_location((7, 7, 3))
            .point_at(empty)
        )