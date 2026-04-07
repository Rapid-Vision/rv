import rv


class RustySemanticScene(rv.Scene):
    def generate(self, seed):
        self.world.set_params(sun_intensity=0.03)

        # This material must exist in ./rusty_metal.blend.
        # Its node graph should output semantic masks to AOV names:
        # - rust
        # - clean_metal
        rusty_material = self.materials.imported("./rusty_metal.blend", "RustyMetal")

        panel = (
            self.objects.sphere(radius=1)
            .set_shading("smooth")
            .set_location((0, 0, 1))
            .set_material(rusty_material)
            .set_tags("metal_panel")
        )
        self.objects.plane(size=100).set_location((0, 0, 0))

        self.enable_semantic_channels("rust", "clean_metal")
        self.set_semantic_mask_threshold(0.5)

        target = self.objects.empty().set_location(panel.get_location())
        self.camera.set_location((5.5, 5.5, 2.7)).point_at(target)
