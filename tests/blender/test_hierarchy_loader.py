import pathlib
import tempfile
import unittest

import bpy
import rv


class _TestScene(rv.Scene):
    def generate(self):
        pass


class HierarchyLoaderTest(unittest.TestCase):
    def setUp(self):
        rv.begin_run(purge_orphans=True)
        self.scene = _TestScene()

    def test_load_hierarchy_instantiates_children(self):
        root_name = "HierarchyRoot"
        child_name = "HierarchyChild"

        root = self.scene.create_empty(name=root_name).set_location((1.0, 2.0, 3.0))
        child = self.scene.create_cube(name=child_name, size=2.0).set_location(
            (0.0, 0.0, 1.0)
        )
        child.obj.parent = root.obj
        child.obj.matrix_parent_inverse = root.obj.matrix_world.inverted()

        with tempfile.TemporaryDirectory() as tmpdir:
            blend_path = pathlib.Path(tmpdir) / "hierarchy_asset.blend"
            result = bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), copy=True)
            self.assertEqual({"FINISHED"}, set(result))

            rv.begin_run(purge_orphans=True)
            self.scene = _TestScene()

            loader = self.scene.load_hierarchy(str(blend_path), root_name=root_name)
            instance = loader.create_instance(name="ImportedHierarchy")

            imported_child = instance.find_child(child_name)
            self.assertIsNotNone(imported_child)
            self.assertIs(imported_child.obj.parent, instance.obj)

            bounds = instance.get_bounds(space="world")
            self.assertGreater(bounds["size"][0], 0.0)
            self.assertGreater(bounds["size"][1], 0.0)
            self.assertGreater(bounds["size"][2], 0.0)


if __name__ == "__main__":
    unittest.main()
