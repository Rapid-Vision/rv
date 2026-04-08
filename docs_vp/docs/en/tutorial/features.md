# Feature Overview

`rv` is built around a simple idea: keep scene generation in Python, but reuse Blender's modeling, shading, geometry nodes, physics, and rendering stack for the heavy lifting.

The examples in [`examples/`](https://github.com/Rapid-Vision/rv/blob/main/examples) cover the main workflows you will use in practice. This page summarizes those features and points to the corresponding example scripts.

## Build scenes with a small Python API

At the core of `rv` is a `Scene` class. You create objects, materials, lights, and cameras directly from Python:

<<<@/snippets/1_basic_scene.py{python:line-numbers}

This keeps scene generation compact while still giving you access to Blender-native behavior. See [`examples/1_primitives/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/1_primitives/scene.py).

### IDE support
Use `rv python install` command to add `rv` to the current active python virtual environement. This will add code completion for `rv` into your IDE of choice. It is recommended to create an empty virtual environment from scartch. It will not be used in the runtime, it is meant for IDE support only.

## Live preview

`rv preview` watches your scene script, reloads it on change, and gives you a fast iteration loop before running a full render.

The default mode opens a Blender window:

```bash
rv preview examples/1_primitives/scene.py
```

Use this when you want the normal interactive Blender view while editing geometry, materials, lighting, or camera placement.

If you want rendered preview outputs written to disk on every change, enable preview files:

```bash
rv preview examples/1_primitives/scene.py --preview-files
```

This combined mode does both: it keeps the Blender window open and also writes a single preview sample into `./preview_out` by default. You can change the output folder with `--preview-out`, set the image size with `--resolution WIDTH,HEIGHT`, and limit render time with `--time-limit`.

For a headless workflow, add `--no-window` together with `--preview-files`:

```bash
rv preview examples/1_primitives/scene.py --preview-files --no-window
```

This mode does not open Blender. Instead, it continuously refreshes the preview files on disk, which is useful for remote environments or when you only want image outputs.

**TLDR;** Live-preview workflows are:

1. Default: Blender window only.
2. Headless: `--preview-files --no-window`.
3. Combined: `--preview-files` for Blender window plus rendered preview files on disk.


## Import reusable assets from `.blend` files

When geometry is more complex than a few primitives, design it in Blender and import from Python. `rv` loads named objects from a `.blend` file and returns an `ObjectLoader`:

```python
rock_loader = self.assets.object("./rock.blend", "Rock")
rock = rock_loader.create_instance()
```

This is the recommended workflow for artist-made assets, procedural Blender setups, and scenes you want to reuse across multiple dataset scripts. See [`examples/2_properties/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/2_properties/scene.py).

## Building shader graph

`rv` can also build Blender shader graphs directly from code, which makes it possible to define materials procedurally from Python instead of preparing every node setup by hand.

<<<@/snippets/8_shader_graph.py{python:line-numbers}

This feature is still in development. Most shader nodes are not available yet, so for now it should be treated as experimental.

## Parametrize the scene 

Synthetic data usually needs variability. In `rv`, the preferred way to expose that variability is to keep procedural logic in Blender and drive it from Python using object properties.


### Material nodes

To control a material from Python:

1. Add an `Attribute` node inside the material node graph.
![Attribute node](/assets/attribute_node.png)
2. Set the attribute name, for example `color_base`.
3. Set **Attribute Type** to **Object**.
4. Read that value in the shader and assign it with `set_property(...)`.

```python
obj.set_property("color_base", (0.93, 0.92, 0.91))
```

### Modifiers

For procedural object generation, a good pattern is to keep the modeling logic inside a Geometry Nodes modifier and parameterize it from Python.

To control a Geometry Nodes modifier from Python:

1. Add a Geometry Nodes modifier to the object in Blender.
2. Expose the inputs you want to randomize on the modifier interface.
3. Change those inputs from Python with `set_modifier_input(...)`.

Minimal Python side:

```python
obj.set_modifier_input("seed", 123.4)
```

If the object has multiple Geometry Nodes modifiers, pass `modifier_name` as well:

```python
obj.set_modifier_input("seed", 123.4, modifier_name="RockGenerator")
```

This keeps procedural modeling inside Blender, while Python only supplies the randomized parameters that drive the modifier.

Note that this workflow is not limited to Geometry Nodes modifiers and can by applied to other modifiers as well.

## Scatter many objects without manual placement

`rv` includes multiple geometry-based scattering workflows for filling a domain with many objects while keeping them separated.

Create a domain:

```python
domain = rv.Domain.ellipse(center=(0, 0), radii=(12, 6), z=0.0)
```

Scatter simple instances:

```python
self.scatter_by_sphere(source=object_loader, count=350, domain=domain, min_gap=0.15)
```

Scatter with mesh-aware placement:

```python
self.scatter_by_bvh(source=object_loader, count=300, domain=domain, min_gap=0.2)
```

Scatter procedural instances with per-object parameters:

```python
self.scatter_parametric(source=source, count=30, domain=domain, strategy="bvh")
```

The available example scenes show three useful patterns:

- [`examples/3_scattering/ellipse_2d.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/ellipse_2d.py): fast planar scattering inside an ellipse.
- [`examples/3_scattering/hull_3d.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/hull_3d.py): fill a 3D convex hull volume.
- [`examples/3_scattering/parametric_scatter.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/parametric_scatter.py): vary each placed instance with a sampler/applier pair.
- [`examples/3_scattering/custom_domain.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/custom_domain.py): define a custom 3D domain for the region `abs(z) > x^2 + y^2`.

You can also define your own scatter domain by providing membership and bounding-box functions:

```python
domain = rv.Domain.custom(
    dimension=3,
    contains_point=lambda point, margin: (
        (point.z * point.z) < (point.x * point.x + point.y * point.y)
    ),
    aabb=lambda inset_margin: (
        rv.Vector((-10.0, -10.0, -6.0)),
        rv.Vector((10.0, 10.0, 6.0)),
    ),
)
```

For many synthetic scenes this is enough. If you need physically plausible final resting positions, use rigid body simulation after or instead of geometric scattering.

## Export semantic material masks with shader AOVs

Object tags are useful for instance-level labeling, but many datasets also need masks for material regions such as rust, dirt, paint, or wear. `rv` supports this through Blender shader AOVs.

On the Blender side, write your mask into an `AOV Output` node named `<channel>`:

```text
rust
```

![AO](/assets/aov_output.png)

Enable the same channel in Python:

```python
self.enable_semantic_channels("rust", "clean_metal")
```

Optionally control binarization:

```python
self.set_semantic_mask_threshold(0.5)
```

When rendered, `rv` exports semantic masks such as `Mask_rust*.png` and `Mask_clean_metal*.png`. See [`examples/4_semantic_aov/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/4_semantic_aov/scene.py) and [`examples/4_semantic_aov/README.md`](https://github.com/Rapid-Vision/rv/blob/main/examples/4_semantic_aov/README.md).

## Use Blender rigid body physics when placement must look real

For piles, collisions, toppling objects, or any scene where contact matters, `rv` lets you set up rigid bodies and run Blender physics directly from the script.

Add rigid bodies:

```python
plane.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
```

```python
cube.add_rigidbody(
    mode="box",
    body_type="ACTIVE",
    mass=0.2,
    collision_margin=0.01,
    use_deactivation=True,
    deactivate_linear_velocity=0.15,
    deactivate_angular_velocity=0.2,
)
```

Run the simulation:

```python
rv.simulate_physics(
    frames=120,
    substeps=12,
    solver_iterations=30,
    use_split_impulse=True,
    time_scale=1.0,
)
```

This is especially useful for generating non-intersecting object piles and impact scenes. The physics examples include:

- [`examples/5_physics/simple.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/5_physics/simple.py): a minimal falling-object setup.
- [`examples/5_physics/scatter.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/5_physics/scatter.py): drop many randomized cubes into a box.
- [`examples/5_physics/wall_break.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/5_physics/wall_break.py): simulate an impact that breaks a wall.

## Export generated scenes and reuse them later

Some scenes are expensive to build, especially if they depend on simulation. `rv` can save the generated result as a `.blend` file and reuse it in another script.

Export a scene:

```bash
rv export examples/6_export/export.py -o examples/6_export/exported.blend --freeze-physics
```

Load the saved objects later:

```python
loaders = self.assets.objects("exported.blend", import_names=CUBE_NAMES)
```

Instantiate them as many times as needed:

```python
obj = loader.create_instance()
```

This is useful when you want to simulate once and then render many camera or lighting variations from the saved result. See [`examples/6_export/export.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/export.py), [`examples/6_export/import.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/import.py), and [`examples/6_export/README.md`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/README.md).

## Preview textures
Exported depth and index masks are not comprehendable by human eye. Thats why `rv` exports additional preview masks alongside them.

<div class="image_block">
    <img alt="Preview Depth" src="/assets/depth_preview.png" style="width: 100%;" />
    <img alt="Preview Index" src="/assets/index_preview.png" style="width: 100%;" />
</div>

## Additional information

Start with the small examples in [`examples/`](https://github.com/Rapid-Vision/rv/blob/main/examples), then use the [API reference](/en/api/) when you need the full method signatures.
