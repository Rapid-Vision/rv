import rv


class BasicScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        cube_loader = self.load_object("./cube.blend", "Cube")
        cube1 = cube_loader.create_instance()
        cube1.set_property("count", 7)
        mat1 = rv.BasicMaterial()
        mat1.set_params(base_color=[1, 0, 0], metallic=0, roughness=1)
        cube1.set_material(mat1)

        mat2 = rv.ImportedMaterial("cube.blend", "Some Material")
        plane = self.create_plane(size=100).set_location([0, 0, -1])
        plane.set_material(mat2)
        empty = self.create_empty().set_location((0, 0, 1))

        cam = self.get_camera().set_location((50, 0, 10)).point_at(empty)
