# Feature Overview

`rv` is built around a simple idea: keep scene generation in Python, but reuse Blender's modeling, shading, geometry nodes, physics, and rendering stack for the heavy lifting.

The examples in [`examples/`](/home/mishapankin/Work/RapidVision/rv/examples) cover the main workflows you will use in practice. This page summarizes those features and points to the corresponding example scripts.

## Build scenes with a small Python API

At the core of `rv` is a `Scene` class. You create objects, materials, lights, and cameras directly from Python:

```python
class MyScene(rv.Scene):
```

```python
self.create_cube().set_location((1, 0, 0.5))
```

```python
self.create_sphere().set_shading("smooth")
```

```python
self.get_camera().set_location((5, 5, 2)).point_at(target)
```

This keeps scene generation compact while still giving you access to Blender-native behavior. See [`examples/1_primitives/scene.py`](/home/mishapankin/Work/RapidVision/rv/examples/1_primitives/scene.py).

## Import reusable assets from `.blend` files

When geometry is more complex than a few primitives, keep it in Blender and instantiate it from Python. `rv` loads named objects from a `.blend` file and returns an `ObjectLoader`:

```python
rock_loader = self.load_object("./rock.blend", "Rock")
```

```python
rock = rock_loader.create_instance()
```

This is the recommended workflow for artist-made assets, procedural Blender setups, and scenes you want to reuse across multiple dataset scripts. See [`examples/2_properties/scene.py`](/home/mishapankin/Work/RapidVision/rv/examples/2_properties/scene.py).

## Drive Blender node setups with object properties

Synthetic data usually needs variability. In `rv`, the preferred way to expose that variability is to keep procedural logic in Blender and drive it from Python using object properties.

```python
rock.set_property("geo_seed", random.uniform(0, 1000))
```

```python
rock.set_property("color_base", random.choice([light_base, dark_base]))
```

```python
rock.set_property("highlight_color", [0.35, 0.25, 0.2])
```

This pattern works well for both geometry nodes and material nodes.

### Material nodes

To control a material from Python:

1. Add an `Attribute` node inside the material node graph.
2. Set the attribute name, for example `color_base`.
3. Set **Attribute Type** to **Object**.
4. Read that value in the shader and assign it with `set_property(...)`.

Minimal Python side:

```python
obj.set_property("color_base", (0.93, 0.92, 0.91))
```

### Geometry nodes

To control geometry nodes from Python:

1. Expose a geometry nodes input in Blender.
2. Wire that input to a custom object property with a driver.
3. Change the property from Python with `set_property(...)`.

Minimal Python side:

```python
obj.set_property("geo_seed", 123.4)
```

This keeps procedural modeling inside Blender, while Python only supplies randomized parameters.

## Scatter many objects without manual placement

`rv` includes multiple geometry-based scattering workflows for filling a domain with many objects while keeping them separated.

Create a domain:

```python
domain = rv.Domain.ellipse(center=(0, 0), radii=(12, 6), z=0.0)
```

Scatter simple instances:

```python
self.scatter_by_sphere(source=loader, count=350, domain=domain, min_gap=0.15)
```

Scatter with mesh-aware placement:

```python
self.scatter_by_bvh(source=loader, count=300, domain=domain, min_gap=0.2)
```

Scatter procedural instances with per-object parameters:

```python
self.scatter_parametric(source=source, count=30, domain=domain, strategy="bvh")
```

The available example scenes show three useful patterns:

- [`examples/3_scattering/ellipse_2d.py`](/home/mishapankin/Work/RapidVision/rv/examples/3_scattering/ellipse_2d.py): fast planar scattering inside an ellipse.
- [`examples/3_scattering/hull_3d.py`](/home/mishapankin/Work/RapidVision/rv/examples/3_scattering/hull_3d.py): fill a 3D convex hull volume.
- [`examples/3_scattering/parametric_scatter.py`](/home/mishapankin/Work/RapidVision/rv/examples/3_scattering/parametric_scatter.py): vary each placed instance with a sampler/applier pair.

For many synthetic scenes this is enough. If you need physically plausible final resting poses, use rigid body simulation after or instead of geometric scattering.

## Export semantic material masks with shader AOVs

Object tags are useful for instance-level labeling, but many datasets also need masks for material regions such as rust, dirt, paint, or wear. `rv` supports this through Blender shader AOVs.

On the Blender side, write your mask into an `Output AOV` node named `SEM_<channel>`:

```text
SEM_rust
```

Enable the same channel in Python:

```python
self.enable_semantic_channels("rust", "clean_metal")
```

Optionally control binarization:

```python
self.set_semantic_mask_threshold(0.5)
```

When rendered, `rv` exports semantic masks such as `Mask_rust*.png` and `Mask_clean_metal*.png`. See [`examples/4_semantic_aov/scene.py`](/home/mishapankin/Work/RapidVision/rv/examples/4_semantic_aov/scene.py) and [`examples/4_semantic_aov/README.md`](/home/mishapankin/Work/RapidVision/rv/examples/4_semantic_aov/README.md).

## Use Blender rigid body physics when placement must look real

For piles, collisions, toppling objects, or any scene where contact matters, `rv` lets you set up rigid bodies and run Blender physics directly from the script.

Add rigid bodies:

```python
plane.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
```

```python
cube.add_rigidbody(mode="box", body_type="ACTIVE", mass=0.2)
```

Run the simulation:

```python
rv.simulate_physics(frames=120, substeps=10, time_scale=1.0)
```

This is especially useful for generating non-intersecting object piles and impact scenes. The physics examples include:

- [`examples/5_physics/simple.py`](/home/mishapankin/Work/RapidVision/rv/examples/5_physics/simple.py): a minimal falling-object setup.
- [`examples/5_physics/scatter.py`](/home/mishapankin/Work/RapidVision/rv/examples/5_physics/scatter.py): drop many randomized cubes into a box.
- [`examples/5_physics/wall_break.py`](/home/mishapankin/Work/RapidVision/rv/examples/5_physics/wall_break.py): simulate an impact that breaks a wall.

## Export generated scenes and reuse them later

Some scenes are expensive to build, especially if they depend on simulation. `rv` can save the generated result as a `.blend` file and reuse it in another script.

Export a scene:

```bash
rv export examples/6_export/export.py -o examples/6_export/exported.blend --freeze-physics
```

Load the saved objects later:

```python
loaders = self.load_objects(str(EXPORTED_BLEND), import_names=CUBE_NAMES)
```

Instantiate them as many times as needed:

```python
obj = loader.create_instance()
```

This is useful when you want to simulate once and then render many camera or lighting variations from the saved result. See [`examples/6_export/export.py`](/home/mishapankin/Work/RapidVision/rv/examples/6_export/export.py), [`examples/6_export/import.py`](/home/mishapankin/Work/RapidVision/rv/examples/6_export/import.py), and [`examples/6_export/README.md`](/home/mishapankin/Work/RapidVision/rv/examples/6_export/README.md).

## Typical workflow

In practice, many dataset scripts follow the same pattern:

1. Build or import assets.
2. Randomize object properties that drive Blender nodes.
3. Place objects with scattering or physics.
4. Add tags, semantic channels, and render passes.
5. Render with `rv render` or save an intermediate scene with `rv export`.

Start with the small examples in [`examples/`](/home/mishapankin/Work/RapidVision/rv/examples), then use the [API reference](/api/) when you need the full method signatures.
