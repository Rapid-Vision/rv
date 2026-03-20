from pathlib import Path

import rv


EXPORTED_BLEND = Path(__file__).with_name("exported.blend")
CUBE_NAMES = [f"Cube_{i}" for i in range(30)]


class ImportScatteredBoxesScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.05, strength=0.4)

        floor = self.create_plane(name="Floor", size=18).set_location((1.5, 0.0, 0.0))
        floor.set_tags("floor")

        loaders = self.load_objects(str(EXPORTED_BLEND), import_names=CUBE_NAMES)

        for loader in loaders:
            left = loader.create_instance()
            right = loader.create_instance()
            right.set_location(
                (
                    right.obj.location.x + 3.0,
                    right.obj.location.y,
                    right.obj.location.z,
                )
            )

        look_at = self.create_empty("LookAt").set_location((1.5, 0.0, 0.9))
        self.get_camera().set_location((8.0, -9.0, 5.5)).point_at(look_at)
