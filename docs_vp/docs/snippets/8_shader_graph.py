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
