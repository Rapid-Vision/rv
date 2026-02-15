# Example 4: Semantic Material Masks from Blender Nodes

This example expects a Blender file at:

- `examples/4_semantic_aov/rusty_metal.blend`

and a material inside it named:

- `RustyMetal`

The material must write semantic masks into shader AOV outputs named:

- `SEM_rust`
- `SEM_clean_metal`

`rv` will export them as:

- `Mask_rust*.png`
- `Mask_clean_metal*.png`

## Blender setup (`rusty_metal.blend`)

1. Open Blender and create/select a material. Rename it to `RustyMetal`.
2. Build your rust blending using shader nodes (any approach is fine).
3. Create a scalar rust mask in the node tree (0 for clean metal, 1 for rust).
4. Add node `Output AOV` and set its AOV name to `SEM_rust`.
5. Connect the rust mask to the AOV node input.
6. Add another `Output AOV` node with AOV name `SEM_clean_metal`.
7. Add a `Math` node set to `Subtract` with value `1 - rust_mask`, and connect that to `SEM_clean_metal`.
8. Save the file as `examples/4_semantic_aov/rusty_metal.blend`.

Notes:
- You do not need to manually configure View Layer AOV passes for this workflow. `rv` registers configured semantic channels automatically during render.
- Keep AOV names exactly `SEM_rust` and `SEM_clean_metal` to match the scene script.

## Run

From repo root:

```bash
rv render examples/4_semantic_aov/scene.py --cwd examples/4_semantic_aov
```

Result:
- Color image(s)
- Index masks
- Semantic masks `Mask_rust*.png`, `Mask_clean_metal*.png`
- `_meta.json` containing semantic channel configuration
