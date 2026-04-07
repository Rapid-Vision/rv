from pathlib import Path

import rv

EXPORTED_BLEND = Path(__file__).with_name("exported.blend")
CUBE_NAMES = [f"Cube_{i}" for i in range(30)]


class ImportScatteredBoxesScene(rv.Scene):
    def generate(self, seed):
        self.world.set_params(sun_intensity=0.05, strength=0.4)

        floor = self.objects.plane(name="Floor", size=18).set_location((1.5, 0.0, 0.0))
        floor.set_tags("floor")

        loaders = self.assets.objects(str(EXPORTED_BLEND), import_names=CUBE_NAMES)

        for loader in loaders:
            for i in range(3):
                loader.create_instance().move(dx=i * 3.0)

        look_at = self.objects.empty("LookAt").set_location((1.5, 0.0, 0.9))
        self.camera.set_location((8.0, -9.0, 5.5)).point_at(look_at)
