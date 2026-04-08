import rv


def cubes_grid(scene: rv.Scene):
    for i in range(3):
        for j in range(3):
            scene.objects.cube().set_location([i, j, 0.5]).set_scale(0.2)
