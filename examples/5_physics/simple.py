import rv


class SimplePhysicsScene(rv.Scene):
    def generate(self, seed):
        self.set_passes([rv.RenderPass.Z])
        self.world.set_params(sun_intensity=0.05, strength=1.0)

        plane = self.objects.plane(name="Ground", size=12).set_location((0.0, 0.0, 0.0))
        plane.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        plane.set_tags("ground")

        falling_box = (
            self.objects.cube(name="FallingBox", size=1)
            .set_location((2, 0.0, 3))
            .set_scale((5.0, 1.0, 1.0))
        )
        falling_box.add_rigidbody(mode="box", body_type="ACTIVE")

        static_box = self.objects.cube(name="StaticBox").set_location((0, 0, 1))
        static_box.add_rigidbody(mode="box", body_type="PASSIVE")

        rv.simulate_physics(frames=30, substeps=5, time_scale=1.0)

        target = self.objects.empty("LookAt").set_location((0.0, 0.0, 0.4))
        self.camera.set_location((5, -5, 3)).point_at(target)
