import bpy
import rv

class MyScene(rv.Scene):
    def generate(self):
        for i in range(3):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1, enter_editmode=False, align='WORLD', location=(i, 0, 0), scale=(1, 1, 1))