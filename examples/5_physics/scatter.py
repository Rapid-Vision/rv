import rv


def box(scene, base_length, height):
    box_center = scene.create_empty("BoxCenter").set_location((0, 0, height / 2.0))

    wall = (
        scene.create_plane(name="wall_1", size=1.0)
        .set_scale((base_length, 1.0, height))
        .set_location((0.0, base_length / 2.0, height / 2.0))
        .point_at(box_center)
        .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
    )
    wall = (
        scene.create_plane(name="wall_2", size=1.0)
        .set_scale((base_length, 1.0, height))
        .set_location((0.0, -base_length / 2.0, height / 2.0))
        .point_at(box_center)
        .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
    )

    wall = (
        scene.create_plane(name="wall_3", size=1.0)
        .set_scale((1.0, base_length, height))
        .set_location((base_length / 2.0, 0.0, height / 2.0))
        .point_at(box_center, 90)
        .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
    )

    wall = (
        scene.create_plane(name="wall_4", size=1.0)
        .set_scale((1.0, base_length, height))
        .set_location((-base_length / 2.0, 0.0, height / 2.0))
        .point_at(box_center, 90)
        .add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
    )


class PhysicsScatterScene(rv.Scene):
    def generate(self, seed):
        self.set_passes([rv.RenderPass.Z])
        self.get_world().set_params(sun_intensity=0.05, strength=0.4)

        base_length = 5
        height = 1

        box(self, base_length, height)

        floor = self.create_plane(name="Floor", size=base_length).set_location(
            (0.0, 0.0, 0.0)
        )
        floor.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
        floor.set_tags("box")

        cube_source = self.create_cube(name="ScatterSourceCube", size=0.5).set_location(
            (0.0, 0.0, -1000.0)
        )
        spawn_domain = rv.Domain.box(
            center=(0.0, 0.0, height + 3.6),
            size=(1.8, 1.8, 7.2),
        )

        def configure_cube(cube, _rng, index):
            cube.obj.name = f"Cube_{index}"
            cube.add_rigidbody(
                mode="box",
                body_type="ACTIVE",
                mass=0.2,
                friction=0.7,
                collision_margin=0.01,
                use_deactivation=True,
                deactivate_linear_velocity=0.08,
                deactivate_angular_velocity=0.12,
            )
            cube.set_tags("cube")

        self.scatter(
            source=cube_source.as_loader(),
            count=30,
            domain=spawn_domain,
            method="fast",
            gap=0.03,
            rotation="free",
            seed=seed,
            unique_data=True,
            on_create=configure_cube,
        )
        cube_source.hide(view="none")

        rv.simulate_physics(
            frames=180,
            substeps=16,
            solver_iterations=40,
            use_split_impulse=True,
            time_scale=1.0,
        )

        look_at = self.create_empty("LookAt").set_location((0.0, 0.0, 0.9))
        self.get_camera().set_location((5.0, -5.0, 4.0)).point_at(look_at)
