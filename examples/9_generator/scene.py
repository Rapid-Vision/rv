import rv


class SeedTextureScene(rv.Scene):
    def generate(self, seed):
        self.world = rv.SkyWorld().set_params(strength=0.2, sun_intensity=0.05)

        generator = self.generators.init("uv run ./gen.py")
        texture_path = generator.generate("seed_texture")

        material = rv.ShaderMaterial(
            rv.PrincipledBSDF(
                base_color=rv.TextureImage(texture_path),
                roughness=0.55,
                specular=0.25,
            ),
            name="SeedTextureMaterial",
        )

        plane = (
            self.objects.plane("SeedPlane", size=2.5)
            .set_location((0.0, 0.0, 0.0))
            .set_material(material)
            .set_tags("seed_plane")
        )

        focus = self.objects.empty("Focus").set_location(plane.get_location())
        self.camera.set_location((0.0, -2.8, 2.0)).point_at(focus)
        self.lights.point("Key", power=90.0).set_location((1.8, -1.5, 2.8))
