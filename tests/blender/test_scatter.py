import math
import unittest

import rv
import rv.internal as rvi


class _TestScene(rv.Scene):
    def generate(self):
        pass


class ScatterTest(unittest.TestCase):
    def setUp(self):
        rvi._internal_begin_run(purge_orphans=True)
        self.scene = _TestScene()

    def test_domain_ellipse_contains(self):
        domain = rv.Domain.ellipse(center=(0.0, 0.0), radii=(4.0, 2.0), z=1.0)
        self.assertTrue(domain.contains_point(rv.mathutils.Vector((0.0, 0.0, 1.0))))
        self.assertFalse(domain.contains_point(rv.mathutils.Vector((10.0, 0.0, 1.0))))

    def test_bounds_scatter_non_overlap_2d(self):
        prototype = self.scene.create_cube(size=1.0)
        loader = prototype.as_loader()
        domain = rv.Domain.rect(center=(0.0, 0.0), size=(15.0, 15.0), z=0.5)
        placed = self.scene.scatter(
            source=loader,
            count=20,
            domain=domain,
            method="fast",
            gap=0.1,
            seed=1,
            unique_data=True,
        )
        self.assertGreater(len(placed), 0)
        self.assertIsNot(placed[0].obj.data, prototype.obj.data)
        for i in range(len(placed)):
            for j in range(i + 1, len(placed)):
                a = placed[i].get_location()
                b = placed[j].get_location()
                self.assertGreater(math.hypot(a[0] - b[0], a[1] - b[1]), 0.1)


if __name__ == "__main__":
    unittest.main()
