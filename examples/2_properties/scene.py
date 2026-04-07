import rv
import random

light_base = (0.93, 0.92, 0.91)
dark_base = (0.12, 0.08, 0.07)


class BasicScene(rv.Scene):
    def generate(self, seed):
        rng = random.Random(seed)
        self.world.set_params(sun_intensity=0.1)
        rock_loader = self.assets.object("./rock.blend", "Rock")
        rock = rock_loader.create_instance()
        rock.set_modifier_input("seed1", rng.uniform(0, 1000))
        rock.set_property(
            "highlight_color",
            [
                0.35 * rng.uniform(0.9, 1.1),
                0.25 * rng.uniform(0.9, 1.1),
                0.2 * rng.uniform(0.9, 1.1),
            ],
        )
        rock.set_property("color_base", rng.choice([light_base, dark_base]))

        plane = self.objects.plane(size=100).set_location([0, 0, 0])
        empty = self.objects.empty().set_location((0, 0, 0.1))

        cam = self.camera.set_location((1, 0, 0.2)).point_at(empty)
