import pathlib

import rv


class ShaderGraphScene(rv.Scene):
    def generate(self, seed):
        self.world = rv.SkyWorld().set_params(strength=0.15, sun_intensity=0.05)

        base = rv.TextureImage("base.jpg") * 0.7 + 0.1
        normal = rv.NormalMap(
            color=rv.TextureImage("normal.png", colorspace="Non-Color"),
            strength=0.2,
        )
        shader = rv.PrincipledBSDF(
            base_color=base,
            roughness=0.35,
            metallic=0.05,
            normal=normal,
        )
        material = rv.ShaderMaterial(shader, name="ShaderGraphMaterial")

        (
            self.objects.sphere("Sphere", radius=0.75)
            .set_location((0.0, 0.0, 0.75))
            .set_shading("smooth")
            .set_material(material)
        )

        self.objects.plane("Ground", size=10.0).set_material(
            self.materials.basic("GroundMaterial").set_params(
                base_color=(0.12, 0.12, 0.12),
                roughness=0.9,
            )
        )

        focus = self.objects.empty("Focus").set_location((0.0, 0.0, 0.75))
        self.camera.set_location((3.0, -3.0, 1.8)).point_at(focus)
        self.lights.point("Key", power=80.0).set_location((2.0, -2.0, 3.0))
