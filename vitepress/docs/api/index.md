# File: `rv.py`

Module for describing an `rv` scenes. To create a scene implement a class derrived from `Scene`.

- To preview scene use the `rv preview <scene.py>` command.
- To render resulting dataset use the `rv render <scene.py>` command.

### Scene example
Here is a basic non-random scene with a cube and a sphere.
To preview resulting segmentation masks see the `PreviewIndexOB0001.png` after rendering.
```python
class BasicScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        cube = (
            self.create_cube().set_location((1, 0, 0.5)).set_scale(0.5).set_tags("cube")
        )
        sphere = (
            self.create_sphere()
            .set_location((-1, 0, 1))
            .set_shading("smooth")
            .set_tags("sphere")
        )
        plane = self.create_plane(size=1000)
        empty = self.create_empty().set_location((0, 0, 1))
        key_light = self.create_area_light(power=250).set_location((4, -4, 6)).point_at(
            empty
        )

        cam = self.get_camera().set_location((7, 7, 3)).point_at(empty)
```

### Results
| Image | Segmentation |
| :-: | :-: |
| ![resulting image](/examples/1_primitives/1_res.png) | ![resulting image](/examples/1_primitives/1_segs.png)|

## Classes

### `class ObjectStats` {#class-objectstats}
Geometric inspection snapshot for an object or loader instance.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `name` | `str` |  |
| `type` | `str` |  |
| `dimensions_world` | `Float3` |  |
| `dimensions_local` | `Float3` |  |
| `bounds_world` | `dict[str, Float3]` |  |
| `bounds_local` | `dict[str, Float3]` |  |
| `scale` | `Float3` |  |

:::

::: details Methods

---
#### `to_dict`

Convert to JSON-compatible dictionary for metadata serialization.

**Signature**

```python
def to_dict(self) -> dict[str, JSONSerializable]
```

**Arguments**


**Returns**: `dict[str, JSONSerializable]`

---
:::

---

### `class Domain` {#class-domain}
Scatter domain descriptor used by scene scattering methods.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `kind` | `str` | Domain kind identifier (rect, ellipse, hull3d, etc.) |
| `data` | `dict` | Domain parameters required by sampling/containment logic |
| `dimension` | `int` | Domain dimensionality (2 for planar, 3 for volumetric) |

:::

::: details Methods

---
#### `inset`

Return a new domain shrunk inward by `margin`.

**Signature**

```python
def inset(self, margin: float) -> 'Domain'
```

**Arguments**

- **`margin`** : `float` — Inset distance from the domain boundary

**Returns**: `'Domain'`

---
---
#### `rect`

Build a rectangular 2D scatter domain.

**Signature**

```python
@staticmethod
def rect(center: Float2=(0.0, 0.0), size: Float2=(10.0, 10.0), z: float=0.0) -> 'Domain'
```

**Arguments**

- **`center`** : `Float2` — XY center of the rectangle
- **`size`** : `Float2` — Rectangle width and depth
- **`z`** : `float` — Fixed Z plane for 2D scattering

**Returns**: `'Domain'`

---
---
#### `ellipse`

Build an elliptical 2D scatter domain.

**Signature**

```python
@staticmethod
def ellipse(center: Float2=(0.0, 0.0), radii: Float2=(5.0, 3.0), z: float=0.0) -> 'Domain'
```

**Arguments**

- **`center`** : `Float2` — XY center of the ellipse
- **`radii`** : `Float2` — Ellipse radii along X and Y
- **`z`** : `float` — Fixed Z plane for 2D scattering

**Returns**: `'Domain'`

---
---
#### `polygon`

Build a convex 2D scatter domain from polygon vertices.

**Signature**

```python
@staticmethod
def polygon(points: Polygon2D, z: float=0.0) -> 'Domain'
```

**Arguments**

- **`points`** : `Polygon2D` — Polygon vertices in XY
- **`z`** : `float` — Fixed Z plane for 2D scattering

**Returns**: `'Domain'`

---
---
#### `box`

Build an axis-aligned box scatter domain.

**Signature**

```python
@staticmethod
def box(center: Float3=(0.0, 0.0, 0.0), size: Float3=(10.0, 10.0, 10.0)) -> 'Domain'
```

**Arguments**

- **`center`** : `Float3` — 3D center
- **`size`** : `Float3` — Box side lengths

**Returns**: `'Domain'`

---
---
#### `cylinder`

Build a cylinder scatter domain aligned to X, Y, or Z.

**Signature**

```python
@staticmethod
def cylinder(center: Float3=(0.0, 0.0, 0.0), radius: float=5.0, height: float=10.0, axis: str='Z') -> 'Domain'
```

**Arguments**

- **`center`** : `Float3` — Cylinder center
- **`radius`** : `float` — Radial extent
- **`height`** : `float` — Length along the selected axis
- **`axis`** : `str` — Longitudinal axis: X, Y, or Z

**Returns**: `'Domain'`

---
---
#### `ellipsoid`

Build an ellipsoid scatter domain.

**Signature**

```python
@staticmethod
def ellipsoid(center: Float3=(0.0, 0.0, 0.0), radii: Float3=(5.0, 3.0, 2.0)) -> 'Domain'
```

**Arguments**

- **`center`** : `Float3` — Ellipsoid center
- **`radii`** : `Float3` — Radii along X, Y, Z

**Returns**: `'Domain'`

---
---
#### `convex_hull`

Build a convex hull domain from an existing object.

**Signature**

```python
@staticmethod
def convex_hull(rv_obj: 'Object', project_2d: bool=False) -> 'Domain'
```

**Arguments**

- **`rv_obj`** : `'Object'` — Source object to build the hull from
- **`project_2d`** : `bool` — If true, project hull to XY polygon

**Returns**: `'Domain'`

---
---
#### `sample_point`

Sample a random point inside this domain.

**Signature**

```python
def sample_point(self, rng: random.Random) -> mathutils.Vector
```

**Arguments**

- **`rng`** : `random.Random` — Random generator

**Returns**: `mathutils.Vector`

---
---
#### `contains_point`

Check whether a world-space point is inside the domain.

**Signature**

```python
def contains_point(self, point: mathutils.Vector, margin: float=0.0) -> bool
```

**Arguments**

- **`point`** : `mathutils.Vector` — Candidate point in world coordinates
- **`margin`** : `float` — Inset margin from boundary

**Returns**: `bool`

---
---
#### `contains_object`

Check whether an object is fully contained within this domain.

**Signature**

```python
def contains_object(self, obj: 'Object', margin: float=0.0, mode: Literal['aabb', 'mesh']='mesh') -> bool
```

**Arguments**

- **`obj`** : `'Object'` — Object to validate against this domain
- **`margin`** : `float` — Additional inset margin
- **`mode`** : `Literal['aabb', 'mesh']` — Containment strategy

**Returns**: `bool`

---
---
#### `aabb`

Return the axis-aligned bounds of this domain.

**Signature**

```python
def aabb(self) -> AABB
```

**Arguments**


**Returns**: `AABB`

---
:::

---

### `class Scene` {#class-scene}
Inherits from: `ABC`, `_Serializable`

Base class for describing rv scene. To set up a scene, implement `generate` function.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `resolution` | `Resolution` | Output image resolution (width, height) |
| `time_limit` | `float` | Per-frame render time limit in seconds |
| `passes` | `RenderPassSet` | Enabled auxiliary render passes |
| `output_dir` | `Optional[str]` | Directory for storing all outputs generated by a single `rv render` run |
| `subdir` | `str` | Directory to store results of a single rendering |
| `camera` | `'Camera'` | Scene camera wrapper |
| `world` | `'World'` | Active environment lighting descriptor |
| `tags` | `TagSet` | Scene-level classification tags |
| `objects` | `set['Object']` | Registered scene objects |
| `materials` | `set['Material']` | Registered material descriptors |
| `lights` | `set['Light']` | Registered lights |
| `semantic_channels` | `SemanticChannelSet` | Semantic mask channels exported from shader AOVs |
| `semantic_mask_threshold` | `float` | Binary threshold for semantic masks |
| `object_index_counter` | `int` | Monotonic object pass-index counter |
| `material_index_counter` | `int` | Monotonic material pass-index counter |
| `light_index_counter` | `int` | Monotonic light index counter |

:::

::: details Methods

---
#### `generate`

Method to describe scene generation. To use framework you must implement it in a derrived class.

**Signature**

```python
@abstractmethod
def generate(self) -> None
```

**Arguments**


**Returns**: `None`

---
---
#### `set_rendering_time_limit`

Set the maximum allowed rendering time for a single image. Higher value leads to better quality.

**Signature**

```python
def set_rendering_time_limit(self, time_limit: float=3.0)
```

**Arguments**

- **`time_limit`** : `float` — Rendering time limit in seconds

**Returns**: `Self`

---
---
#### `set_passes`

Set a list of render passes that will be saved when rendering.

**Signature**

```python
def set_passes(self, *passes: tuple[RenderPass | list[RenderPass], ...])
```

**Arguments**

- **`*passes`** : `tuple[RenderPass | list[RenderPass], ...]` — Render passes to enable

**Returns**: `Self`

---
---
#### `enable_semantic_channels`

Enable semantic shader channels to be exported as masks.
In Blender node graphs, write channel values to AOV outputs named `SEM_<channel>`.

**Signature**

```python
def enable_semantic_channels(self, *channels: tuple[str | list[str], ...]) -> 'Scene'
```

**Arguments**

- **`*channels`** : `tuple[str | list[str], ...]` — Semantic channel names written via AOVs

**Returns**: `Self`

---
---
#### `set_semantic_mask_threshold`

Set threshold used when exporting binary semantic masks.

**Signature**

```python
def set_semantic_mask_threshold(self, threshold: float) -> 'Scene'
```

**Arguments**

- **`threshold`** : `float` — Binary mask threshold in [0, 1]

**Returns**: `Self`

---
---
#### `create_empty`

Create an empty object. May be useful to point camera at or for debugging during `preview` stage.

**Signature**

```python
def create_empty(self, name: str='Empty') -> 'Object'
```

**Arguments**

- **`name`** : `str` — Object name

**Returns**: `'Object'`

---
---
#### `create_sphere`

Create a sphere primitive.

**Signature**

```python
def create_sphere(self, name: str='Sphere', radius: float=1.0, segments: int=32, ring_count: int=16) -> 'Object'
```

**Arguments**

- **`name`** : `str` — Object name
- **`radius`** : `float` — Sphere radius
- **`segments`** : `int` — Horizontal segments
- **`ring_count`** : `int` — Vertical segments

**Returns**: `'Object'`

---
---
#### `create_cube`

Create a cube primitive.

**Signature**

```python
def create_cube(self, name: str='Cube', size: float=2.0) -> 'Object'
```

**Arguments**

- **`name`** : `str` — Object name
- **`size`** : `float` — Cube side size

**Returns**: `'Object'`

---
---
#### `create_plane`

Create a plane primitive.

**Signature**

```python
def create_plane(self, name: str='Plane', size: float=2.0) -> 'Object'
```

**Arguments**

- **`name`** : `str` — Object name
- **`size`** : `float` — Plane side size

**Returns**: `'Object'`

---
---
#### `create_point_light`

Create a point light.

**Signature**

```python
def create_point_light(self, name: str='Point', power: float=1000.0) -> 'PointLight'
```

**Arguments**

- **`name`** : `str` — Light object name
- **`power`** : `float` — Light power in Blender energy units

**Returns**: `'PointLight'`

---
---
#### `create_sun_light`

Create a sun light.

**Signature**

```python
def create_sun_light(self, name: str='Sun', power: float=1.0) -> 'SunLight'
```

**Arguments**

- **`name`** : `str` — Light object name
- **`power`** : `float` — Light power in Blender energy units

**Returns**: `'SunLight'`

---
---
#### `create_area_light`

Create an area light.

**Signature**

```python
def create_area_light(self, name: str='Area', power: float=100.0) -> 'AreaLight'
```

**Arguments**

- **`name`** : `str` — Light object name
- **`power`** : `float` — Light power in Blender energy units

**Returns**: `'AreaLight'`

---
---
#### `create_spot_light`

Create a spot light.

**Signature**

```python
def create_spot_light(self, name: str='Spot', power: float=1000.0) -> 'SpotLight'
```

**Arguments**

- **`name`** : `str` — Light object name
- **`power`** : `float` — Light power in Blender energy units

**Returns**: `'SpotLight'`

---
---
#### `get_camera`

Get the `Camera` object used for rendering.

**Signature**

```python
def get_camera(self) -> 'Camera'
```

**Arguments**


**Returns**: `'Camera'`

---
---
#### `set_world`

Set a new `World` representing environmental lighting.

**Signature**

```python
def set_world(self, world: 'World') -> 'World'
```

**Arguments**

- **`world`** : `'World'` — World descriptor to apply to the scene

**Returns**: `Self`

---
---
#### `get_world`

Get current used `World`.

**Signature**

```python
def get_world(self) -> 'World'
```

**Arguments**


**Returns**: `'World'`

---
---
#### `set_tags`

Set scene's global tags.

Tags are used to represent image class for training a computer vision model for a classification task.

**Signature**

```python
def set_tags(self, *tags) -> 'Scene'
```

**Arguments**

- **`*tags`** — Scene-level tags

**Returns**: `Self`

---
---
#### `add_tags`

Add tags to the scene.

Tags are used to represent image class for training a computer vision model for a classification task.

**Signature**

```python
def add_tags(self, *tags) -> 'Scene'
```

**Arguments**

- **`*tags`** — Tags to append to scene-level tags

**Returns**: `Self`

---
---
#### `load_object`

Get a loader object to import from a blender file.

If `import_name` is specified, it imports an object with specified name.
If no `import_name` is specified, it imports the first object.

Loader object is used to create instances of an object.

**Signature**

```python
def load_object(self, blendfile: str, import_name: str=None) -> 'ObjectLoader'
```

**Arguments**

- **`blendfile`** : `str` — Path to source .blend file
- **`import_name`** : `str` — Optional object name to import

**Returns**: `'ObjectLoader'`

---
---
#### `load_objects`

Get a list of loader objects to import from a blender file.

If `import_names` is specified, it imports only specified objects.
If no `import_names` is specified, it imports all specfied objects.

Loader object is used to create instances of an object.

**Signature**

```python
def load_objects(self, blendfile: str, import_names: list[str]=None) -> list['ObjectLoader']
```

**Arguments**

- **`blendfile`** : `str` — Path to source .blend file
- **`import_names`** : `list[str]` — Optional list of object names to import

**Returns**: `Self`

---
---
#### `create_material`

Create a new basic (Principled BSDF) material.

**Signature**

```python
def create_material(self, name: str='Material') -> 'BasicMaterial'
```

**Arguments**

- **`name`** : `str` — Material name

**Returns**: `'BasicMaterial'`

---
---
#### `import_material`

Create an imported material descriptor from a .blend file.

**Signature**

```python
def import_material(self, blendfile: str, material_name: str=None) -> 'ImportedMaterial'
```

**Arguments**

- **`blendfile`** : `str` — Path to source .blend file
- **`material_name`** : `str` — Material name to import (defaults to first)

**Returns**: `'ImportedMaterial'`

---
---
#### `inspect_object`

Inspect geometric stats for a loader/object without manual .blend inspection.

**Signature**

```python
def inspect_object(self, loader_or_obj: Union['ObjectLoader', 'Object'], applied_scale: bool=True) -> ObjectStats
```

**Arguments**

- **`loader_or_obj`** : `Union['ObjectLoader', 'Object']` — Object or loader to inspect
- **`applied_scale`** : `bool` — Include object scale in reported local dimensions

**Returns**: `Self`

---
---
#### `scatter_by_sphere`

Scatter objects using bounding-sphere collisions.

**Signature**

```python
def scatter_by_sphere(self, source: ObjectLoaderSource, count: int, domain: 'Domain', min_gap: float=0.0, yaw_range: Float2=(0.0, 360.0), rotation_mode: Literal['yaw', 'free']='yaw', scale_range: Float2=(1.0, 1.0), max_attempts_per_object: int=100, boundary_mode: Literal['center_margin']='center_margin', boundary_margin: float=0.0, seed: int | None=None) -> list['Object']
```

**Arguments**

- **`source`** : `ObjectLoaderSource` — Source loader(s)
- **`count`** : `int` — Requested number of objects to place
- **`domain`** : `'Domain'` — Scatter domain descriptor
- **`min_gap`** : `float` — Extra spacing between placed objects
- **`yaw_range`** : `Float2` — Yaw range in degrees
- **`rotation_mode`** : `Literal['yaw', 'free']` — Rotation sampling strategy
- **`scale_range`** : `Float2` — Uniform scale range
- **`max_attempts_per_object`** : `int` — Retry budget per requested object
- **`boundary_mode`** : `Literal['center_margin']` — Boundary policy
- **`boundary_margin`** : `float` — Required inset distance from domain edge
- **`seed`** : `int | None` — RNG seed for deterministic sampling

**Returns**: `Self`

---
---
#### `scatter_by_bvh`

Scatter objects using exact BVH overlap checks with broad-phase pruning.

**Signature**

```python
def scatter_by_bvh(self, source: ObjectLoaderSource, count: int, domain: 'Domain', min_gap: float=0.0, yaw_range: Float2=(0.0, 360.0), rotation_mode: Literal['yaw', 'free']='yaw', scale_range: Float2=(1.0, 1.0), max_attempts_per_object: int=100, boundary_mode: Literal['center_margin']='center_margin', boundary_margin: float=0.0, seed: int | None=None) -> list['Object']
```

**Arguments**

- **`source`** : `ObjectLoaderSource` — Source loader(s)
- **`count`** : `int` — Requested number of objects to place
- **`domain`** : `'Domain'` — Scatter domain descriptor
- **`min_gap`** : `float` — Extra spacing between placed objects
- **`yaw_range`** : `Float2` — Yaw range in degrees
- **`rotation_mode`** : `Literal['yaw', 'free']` — Rotation sampling strategy
- **`scale_range`** : `Float2` — Uniform scale range
- **`max_attempts_per_object`** : `int` — Retry budget per requested object
- **`boundary_mode`** : `Literal['center_margin']` — Boundary policy
- **`boundary_margin`** : `float` — Required inset distance from domain edge
- **`seed`** : `int | None` — RNG seed for deterministic sampling

**Returns**: `Self`

---
---
#### `scatter_parametric`

Scatter parameterized objects. Dimensions are measured on candidate geometry per attempt.

**Signature**

```python
def scatter_parametric(self, source: 'ParametricSource', count: int, domain: 'Domain', strategy: Literal['sphere', 'bvh']='sphere', min_gap: float=0.0, yaw_range: Float2=(0.0, 360.0), rotation_mode: Literal['yaw', 'free']='yaw', scale_range: Float2=(1.0, 1.0), max_attempts_per_object: int=100, boundary_mode: Literal['center_margin']='center_margin', boundary_margin: float=0.0, seed: int | None=None) -> list['Object']
```

**Arguments**

- **`source`** : `'ParametricSource'` — Parameterized source descriptor
- **`count`** : `int` — Requested number of objects to place
- **`domain`** : `'Domain'` — Scatter domain descriptor
- **`strategy`** : `Literal['sphere', 'bvh']` — Collision strategy
- **`min_gap`** : `float` — Extra spacing between placed objects
- **`yaw_range`** : `Float2` — Yaw range in degrees
- **`rotation_mode`** : `Literal['yaw', 'free']` — Rotation sampling strategy
- **`scale_range`** : `Float2` — Uniform scale range
- **`max_attempts_per_object`** : `int` — Retry budget per requested object
- **`boundary_mode`** : `Literal['center_margin']` — Boundary policy
- **`boundary_margin`** : `float` — Required inset distance from domain edge
- **`seed`** : `int | None` — RNG seed for deterministic sampling

**Returns**: `Self`

---
:::

---

### `class ObjectLoader` {#class-objectloader}
Helper for creating object instances from a loaded Blender object source.

::: details Methods

---
#### `set_source`

Rebind this loader to use an existing object as its instancing prototype.

**Signature**

```python
def set_source(self, source: 'Object') -> 'ObjectLoader'
```

**Arguments**

- **`source`** : `'Object'` — Object used as instancing prototype

**Returns**: `Self`

---
---
#### `create_instance`

Create a single object instance from a loader.

**Signature**

```python
def create_instance(self, name: str=None, register_object: bool=True) -> 'Object'
```

**Arguments**

- **`name`** : `str` — Instanced object name
- **`register_object`** : `bool` — Register in scene metadata/indexes

**Returns**: `'Object'`

---
:::

---

### `class ParametricSource` {#class-parametricsource}
Source wrapper for parameterized scattering.

It can sample parameters per candidate and apply them to each created instance.

::: details Methods

---
#### `set_sampler`

Set a callback that samples a parameter dictionary for each candidate.

**Signature**

```python
def set_sampler(self, sampler: typing.Callable[[random.Random], dict]) -> 'ParametricSource'
```

**Arguments**

- **`sampler`** : `typing.Callable[[random.Random], dict]` — Samples a params dict from RNG

**Returns**: `Self`

---
---
#### `set_applier`

Set a callback that applies sampled parameters to the created object.

**Signature**

```python
def set_applier(self, applier: typing.Callable[['Object', dict], None]) -> 'ParametricSource'
```

**Arguments**

- **`applier`** : `typing.Callable[['Object', dict], None]` — Applies params to created object

**Returns**: `Self`

---
---
#### `sample_params`

**Signature**

```python
def sample_params(self, rng: random.Random) -> dict
```

**Arguments**

- **`rng`** : `random.Random` — Random generator

**Returns**: `dict`

---
---
#### `create_instance`

**Signature**

```python
def create_instance(self, params: dict | None=None, register_object: bool=True, name: str=None) -> 'Object'
```

**Arguments**

- **`params`** : `dict | None` — Sampled parameter dictionary
- **`register_object`** : `bool` — Register in scene metadata/indexes
- **`name`** : `str` — Instance object name

**Returns**: `Self`

---
:::

---

### `class Material` {#class-material}
Inherits from: `ABC`, `_Serializable`

Base class for material descriptors.

A material descriptor is converted to a real Blender material when assigned to an object.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `name` | `str \| None` | Material display name |
| `index` | `int \| None` | Assigned material pass index in the scene |

:::

::: details Methods

---
#### `set_params`

Update descriptor-specific material parameters and return `self`.

**Signature**

```python
@abstractmethod
def set_params(self, **kwargs)
```

**Arguments**

- **`**kwargs`**

---
:::

---

### `class BasicMaterial` {#class-basicmaterial}
Inherits from: `Material`

Material descriptor backed by Blender's Principled BSDF shader.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `base_color` | `ColorRGBA \| None` | Principled base RGBA color |
| `roughness` | `float \| None` | Surface roughness |
| `metallic` | `float \| None` | Metallic factor |
| `specular` | `float \| None` | Specular IOR level |
| `emission_color` | `ColorRGBA \| None` | Emission RGBA color |
| `emission_strength` | `float \| None` | Emission intensity |
| `alpha` | `float \| None` | Surface alpha/transparency |
| `transmission` | `float \| None` | Transmission weight |
| `ior` | `float \| None` | Index of refraction |
| `properties` | `dict` | Custom Blender properties to set on the material |

:::

::: details Methods

---
#### `set_params`

Set Principled BSDF parameters used when building the material.

**Signature**

```python
def set_params(self, base_color: OptionalColor=None, roughness: float=None, metallic: float=None, specular: float=None, emission_color: OptionalColor=None, emission_strength: float=None, alpha: float=None, transmission: float=None, ior: float=None)
```

**Arguments**

- **`base_color`** : `OptionalColor` — Base color (RGB/RGBA)
- **`roughness`** : `float` — Surface roughness
- **`metallic`** : `float` — Metallic factor
- **`specular`** : `float` — Specular IOR level
- **`emission_color`** : `OptionalColor` — Emission color (RGB/RGBA)
- **`emission_strength`** : `float` — Emission intensity
- **`alpha`** : `float` — Alpha/transparency
- **`transmission`** : `float` — Transmission weight
- **`ior`** : `float` — Index of refraction

---
---
#### `set_property`

Set a custom Blender property on the generated material.

**Signature**

```python
def set_property(self, key: str, value: any)
```

**Arguments**

- **`key`** : `str` — Custom property key
- **`value`** : `any` — Custom property value

**Returns**: `Self`

---
:::

---

### `class ImportedMaterial` {#class-importedmaterial}
Inherits from: `Material`

Material descriptor that imports a material from another `.blend` file.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `filepath` | `str` | Source .blend file path |
| `material_name` | `str \| None` | Material name inside the .blend file |
| `params` | `dict` | Custom properties to apply after import |

:::

::: details Methods

---
#### `set_params`

Set custom properties applied to the imported material.

**Signature**

```python
def set_params(self, **kwargs)
```

**Arguments**

- **`**kwargs`**

**Returns**: `Self`

---
:::

---

### `class Object` {#class-object}
Inherits from: `_Serializable`

Wrapper around a Blender object with chainable transformation and metadata helpers.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `obj` | `bpy.types.Object` | Underlying Blender object |
| `scene` | `Scene` | Owning scene |
| `tags` | `TagSet` | Object-level semantic tags |
| `properties` | `dict` | Custom properties assigned to this object |
| `index` | `int \| None` | Assigned object pass index |

:::

::: details Methods

---
#### `set_location`

Set the location of the object in 3D space.

**Signature**

```python
def set_location(self, location: Union[mathutils.Vector, typing.Sequence[float]])
```

**Arguments**

- **`location`** : `Union[mathutils.Vector, typing.Sequence[float]]` — Object location in world coordinates

**Returns**: `Self`

---
---
#### `set_rotation`

Set the rotation of the object.

**Signature**

```python
def set_rotation(self, rotation: Union[mathutils.Euler, mathutils.Quaternion])
```

**Arguments**

- **`rotation`** : `Union[mathutils.Euler, mathutils.Quaternion]` — Object rotation value

**Returns**: `Self`

---
---
#### `set_scale`

Set the scale of the object.

If `scale` is a single numeric value, all axes are set to that value.
If `scale` is a sequence or Vector of length 3, each axis is set individually.

**Signature**

```python
def set_scale(self, scale: Union[mathutils.Vector, typing.Sequence[float], float, int])
```

**Arguments**

- **`scale`** : `Union[mathutils.Vector, typing.Sequence[float], float, int]` — Uniform scalar or per-axis XYZ scale

**Returns**: `Self`

---
---
#### `set_property`

Set a property of the object. Properties can be used inside object's material nodes.

**Signature**

```python
def set_property(self, key: str, value: any)
```

**Arguments**

- **`key`** : `str` — Custom property key
- **`value`** : `any` — Custom property value

**Returns**: `Self`

---
---
#### `set_material`

Set object material in the given slot.

**Signature**

```python
def set_material(self, material: 'Material', slot: int=0)
```

**Arguments**

- **`material`** : `'Material'` — Material descriptor to assign
- **`slot`** : `int` — Material slot index

**Returns**: `Self`

---
---
#### `add_material`

Append material to object's material slots.

**Signature**

```python
def add_material(self, material: 'Material')
```

**Arguments**

- **`material`** : `'Material'` — Material descriptor to append

**Returns**: `Self`

---
---
#### `clear_materials`

Remove all materials from object.

**Signature**

```python
def clear_materials(self)
```

**Arguments**


**Returns**: `Self`

---
---
#### `set_tags`

Set object's tags.

Tags are used to represent object class for training a computer vision model. Object can have more then one tag.

**Signature**

```python
def set_tags(self, *tags: str | list[str])
```

**Arguments**

- **`*tags`** : `str | list[str]` — Object-level tags

**Returns**: `Self`

---
---
#### `add_tags`

Add tags to the object.

Tags are used to represent object class for training a computer vision model. Object can have more then one tag.

**Signature**

```python
def add_tags(self, *tags: str | list[str])
```

**Arguments**

- **`*tags`** : `str | list[str]` — Tags to append to object-level tags

**Returns**: `Self`

---
---
#### `point_at`

Orients the current object to point at another object, with an optional rotation around the direction vector.

**Signature**

```python
def point_at(self, rv_obj: 'Object', angle: float=0.0)
```

**Arguments**

- **`rv_obj`** : `'Object'` — Object to point at
- **`angle`** : `float` — Angle to rotate around the direction vector in degrees

**Returns**: `Self`

---
---
#### `rotate_around_axis`

Rotate object around an axis.

**Signature**

```python
def rotate_around_axis(self, axis: mathutils.Vector, angle: float)
```

**Arguments**

- **`axis`** : `mathutils.Vector` — Axis of rotation
- **`angle`** : `float` — Angle of rotation in degrees

**Returns**: `Self`

---
---
#### `set_shading`

Set shading to flat, smooth, or auto.

**Signature**

```python
def set_shading(self, shading: Literal['flat', 'smooth', 'auto'])
```

**Arguments**

- **`shading`** : `Literal['flat', 'smooth', 'auto']` — Target shading mode

**Returns**: `Self`

---
---
#### `show_debug_axes`

Show debug axes that can be seen in the `preview` mode.

**Signature**

```python
def show_debug_axes(self, show=True)
```

**Arguments**

- **`show`** — Toggle axis visibility in preview

**Returns**: `Self`

---
---
#### `show_debug_name`

Show object's name that can be seen in the `preview` mode.

**Signature**

```python
def show_debug_name(self, show)
```

**Arguments**

- **`show`** — Toggle object-name visibility in preview

**Returns**: `Self`

---
---
#### `hide`

Hide object from render output while controlling preview visibility.

**Signature**

```python
def hide(self, view: Literal['wireframe', 'none']='wireframe')
```

**Arguments**

- **`view`** : `Literal['wireframe', 'none']` — Preview visibility mode

**Returns**: `Self`

---
---
#### `get_dimensions`

Get object dimensions (axis-aligned extents) in world or local space.

**Signature**

```python
def get_dimensions(self, space: Literal['world', 'local']='world') -> Float3
```

**Arguments**

- **`space`** : `Literal['world', 'local']` — Coordinate space for dimensions

**Returns**: `Float3`

---
---
#### `inspect`

Inspect geometric stats for this object.

**Signature**

```python
def inspect(self, applied_scale: bool=True) -> ObjectStats
```

**Arguments**

- **`applied_scale`** : `bool` — Include object scale in local dimensions

**Returns**: `ObjectStats`

---
---
#### `get_bounds`

Get axis-aligned bounds in world or local space.

**Signature**

```python
def get_bounds(self, space: Literal['world', 'local']='world') -> dict[str, Float3]
```

**Arguments**

- **`space`** : `Literal['world', 'local']` — Coordinate space for bounds

**Returns**: `dict[str, Float3]`

---
---
#### `add_rigidbody`

Add or update rigid-body settings for this object.

**Signature**

```python
def add_rigidbody(self, mode: Literal['box', 'sphere', 'hull', 'mesh', 'capsule', 'cylinder', 'cone']='hull', body_type: Literal['ACTIVE', 'PASSIVE']='ACTIVE', mass: float=1.0, friction: float=0.5, restitution: float=0.0, linear_damping: float=0.04, angular_damping: float=0.1) -> 'Object'
```

**Arguments**

- **`mode`** : `Literal['box', 'sphere', 'hull', 'mesh', 'capsule', 'cylinder', 'cone']` — Collision shape
- **`body_type`** : `Literal['ACTIVE', 'PASSIVE']` — Rigid body type
- **`mass`** : `float` — Body mass
- **`friction`** : `float` — Surface friction
- **`restitution`** : `float` — Bounciness
- **`linear_damping`** : `float` — Linear damping factor
- **`angular_damping`** : `float` — Angular damping factor

**Returns**: `Self`

---
---
#### `remove_rigidbody`

Remove rigid body from this object if present.

**Signature**

```python
def remove_rigidbody(self, keep_transform: bool=True) -> 'Object'
```

**Arguments**

- **`keep_transform`** : `bool` — Preserve world transform after removal

**Returns**: `Self`

---
:::

---

### `class Camera` {#class-camera}
Inherits from: `Object`

`Object` specialization with camera-specific controls.

::: details Methods

---
#### `set_fov`

Sets the field of view (FOV) for the object's camera in degrees.

**Signature**

```python
def set_fov(self, angle: float)
```

**Arguments**

- **`angle`** : `float` — Camera FOV in degrees

**Returns**: `Self`

---
:::

---

### `class Light` {#class-light}
Inherits from: `Object`

Base object wrapper for Blender lights with chainable parameter setters.

::: details Methods

---
#### `light_data`

Return the underlying Blender light datablock.

**Signature**

```python
@property
def light_data(self) -> bpy.types.Light
```

**Arguments**


**Returns**: `bpy.types.Light`

---
---
#### `set_color`

Set light RGB color. Alpha (if provided) is ignored.

**Signature**

```python
def set_color(self, color: Color) -> 'Light'
```

**Arguments**

- **`color`** : `Color` — RGB/RGBA light color

**Returns**: `Self`

---
---
#### `set_power`

Set light power in Blender `energy` units.

**Signature**

```python
def set_power(self, power: float) -> 'Light'
```

**Arguments**

- **`power`** : `float` — Light power in Blender energy units

**Returns**: `Self`

---
---
#### `set_cast_shadow`

Enable or disable shadow casting.

**Signature**

```python
def set_cast_shadow(self, enabled: bool=True) -> 'Light'
```

**Arguments**

- **`enabled`** : `bool` — Shadow-casting toggle

**Returns**: `Self`

---
---
#### `set_specular_factor`

Set the light contribution to specular highlights.

**Signature**

```python
def set_specular_factor(self, factor: float) -> 'Light'
```

**Arguments**

- **`factor`** : `float` — Specular contribution factor

**Returns**: `Self`

---
---
#### `set_softness`

Set softness parameter mapped to the current light type.

**Signature**

```python
def set_softness(self, value: float) -> 'Light'
```

**Arguments**

- **`value`** : `float` — Softness parameter

**Returns**: `Self`

---
---
#### `set_params`

Set known light-data attributes or custom properties.

**Signature**

```python
def set_params(self, **kwargs) -> 'Light'
```

**Arguments**

- **`**kwargs`**

**Returns**: `Self`

---
:::

---

### `class PointLight` {#class-pointlight}
Inherits from: `Light`

Point light with radius control.

::: details Methods

---
#### `set_radius`

Set point light radius.

**Signature**

```python
def set_radius(self, radius: float) -> 'PointLight'
```

**Arguments**

- **`radius`** : `float` — Radius/soft size

**Returns**: `Self`

---
:::

---

### `class SunLight` {#class-sunlight}
Inherits from: `Light`

Directional sun light with angular size control.

::: details Methods

---
#### `set_angle`

Set sun angular size in radians.

**Signature**

```python
def set_angle(self, angle_radians: float) -> 'SunLight'
```

**Arguments**

- **`angle_radians`** : `float` — Angular sun size in radians

**Returns**: `Self`

---
:::

---

### `class AreaLight` {#class-arealight}
Inherits from: `Light`

Area light with shape and size controls.

::: details Methods

---
#### `set_shape`

Set area light shape.

**Signature**

```python
def set_shape(self, shape: Literal['SQUARE', 'RECTANGLE', 'DISK', 'ELLIPSE']) -> 'AreaLight'
```

**Arguments**

- **`shape`** : `Literal['SQUARE', 'RECTANGLE', 'DISK', 'ELLIPSE']` — Area-light shape

**Returns**: `Self`

---
---
#### `set_size`

Set primary area light size.

**Signature**

```python
def set_size(self, size: float) -> 'AreaLight'
```

**Arguments**

- **`size`** : `float` — Primary size

**Returns**: `Self`

---
---
#### `set_size_xy`

Set area light X and Y sizes.

**Signature**

```python
def set_size_xy(self, size_x: float, size_y: float) -> 'AreaLight'
```

**Arguments**

- **`size_x`** : `float` — Size along X
- **`size_y`** : `float` — Size along Y

**Returns**: `Self`

---
:::

---

### `class SpotLight` {#class-spotlight}
Inherits from: `Light`

Spot light with cone and blend controls.

::: details Methods

---
#### `set_spot_size`

Set spotlight cone angle in radians.

**Signature**

```python
def set_spot_size(self, angle_radians: float) -> 'SpotLight'
```

**Arguments**

- **`angle_radians`** : `float` — Cone angle in radians

**Returns**: `Self`

---
---
#### `set_blend`

Set spotlight edge softness in the [0, 1] range.

**Signature**

```python
def set_blend(self, blend: float) -> 'SpotLight'
```

**Arguments**

- **`blend`** : `float` — Edge softness in [0, 1]

**Returns**: `Self`

---
---
#### `set_show_cone`

Show or hide the spotlight cone in viewport.

**Signature**

```python
def set_show_cone(self, show: bool=True) -> 'SpotLight'
```

**Arguments**

- **`show`** : `bool` — Viewport cone visibility

**Returns**: `Self`

---
:::

---

### `class World` {#class-world}
Inherits from: `ABC`

Base class representing world (environment ligthing).

::: details Methods

---
#### `set_params`

Update world-specific lighting parameters.

**Signature**

```python
@abstractmethod
def set_params(self)
```

**Arguments**


---
:::

---

### `class BasicWorld` {#class-basicworld}
Inherits from: `World`

`World` class representing a single color environmental lighting.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `color` | `ColorRGBA \| None` | Environment RGBA color |
| `strength` | `float` | Background light intensity |

:::

::: details Methods

---
#### `set_params`

Set ligthing parameters.

**Signature**

```python
def set_params(self, color: ColorRGBA | None=None, strength: float=None)
```

**Arguments**

- **`color`** : `ColorRGBA | None` — environement color
- **`strength`** : `float` — envronement light strength

---
:::

---

### `class SkyWorld` {#class-skyworld}
Inherits from: `World`

`World` class representing a procedural sky environement.

For more information, view [official blender docs](https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/sky.html).

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `strength` | `float` | Background light intensity |
| `sun_size` | `float` | Sun angular size |
| `sun_intensity` | `float` | Sun intensity |
| `sun_elevation` | `float` | Sun elevation angle |
| `rotation_z` | `float` | Sun azimuth rotation |
| `altitude` | `float` | Observer altitude |
| `air` | `float` | Air density |
| `aerosol_density` | `float` | Aerosol density |
| `ozone` | `float` | Ozone density |

:::

::: details Methods

---
#### `set_params`

Set procedural sky parameters for the current world.

**Signature**

```python
def set_params(self, strength: float=None, sun_size: float=None, sun_intensity: float=None, sun_elevation: float=None, rotation_z: float=None, air: float=None, aerosol_density: float=None, ozone: float=None)
```

**Arguments**

- **`strength`** : `float` — Environement light strength
- **`sun_size`** : `float` — Sun angular size
- **`sun_intensity`** : `float` — Sun intensity
- **`sun_elevation`** : `float` — Sun elevation
- **`rotation_z`** : `float` — Angle representing the sun direction
- **`air`** : `float` — Air density
- **`aerosol_density`** : `float` — Aerosol density
- **`ozone`** : `float` — Ozone density

---
:::

---

### `class HDRIWorld` {#class-hdriworld}
Inherits from: `World`

`World` class for importing lighting from an hdri `.exr` file.

HDRI files can be captured by a 360 camera or a smartphone app or downloaded from public libraries such as [polyhaven](https://polyhaven.com/hdris).

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `hdri_path` | `str` | Path to HDRI image file |
| `strength` | `float` | Environment light intensity multiplier |
| `rotation_z` | `float` | Rotation around world Z axis |

:::

::: details Methods

---
#### `set_params`

Set HDRI source and environment lighting parameters.

**Signature**

```python
def set_params(self, hdri_path: str=None, strength: float=None, rotation_z: float=None)
```

**Arguments**

- **`hdri_path`** : `str` — Path to the `.exr` file
- **`strength`** : `float` — Environment intensity multiplier
- **`rotation_z`** : `float` — Rotation around world Z axis

---
:::

---

### `class ImportedWorld` {#class-importedworld}
Inherits from: `World`

`World` class for importing environment lighting from a `.blend` file.

Use it to bring in custom procedural lighting setups and adjust their parameters by the script.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `filepath` | `str` | Source .blend file path |
| `world_name` | `str` | World name inside source .blend |
| `params` | `dict` | Custom properties applied to imported world |

:::

::: details Methods

---
#### `set_params`

Set custom properties applied to the imported world.

**Signature**

```python
def set_params(self, **kwargs)
```

**Arguments**

- **`**kwargs`**

---
:::

---

## Enums

### RenderPass {#enum-renderpass}
Enum representing the supported render passes available for export. To enable them, use `Scene.set_passes` method.

For full documentation view [blender docs](https://docs.blender.org/manual/en/latest/render/layers/passes.html)

::: details Variants

| Name | Description |
| - | - |
| `Z` | Distance to the nearest visible surface. |
| `VECTOR` | Motion vector |
| `MIST` | Distance to the nearest visible surface, mapped to the 0.0 - 1.0 range. |
| `POSITION` | Positions in world space. |
| `NORMAL` | Surface normals in world space. |
| `UV` | The UV coordinates within each object’s active UV map, represented through the red and green channels of the image. |
| `OBJECT_INDEX` | A map where each pixel stores the user-defined ID of the object at that pixel. It is saved as 16-bit BW image. |
| `MATERIAL_INDEX` | A map where each pixel stores the user-defined ID of the material at that pixel. It is saved as 16-bit BW image. |
| `SHADOW` | Shadow map |
| `AO` | Ambient Occlusion contribution from indirect lighting. |
| `EMISSION` | Emission from materials, without influence from lighting. |
| `ENVIRONMENT` | Captures the background/environment lighting. |
| `SHADOW_CATCHER` | Captures shadows cast on shadow catcher objects. |
| `DIFFUSE_COLOR` | Base diffuse color of surfaces. |
| `DIFFUSE_DIRECT` | Direct light contribution to diffuse surfaces. |
| `DIFFUSE_INDIRECT` | Indirect light contribution to diffuse surfaces. |
| `GLOSSY_COLOR` | Base glossy (specular) color of surfaces. |
| `GLOSSY_DIRECT` | Direct light contribution to glossy reflections. |
| `GLOSSY_INDIRECT` | Indirect light contribution to glossy reflections. |
| `TRANSMISSION_COLOR` | Base transmission color of materials. |
| `TRANSMISSION_DIRECT` | Direct light through transmissive materials. |
| `TRANSMISSION_INDIRECT` | Indirect light through transmissive materials. |
| `CRYPTO_OBJECT` |  |
| `CRYPTO_MATERIAL` |  |
| `CRYPTO_ASSET` |  |

:::

---

## Functions

### `begin_run` {#function-begin-run}

Start a new rv run by clearing previously generated data and returning a new run ID.

::: details Details

**Signature**

```python
def begin_run(purge_orphans: bool=True) -> str
```

**Arguments**

- **`purge_orphans`** : `bool` — Remove orphaned Blender datablocks after cleanup

**Returns**: `Self`

:::

### `end_run` {#function-end-run}

Finish the current rv run and optionally purge orphaned Blender datablocks.

::: details Details

**Signature**

```python
def end_run(purge_orphans: bool=False) -> None
```

**Arguments**

- **`purge_orphans`** : `bool` — Remove orphaned Blender datablocks on shutdown

**Returns**: `None`

:::

### `simulate_physics` {#function-simulate-physics}

Simulate current Blender rigid-body world for a fixed number of frames.

::: details Details

**Signature**

```python
def simulate_physics(frames: int=20, substeps: int=10, time_scale: float=1.0) -> None
```

**Arguments**

- **`frames`** : `int` — Number of simulation frames
- **`substeps`** : `int` — Substeps per frame
- **`time_scale`** : `float` — Physics time scale

**Returns**: `None`

:::
