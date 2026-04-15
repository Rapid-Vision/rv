# Overview

Project: `rv`

## Modules

_Module links omitted in flattened output._

## Module: `__init__`

### File: `__init__.py`

Package for describing `rv` scenes.

- Preview a scene with `rv preview <scene.py>`.
- Render a dataset with `rv render <scene.py>`.

## Module: `assets`

### File: `assets.py`

## Module: `compositor`

### File: `compositor.py`

## Module: `domain`

### File: `domain.py`

#### Classes

##### `class Domain` {#class-domain}
Scatter domain descriptor used by scene scattering methods.

::: details Methods

---
###### `kind`

**Signature**

```python
@property
def kind(self) -> str
```

**Arguments**


**Returns**: `str`

---
---
###### `data`

**Signature**

```python
@property
def data(self) -> dict
```

**Arguments**


**Returns**: `dict`

---
---
###### `dimension`

**Signature**

```python
@property
def dimension(self) -> int
```

**Arguments**


**Returns**: `int`

---
---
###### `inset`

**Signature**

```python
def inset(self, margin: float) -> 'Domain'
```

**Arguments**

- **`margin`** : `float`

**Returns**: `'Domain'`

---
---
###### `rect`

**Signature**

```python
@staticmethod
def rect(center: Float2=(0.0, 0.0), size: Float2=(10.0, 10.0), z: float=0.0) -> 'Domain'
```

**Arguments**

- **`center`** : `Float2`
- **`size`** : `Float2`
- **`z`** : `float`

**Returns**: `'Domain'`

---
---
###### `custom`

**Signature**

```python
@staticmethod
def custom(*, dimension: int, contains_point: Callable[[mathutils.Vector, float], bool], aabb: Callable[[float], AABB], sample_point: Union[Callable[[random.Random, float], mathutils.Vector], None]=None, kind: str='custom', data: Union[dict, None]=None) -> 'Domain'
```

**Arguments**

- **`dimension`** : `int`
- **`contains_point`** : `Callable[[mathutils.Vector, float], bool]`
- **`aabb`** : `Callable[[float], AABB]`
- **`sample_point`** : `Union[Callable[[random.Random, float], mathutils.Vector], None]`
- **`kind`** : `str`
- **`data`** : `Union[dict, None]`

**Returns**: `'Domain'`

---
---
###### `ellipse`

**Signature**

```python
@staticmethod
def ellipse(center: Float2=(0.0, 0.0), radii: Float2=(5.0, 3.0), z: float=0.0) -> 'Domain'
```

**Arguments**

- **`center`** : `Float2`
- **`radii`** : `Float2`
- **`z`** : `float`

**Returns**: `'Domain'`

---
---
###### `polygon`

**Signature**

```python
@staticmethod
def polygon(points, z: float=0.0) -> 'Domain'
```

**Arguments**

- **`points`**
- **`z`** : `float`

**Returns**: `'Domain'`

---
---
###### `convex_polygon`

**Signature**

```python
@staticmethod
def convex_polygon(points, z: float=0.0) -> 'Domain'
```

**Arguments**

- **`points`**
- **`z`** : `float`

**Returns**: `'Domain'`

---
---
###### `box`

**Signature**

```python
@staticmethod
def box(center: Float3=(0.0, 0.0, 0.0), size: Float3=(10.0, 10.0, 10.0)) -> 'Domain'
```

**Arguments**

- **`center`** : `Float3`
- **`size`** : `Float3`

**Returns**: `'Domain'`

---
---
###### `cylinder`

**Signature**

```python
@staticmethod
def cylinder(center: Float3=(0.0, 0.0, 0.0), radius: float=5.0, height: float=10.0, axis: str='Z') -> 'Domain'
```

**Arguments**

- **`center`** : `Float3`
- **`radius`** : `float`
- **`height`** : `float`
- **`axis`** : `str`

**Returns**: `'Domain'`

---
---
###### `ellipsoid`

**Signature**

```python
@staticmethod
def ellipsoid(center: Float3=(0.0, 0.0, 0.0), radii: Float3=(5.0, 3.0, 2.0)) -> 'Domain'
```

**Arguments**

- **`center`** : `Float3`
- **`radii`** : `Float3`

**Returns**: `'Domain'`

---
---
###### `convex_hull_2d`

**Signature**

```python
@staticmethod
def convex_hull_2d(rv_obj: Object) -> 'Domain'
```

**Arguments**

- **`rv_obj`** : `Object`

**Returns**: `'Domain'`

---
---
###### `convex_hull_3d`

**Signature**

```python
@staticmethod
def convex_hull_3d(rv_obj: Object) -> 'Domain'
```

**Arguments**

- **`rv_obj`** : `Object`

**Returns**: `'Domain'`

---
---
###### `convex_hull`

**Signature**

```python
@staticmethod
def convex_hull(rv_obj: Object, project_2d: bool=False) -> 'Domain'
```

**Arguments**

- **`rv_obj`** : `Object`
- **`project_2d`** : `bool`

**Returns**: `'Domain'`

---
---
###### `sample_point`

**Signature**

```python
def sample_point(self, rng: random.Random) -> mathutils.Vector
```

**Arguments**

- **`rng`** : `random.Random`

**Returns**: `mathutils.Vector`

---
---
###### `contains_point`

**Signature**

```python
def contains_point(self, point: mathutils.Vector, margin: float=0.0) -> bool
```

**Arguments**

- **`point`** : `mathutils.Vector`
- **`margin`** : `float`

**Returns**: `bool`

---
---
###### `contains_object`

**Signature**

```python
def contains_object(self, obj: Object, margin: float=0.0, mode: Literal['aabb', 'mesh']='mesh') -> bool
```

**Arguments**

- **`obj`** : `Object`
- **`margin`** : `float`
- **`mode`** : `Literal['aabb', 'mesh']`

**Returns**: `bool`

---
---
###### `aabb`

**Signature**

```python
def aabb(self) -> AABB
```

**Arguments**


**Returns**: `AABB`

---
:::

---

## Module: `generators`

### File: `generators.py`

#### Classes

##### `class GeneratorHandle` {#class-generatorhandle}
::: details Methods

---
###### `generate`

**Signature**

```python
def generate(self, **params) -> Any
```

**Arguments**

- **`**params`**

**Returns**: `Any`

---
---
###### `generate_path`

**Signature**

```python
def generate_path(self, **params) -> str
```

**Arguments**

- **`**params`**

**Returns**: `str`

---
---
###### `generate_str`

**Signature**

```python
def generate_str(self, **params) -> str
```

**Arguments**

- **`**params`**

**Returns**: `Self`

---
---
###### `generate_num`

**Signature**

```python
def generate_num(self, **params) -> float
```

**Arguments**

- **`**params`**

**Returns**: `float`

---
:::

---

##### `class GeneratorFactory` {#class-generatorfactory}
::: details Methods

---
###### `init`

**Signature**

```python
def init(self, command: str) -> GeneratorHandle
```

**Arguments**

- **`command`** : `str`

**Returns**: `GeneratorHandle`

---
:::

---

## Module: `geometry`

### File: `geometry.py`

## Module: `internal`

### File: `internal.py`

Runner-only helpers for the `rvlib` runtime.

These functions are intentionally separated from the public `rv` package API.
They remain importable for bundled runners such as preview/render/export.

## Module: `material`

### File: `material.py`

#### Classes

##### `class Material` {#class-material}
Inherits from: `ABC`, `_Serializable`

Base class for material descriptors.

A material descriptor is converted to a real Blender material when assigned to an object.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `name` | `Union[str, None]` |  |
| `index` | `Union[int, None]` |  |

:::

::: details Methods

---
###### `set_params`

**Signature**

```python
@abstractmethod
def set_params(self, **kwargs) -> Self
```

**Arguments**

- **`**kwargs`**

**Returns**: `Self`

---
:::

---

##### `class BasicMaterial` {#class-basicmaterial}
Inherits from: `Material`

Material descriptor backed by Blender's Principled BSDF shader.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `base_color` | `Union[ColorRGBA, None]` |  |
| `roughness` | `Union[float, None]` |  |
| `metallic` | `Union[float, None]` |  |
| `specular` | `Union[float, None]` |  |
| `emission_color` | `Union[ColorRGBA, None]` |  |
| `emission_strength` | `Union[float, None]` |  |
| `alpha` | `Union[float, None]` |  |
| `transmission` | `Union[float, None]` |  |
| `ior` | `Union[float, None]` |  |
| `properties` | `dict` |  |

:::

::: details Methods

---
###### `set_params`

**Signature**

```python
def set_params(self, base_color: OptionalColor=None, roughness: Union[float, None]=None, metallic: Union[float, None]=None, specular: Union[float, None]=None, emission_color: OptionalColor=None, emission_strength: Union[float, None]=None, alpha: Union[float, None]=None, transmission: Union[float, None]=None, ior: Union[float, None]=None) -> Self
```

**Arguments**

- **`base_color`** : `OptionalColor`
- **`roughness`** : `Union[float, None]`
- **`metallic`** : `Union[float, None]`
- **`specular`** : `Union[float, None]`
- **`emission_color`** : `OptionalColor`
- **`emission_strength`** : `Union[float, None]`
- **`alpha`** : `Union[float, None]`
- **`transmission`** : `Union[float, None]`
- **`ior`** : `Union[float, None]`

**Returns**: `Self`

---
---
###### `set_property`

**Signature**

```python
def set_property(self, key: str, value: Any)
```

**Arguments**

- **`key`** : `str`
- **`value`** : `Any`

**Returns**: `Self`

---
:::

---

##### `class ImportedMaterial` {#class-importedmaterial}
Inherits from: `Material`

Material descriptor that imports a material from another `.blend` file.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `filepath` | `str` |  |
| `material_name` | `Union[str, None]` |  |
| `params` | `dict` |  |

:::

::: details Methods

---
###### `set_params`

**Signature**

```python
def set_params(self, **kwargs: Any)
```

**Arguments**

- **`**kwargs`** : `Any`

**Returns**: `Self`

---
:::

---

## Module: `modifiers`

### File: `modifiers.py`

## Module: `object`

### File: `object.py`

#### Classes

##### `class ObjectStats` {#class-objectstats}
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
###### `to_dict`

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

##### `class ObjectLoader` {#class-objectloader}
Helper for creating object instances from a loaded Blender object source.

::: details Methods

---
###### `set_source`

Rebind this loader to use an existing object as its instancing prototype.

**Signature**

```python
def set_source(self, source: 'Object') -> 'ObjectLoader'
```

**Arguments**

- **`source`** : `'Object'`

**Returns**: `Self`

---
---
###### `create_instance`

Create a single object instance from a loader.

**Signature**

```python
def create_instance(self, name: Union[str, None]=None, register_object: bool=True, linked_data: bool=True) -> 'Object'
```

**Arguments**

- **`name`** : `Union[str, None]`
- **`register_object`** : `bool`
- **`linked_data`** : `bool`

**Returns**: `Self`

---
:::

---

##### `class Object` {#class-object}
Inherits from: `_Serializable`

Wrapper around a Blender object with chainable transformation and metadata helpers.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `obj` | `bpy.types.Object` |  |
| `scene` | `'Scene'` |  |
| `tags` | `TagSet` |  |
| `properties` | `dict` |  |
| `modifier_parameters` | `list[dict[str, JSONSerializable]]` |  |
| `index` | `Union[int, None]` |  |

:::

::: details Methods

---
###### `as_loader`

Create an `ObjectLoader` that instances this object.

**Signature**

```python
def as_loader(self) -> ObjectLoader
```

**Arguments**


**Returns**: `ObjectLoader`

---
---
###### `copy`

Duplicate this object.

If `linked_data` is False, mesh/light/camera data is copied as well.

**Signature**

```python
def copy(self, name: Union[str, None]=None, linked_data: bool=True, register_object: bool=True) -> 'Object'
```

**Arguments**

- **`name`** : `Union[str, None]`
- **`linked_data`** : `bool`
- **`register_object`** : `bool`

**Returns**: `Self`

---
---
###### `set_location`

Set the location of the object in 3D space.

**Signature**

```python
def set_location(self, location: Union[mathutils.Vector, Sequence[float]])
```

**Arguments**

- **`location`** : `Union[mathutils.Vector, Sequence[float]]`

**Returns**: `Self`

---
---
###### `get_location`

Get the object location as an `(x, y, z)` tuple.

**Signature**

```python
def get_location(self) -> Float3
```

**Arguments**


**Returns**: `Float3`

---
---
###### `move`

Translate the object by the given offsets.

**Signature**

```python
def move(self, dx: float=0.0, dy: float=0.0, dz: float=0.0) -> 'Object'
```

**Arguments**

- **`dx`** : `float`
- **`dy`** : `float`
- **`dz`** : `float`

**Returns**: `Self`

---
---
###### `set_rotation`

Set the rotation of the object.

**Signature**

```python
def set_rotation(self, rotation: Union[mathutils.Euler, mathutils.Quaternion])
```

**Arguments**

- **`rotation`** : `Union[mathutils.Euler, mathutils.Quaternion]`

**Returns**: `Self`

---
---
###### `set_scale`

Set the scale of the object.

If `scale` is a single numeric value, all axes are set to that value.
If `scale` is a sequence or Vector of length 3, each axis is set individually.

**Signature**

```python
def set_scale(self, scale: Union[mathutils.Vector, Sequence[float], float, int])
```

**Arguments**

- **`scale`** : `Union[mathutils.Vector, Sequence[float], float, int]`

**Returns**: `Self`

---
---
###### `set_property`

Set a property of the object. Properties can be used inside object's material nodes.

**Signature**

```python
def set_property(self, key: str, value: Any)
```

**Arguments**

- **`key`** : `str`
- **`value`** : `Any`

**Returns**: `Self`

---
---
###### `set_modifier_input`

Set an exposed Geometry Nodes modifier input.

If `modifier_name` is omitted, `rv` searches for a unique Geometry Nodes
modifier that exposes the requested input.

**Signature**

```python
def set_modifier_input(self, input_name: str, value: Any, modifier_name: Union[str, None]=None)
```

**Arguments**

- **`input_name`** : `str`
- **`value`** : `Any`
- **`modifier_name`** : `Union[str, None]`

**Returns**: `Self`

---
---
###### `set_material`

Set object material in the given slot.

**Signature**

```python
def set_material(self, material: 'Material', slot: int=0)
```

**Arguments**

- **`material`** : `'Material'`
- **`slot`** : `int`

**Returns**: `Self`

---
---
###### `add_material`

Append material to object's material slots.

**Signature**

```python
def add_material(self, material: 'Material')
```

**Arguments**

- **`material`** : `'Material'`

**Returns**: `Self`

---
---
###### `clear_materials`

Remove all materials from object.

**Signature**

```python
def clear_materials(self)
```

**Arguments**


**Returns**: `Self`

---
---
###### `set_tags`

Set object's tags.

Tags are used to represent object class for training a computer vision model. Object can have more then one tag.

**Signature**

```python
def set_tags(self, *tags: Union[str, list[str]])
```

**Arguments**

- **`*tags`** : `Union[str, list[str]]`

**Returns**: `Self`

---
---
###### `add_tags`

Add tags to the object.

Tags are used to represent object class for training a computer vision model. Object can have more then one tag.

**Signature**

```python
def add_tags(self, *tags: Union[str, list[str]])
```

**Arguments**

- **`*tags`** : `Union[str, list[str]]`

**Returns**: `Self`

---
---
###### `point_at`

Orients the current object to point at another object, with an optional rotation around the direction vector.

**Signature**

```python
def point_at(self, rv_obj: 'Object', angle: float=0.0)
```

**Arguments**

- **`rv_obj`** : `'Object'`
- **`angle`** : `float`

**Returns**: `Self`

---
---
###### `rotate_around_axis`

Rotate object around an axis.

**Signature**

```python
def rotate_around_axis(self, axis: mathutils.Vector, angle: float)
```

**Arguments**

- **`axis`** : `mathutils.Vector`
- **`angle`** : `float`

**Returns**: `Self`

---
---
###### `set_shading`

Set shading to flat, smooth, or auto.

**Signature**

```python
def set_shading(self, shading: Literal['flat', 'smooth', 'auto'])
```

**Arguments**

- **`shading`** : `Literal['flat', 'smooth', 'auto']`

**Returns**: `Self`

---
---
###### `show_debug_axes`

Show debug axes that can be seen in the `preview` mode.

**Signature**

```python
def show_debug_axes(self, show=True)
```

**Arguments**

- **`show`**

**Returns**: `Self`

---
---
###### `show_debug_name`

Show object's name that can be seen in the `preview` mode.

**Signature**

```python
def show_debug_name(self, show)
```

**Arguments**

- **`show`**

**Returns**: `Self`

---
---
###### `hide`

Hide object from render output while controlling preview visibility.

**Signature**

```python
def hide(self, view: Literal['wireframe', 'none']='wireframe')
```

**Arguments**

- **`view`** : `Literal['wireframe', 'none']`

**Returns**: `Self`

---
---
###### `get_dimensions`

Get object dimensions (axis-aligned extents) in world or local space.

**Signature**

```python
def get_dimensions(self, space: Literal['world', 'local']='world') -> Float3
```

**Arguments**

- **`space`** : `Literal['world', 'local']`

**Returns**: `Float3`

---
---
###### `inspect`

Inspect geometric stats for this object.

**Signature**

```python
def inspect(self, applied_scale: bool=True) -> ObjectStats
```

**Arguments**

- **`applied_scale`** : `bool`

**Returns**: `ObjectStats`

---
---
###### `get_bounds`

Get axis-aligned bounds in world or local space.

**Signature**

```python
def get_bounds(self, space: Literal['world', 'local']='world') -> dict[str, Float3]
```

**Arguments**

- **`space`** : `Literal['world', 'local']`

**Returns**: `dict[str, Float3]`

---
---
###### `add_rigidbody`

Add or update rigid-body settings for this object.

**Signature**

```python
def add_rigidbody(self, mode: Literal['box', 'sphere', 'hull', 'mesh', 'capsule', 'cylinder', 'cone']='hull', mesh_source: Literal['BASE', 'DEFORM', 'FINAL']='FINAL', body_type: Literal['ACTIVE', 'PASSIVE']='ACTIVE', mass: float=1.0, friction: float=0.5, restitution: float=0.0, linear_damping: float=0.04, angular_damping: float=0.1, use_margin: bool=True, collision_margin: Union[float, None]=None, use_deactivation: Union[bool, None]=None, deactivate_linear_velocity: Union[float, None]=None, deactivate_angular_velocity: Union[float, None]=None, start_deactivated: Union[bool, None]=None) -> 'Object'
```

**Arguments**

- **`mode`** : `Literal['box', 'sphere', 'hull', 'mesh', 'capsule', 'cylinder', 'cone']`
- **`mesh_source`** : `Literal['BASE', 'DEFORM', 'FINAL']`
- **`body_type`** : `Literal['ACTIVE', 'PASSIVE']`
- **`mass`** : `float`
- **`friction`** : `float`
- **`restitution`** : `float`
- **`linear_damping`** : `float`
- **`angular_damping`** : `float`
- **`use_margin`** : `bool`
- **`collision_margin`** : `Union[float, None]`
- **`use_deactivation`** : `Union[bool, None]`
- **`deactivate_linear_velocity`** : `Union[float, None]`
- **`deactivate_angular_velocity`** : `Union[float, None]`
- **`start_deactivated`** : `Union[bool, None]`

**Returns**: `Self`

---
---
###### `remove_rigidbody`

Remove rigid body from this object if present.

**Signature**

```python
def remove_rigidbody(self, keep_transform: bool=True) -> 'Object'
```

**Arguments**

- **`keep_transform`** : `bool`

**Returns**: `Self`

---
:::

---

##### `class Camera` {#class-camera}
Inherits from: `Object`

`Object` specialization with camera-specific controls.

::: details Methods

---
###### `set_fov`

Sets the field of view (FOV) for the object's camera in degrees.

**Signature**

```python
def set_fov(self, angle: float)
```

**Arguments**

- **`angle`** : `float`

**Returns**: `Self`

---
:::

---

##### `class Light` {#class-light}
Inherits from: `Object`

Base object wrapper for Blender lights with chainable parameter setters.

::: details Methods

---
###### `light_data`

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
###### `set_color`

Set light RGB color. Alpha (if provided) is ignored.

**Signature**

```python
def set_color(self, color: Color) -> Self
```

**Arguments**

- **`color`** : `Color`

**Returns**: `Self`

---
---
###### `set_power`

Set light power in Blender `energy` units.

**Signature**

```python
def set_power(self, power: float) -> Self
```

**Arguments**

- **`power`** : `float`

**Returns**: `Self`

---
---
###### `set_cast_shadow`

Enable or disable shadow casting.

**Signature**

```python
def set_cast_shadow(self, enabled: bool=True) -> Self
```

**Arguments**

- **`enabled`** : `bool`

**Returns**: `Self`

---
---
###### `set_specular_factor`

Set the light contribution to specular highlights.

**Signature**

```python
def set_specular_factor(self, factor: float) -> Self
```

**Arguments**

- **`factor`** : `float`

**Returns**: `Self`

---
---
###### `set_softness`

Set softness parameter mapped to the current light type.

**Signature**

```python
def set_softness(self, value: float) -> Self
```

**Arguments**

- **`value`** : `float`

**Returns**: `Self`

---
---
###### `set_params`

Set known light-data attributes or custom properties.

**Signature**

```python
def set_params(self, **kwargs) -> Self
```

**Arguments**

- **`**kwargs`**

**Returns**: `Self`

---
:::

---

##### `class PointLight` {#class-pointlight}
Inherits from: `Light`

Point light with radius control.

::: details Methods

---
###### `set_radius`

Set point light radius.

**Signature**

```python
def set_radius(self, radius: float) -> 'PointLight'
```

**Arguments**

- **`radius`** : `float`

**Returns**: `Self`

---
:::

---

##### `class SunLight` {#class-sunlight}
Inherits from: `Light`

Directional sun light with angular size control.

::: details Methods

---
###### `set_angle`

Set sun angular size in degrees.

**Signature**

```python
def set_angle(self, angle: float) -> 'SunLight'
```

**Arguments**

- **`angle`** : `float`

**Returns**: `Self`

---
:::

---

##### `class AreaLight` {#class-arealight}
Inherits from: `Light`

Area light with shape and size controls.

::: details Methods

---
###### `set_shape`

Set area light shape.

**Signature**

```python
def set_shape(self, shape: Literal['SQUARE', 'RECTANGLE', 'DISK', 'ELLIPSE']) -> 'AreaLight'
```

**Arguments**

- **`shape`** : `Literal['SQUARE', 'RECTANGLE', 'DISK', 'ELLIPSE']`

**Returns**: `Self`

---
---
###### `set_size`

Set primary area light size.

**Signature**

```python
def set_size(self, size: float) -> 'AreaLight'
```

**Arguments**

- **`size`** : `float`

**Returns**: `Self`

---
---
###### `set_size_xy`

Set area light X and Y sizes.

**Signature**

```python
def set_size_xy(self, size_x: float, size_y: float) -> 'AreaLight'
```

**Arguments**

- **`size_x`** : `float`
- **`size_y`** : `float`

**Returns**: `Self`

---
:::

---

##### `class SpotLight` {#class-spotlight}
Inherits from: `Light`

Spot light with cone and blend controls.

::: details Methods

---
###### `set_spot_size`

Set spotlight cone angle in degrees.

**Signature**

```python
def set_spot_size(self, angle: float) -> 'SpotLight'
```

**Arguments**

- **`angle`** : `float`

**Returns**: `Self`

---
---
###### `set_blend`

Set spotlight edge softness in the [0, 1] range.

**Signature**

```python
def set_blend(self, blend: float) -> 'SpotLight'
```

**Arguments**

- **`blend`** : `float`

**Returns**: `Self`

---
---
###### `set_show_cone`

Show or hide the spotlight cone in viewport.

**Signature**

```python
def set_show_cone(self, show: bool=True) -> 'SpotLight'
```

**Arguments**

- **`show`** : `bool`

**Returns**: `Self`

---
:::

---

## Module: `passes`

### File: `passes.py`

#### Enums

##### RenderPass {#enum-renderpass}
Enum representing the supported render passes available for export. To enable them, use `Scene.set_passes` method.

For full documentation view [blender docs](https://docs.blender.org/manual/en/latest/render/layers/passes.html)

::: details Variants

| Name | Description |
| - | - |
| `Z` |  |
| `VECTOR` |  |
| `MIST` |  |
| `POSITION` |  |
| `NORMAL` |  |
| `UV` |  |
| `OBJECT_INDEX` |  |
| `MATERIAL_INDEX` |  |
| `SHADOW` |  |
| `AO` |  |
| `EMISSION` |  |
| `ENVIRONMENT` |  |
| `SHADOW_CATCHER` |  |
| `DIFFUSE_COLOR` |  |
| `DIFFUSE_DIRECT` |  |
| `DIFFUSE_INDIRECT` |  |
| `GLOSSY_COLOR` |  |
| `GLOSSY_DIRECT` |  |
| `GLOSSY_INDIRECT` |  |
| `TRANSMISSION_COLOR` |  |
| `TRANSMISSION_DIRECT` |  |
| `TRANSMISSION_INDIRECT` |  |
| `CRYPTO_OBJECT` |  |
| `CRYPTO_MATERIAL` |  |
| `CRYPTO_ASSET` |  |

:::

---

## Module: `physics`

### File: `physics.py`

#### Functions

##### `simulate_physics` {#function-simulate-physics}

Simulate current Blender rigid-body world for a fixed number of frames.

::: details Details

**Signature**

```python
def simulate_physics(frames: int=20, substeps: int=10, time_scale: float=1.0, solver_iterations: Union[int, None]=None, use_split_impulse: Union[bool, None]=None, split_impulse_penetration_threshold: Union[float, None]=None) -> None
```

**Arguments**

- **`frames`** : `int`
- **`substeps`** : `int`
- **`time_scale`** : `float`
- **`solver_iterations`** : `Union[int, None]`
- **`use_split_impulse`** : `Union[bool, None]`
- **`split_impulse_penetration_threshold`** : `Union[float, None]`

**Returns**: `None`

:::

## Module: `render`

### File: `render.py`

## Module: `scatter`

### File: `scatter.py`

## Module: `scene`

### File: `scene.py`

#### Classes

##### `class ObjectFactory` {#class-objectfactory}
::: details Methods

---
###### `empty`

**Signature**

```python
def empty(self, name: str='Empty') -> 'Object'
```

**Arguments**

- **`name`** : `str`

**Returns**: `'Object'`

---
---
###### `sphere`

**Signature**

```python
def sphere(self, name: str='Sphere', radius: float=1.0, segments: int=32, ring_count: int=16) -> 'Object'
```

**Arguments**

- **`name`** : `str`
- **`radius`** : `float`
- **`segments`** : `int`
- **`ring_count`** : `int`

**Returns**: `'Object'`

---
---
###### `cube`

**Signature**

```python
def cube(self, name: str='Cube', size: float=2.0) -> 'Object'
```

**Arguments**

- **`name`** : `str`
- **`size`** : `float`

**Returns**: `'Object'`

---
---
###### `plane`

**Signature**

```python
def plane(self, name: str='Plane', size: float=2.0) -> 'Object'
```

**Arguments**

- **`name`** : `str`
- **`size`** : `float`

**Returns**: `'Object'`

---
:::

---

##### `class LightFactory` {#class-lightfactory}
::: details Methods

---
###### `point`

**Signature**

```python
def point(self, name: str='Point', power: float=1000.0) -> 'PointLight'
```

**Arguments**

- **`name`** : `str`
- **`power`** : `float`

**Returns**: `Self`

---
---
###### `sun`

**Signature**

```python
def sun(self, name: str='Sun', power: float=1.0) -> 'SunLight'
```

**Arguments**

- **`name`** : `str`
- **`power`** : `float`

**Returns**: `Self`

---
---
###### `area`

**Signature**

```python
def area(self, name: str='Area', power: float=100.0) -> 'AreaLight'
```

**Arguments**

- **`name`** : `str`
- **`power`** : `float`

**Returns**: `Self`

---
---
###### `spot`

**Signature**

```python
def spot(self, name: str='Spot', power: float=1000.0) -> 'SpotLight'
```

**Arguments**

- **`name`** : `str`
- **`power`** : `float`

**Returns**: `Self`

---
:::

---

##### `class MaterialFactory` {#class-materialfactory}
::: details Methods

---
###### `basic`

**Signature**

```python
def basic(self, name: str='Material') -> 'BasicMaterial'
```

**Arguments**

- **`name`** : `str`

**Returns**: `'BasicMaterial'`

---
---
###### `imported`

**Signature**

```python
def imported(self, blendfile: str, material_name: Union[str, None]=None) -> 'ImportedMaterial'
```

**Arguments**

- **`blendfile`** : `str`
- **`material_name`** : `Union[str, None]`

**Returns**: `'ImportedMaterial'`

---
:::

---

##### `class AssetFactory` {#class-assetfactory}
::: details Methods

---
###### `object`

**Signature**

```python
def object(self, blendfile: str, import_name: Union[str, None]=None) -> 'ObjectLoader'
```

**Arguments**

- **`blendfile`** : `str`
- **`import_name`** : `Union[str, None]`

**Returns**: `'ObjectLoader'`

---
---
###### `objects`

**Signature**

```python
def objects(self, blendfile: str, import_names: Union[list[str], None]=None) -> list['ObjectLoader']
```

**Arguments**

- **`blendfile`** : `str`
- **`import_names`** : `Union[list[str], None]`

**Returns**: `Self`

---
:::

---

##### `class Scene` {#class-scene}
Inherits from: `ABC`, `_Serializable`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `resolution` | `Resolution` |  |
| `time_limit` | `float` |  |
| `passes` | `RenderPassSet` |  |
| `output_dir` | `Optional[str]` |  |
| `subdir` | `Union[str, None]` |  |
| `camera` | `'Camera'` |  |
| `world` | `'World'` |  |
| `tags` | `TagSet` |  |
| `objects` | `ObjectFactory` |  |
| `materials` | `MaterialFactory` |  |
| `lights` | `LightFactory` |  |
| `assets` | `AssetFactory` |  |
| `generators` | `GeneratorFactory` |  |
| `semantic_channels` | `SemanticChannelSet` |  |
| `semantic_mask_threshold` | `float` |  |
| `seed` | `Union[int, None]` |  |
| `seed_mode` | `Union[str, None]` |  |
| `object_index_counter` | `int` |  |
| `material_index_counter` | `int` |  |
| `light_index_counter` | `int` |  |

:::

::: details Methods

---
###### `generate`

**Signature**

```python
@abstractmethod
def generate(self, seed: Union[int, None]=None) -> None
```

**Arguments**

- **`seed`** : `Union[int, None]`

**Returns**: `None`

---
---
###### `set_rendering_time_limit`

**Signature**

```python
def set_rendering_time_limit(self, time_limit: float=3.0)
```

**Arguments**

- **`time_limit`** : `float`

**Returns**: `Self`

---
---
###### `generated_objects`

**Signature**

```python
@property
def generated_objects(self) -> tuple['Object', ...]
```

**Arguments**


**Returns**: `tuple['Object', ...]`

---
---
###### `generated_materials`

**Signature**

```python
@property
def generated_materials(self) -> tuple['Material', ...]
```

**Arguments**


**Returns**: `tuple['Material', ...]`

---
---
###### `generated_lights`

**Signature**

```python
@property
def generated_lights(self) -> tuple['Light', ...]
```

**Arguments**


**Returns**: `tuple['Light', ...]`

---
---
###### `set_passes`

**Signature**

```python
def set_passes(self, *passes: tuple[Union[RenderPass, list[RenderPass]], ...])
```

**Arguments**

- **`*passes`** : `tuple[Union[RenderPass, list[RenderPass]], ...]`

**Returns**: `Self`

---
---
###### `enable_semantic_channels`

**Signature**

```python
def enable_semantic_channels(self, *channels: tuple[Union[str, list[str]], ...]) -> 'Scene'
```

**Arguments**

- **`*channels`** : `tuple[Union[str, list[str]], ...]`

**Returns**: `Self`

---
---
###### `set_semantic_mask_threshold`

**Signature**

```python
def set_semantic_mask_threshold(self, threshold: float) -> 'Scene'
```

**Arguments**

- **`threshold`** : `float`

**Returns**: `Self`

---
---
###### `set_tags`

**Signature**

```python
def set_tags(self, *tags) -> 'Scene'
```

**Arguments**

- **`*tags`**

**Returns**: `Self`

---
---
###### `add_tags`

**Signature**

```python
def add_tags(self, *tags) -> 'Scene'
```

**Arguments**

- **`*tags`**

**Returns**: `Self`

---
---
###### `inspect_object`

**Signature**

```python
def inspect_object(self, loader_or_obj: Union['ObjectLoader', 'Object'], applied_scale: bool=True) -> ObjectStats
```

**Arguments**

- **`loader_or_obj`** : `Union['ObjectLoader', 'Object']`
- **`applied_scale`** : `bool`

**Returns**: `Self`

---
---
###### `scatter`

**Signature**

```python
def scatter(self, source: ScatterSource, count: int, domain: 'Domain', *, method: Literal['auto', 'fast', 'exact']='auto', gap: float=0.0, scale: Union[float, Float2]=1.0, rotation: Literal['yaw', 'free']='yaw', yaw: Float2=(0.0, 360.0), margin: float=0.0, seed: Union[int, None]=None, unique_data: bool=False, on_create=None, max_attempts_per_object: int=100) -> list['Object']
```

**Arguments**

- **`source`** : `ScatterSource`
- **`count`** : `int`
- **`domain`** : `'Domain'`
- **`method`** : `Literal['auto', 'fast', 'exact']`
- **`gap`** : `float`
- **`scale`** : `Union[float, Float2]`
- **`rotation`** : `Literal['yaw', 'free']`
- **`yaw`** : `Float2`
- **`margin`** : `float`
- **`seed`** : `Union[int, None]`
- **`unique_data`** : `bool`
- **`on_create`**
- **`max_attempts_per_object`** : `int`

**Returns**: `Self`

---
:::

---

## Module: `shader`

### File: `shader.py`

#### Classes

##### `class Expr` {#class-expr}
::: details Attributes

| Name | Type | Description |
| - | - | - |
| `value_type` | `str` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
---
###### `to_meta`

**Signature**

```python
def to_meta(self) -> dict[str, Any]
```

**Arguments**


**Returns**: `Self`

---
---
###### `x_depth`

**Signature**

```python
@cached_property
def x_depth(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class FloatExpr` {#class-floatexpr}
Inherits from: `Expr`

---

##### `class ColorExpr` {#class-colorexpr}
Inherits from: `Expr`

---

##### `class VectorExpr` {#class-vectorexpr}
Inherits from: `Expr`

---

##### `class NormalExpr` {#class-normalexpr}
Inherits from: `VectorExpr`

---

##### `class ShaderExpr` {#class-shaderexpr}
Inherits from: `Expr`

---

##### `class Value` {#class-value}
Inherits from: `FloatExpr`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `value` | `float` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class ColorValue` {#class-colorvalue}
Inherits from: `ColorExpr`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `value` | `tuple[float, ...]` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class VectorValue` {#class-vectorvalue}
Inherits from: `VectorExpr`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `value` | `tuple[float, ...]` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class BinaryMath` {#class-binarymath}
Inherits from: `Expr`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `operation` | `str` |  |
| `left` | `Expr` |  |
| `right` | `Expr` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class TextureImage` {#class-textureimage}
Inherits from: `ColorExpr`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `path` | `str` |  |
| `colorspace` | `str` |  |
| `interpolation` | `str` |  |
| `projection` | `str` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class NormalMap` {#class-normalmap}
Inherits from: `NormalExpr`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `color` | `ShaderValueLike` |  |
| `strength` | `ShaderValueLike` |  |
| `space` | `str` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class PrincipledBSDF` {#class-principledbsdf}
Inherits from: `ShaderExpr`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `base_color` | `Union[ShaderValueLike, None]` |  |
| `metallic` | `Union[ShaderValueLike, None]` |  |
| `roughness` | `Union[ShaderValueLike, None]` |  |
| `specular` | `Union[ShaderValueLike, None]` |  |
| `normal` | `Union[ShaderValueLike, None]` |  |
| `emission_color` | `Union[ShaderValueLike, None]` |  |
| `emission_strength` | `Union[ShaderValueLike, None]` |  |
| `alpha` | `Union[ShaderValueLike, None]` |  |
| `transmission` | `Union[ShaderValueLike, None]` |  |
| `ior` | `Union[ShaderValueLike, None]` |  |

:::

::: details Methods

---
###### `compile`

**Signature**

```python
def compile(self, compiler: '_ShaderGraphCompiler') -> bpy.types.NodeSocket
```

**Arguments**

- **`compiler`** : `'_ShaderGraphCompiler'`

**Returns**: `bpy.types.NodeSocket`

---
---
###### `node_height`

**Signature**

```python
def node_height(self) -> int
```

**Arguments**


**Returns**: `int`

---
:::

---

##### `class ShaderMaterial` {#class-shadermaterial}
Inherits from: `Material`

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `shader` | `ShaderExpr` |  |
| `properties` | `dict[str, Any]` |  |

:::

::: details Methods

---
###### `set_params`

**Signature**

```python
def set_params(self, shader: Union[ShaderExpr, None]=None) -> Self
```

**Arguments**

- **`shader`** : `Union[ShaderExpr, None]` — type: ignore[override]

**Returns**: `Self`

---
---
###### `set_property`

**Signature**

```python
def set_property(self, key: str, value: Any)
```

**Arguments**

- **`key`** : `str`
- **`value`** : `Any`

**Returns**: `Self`

---
:::

---

## Module: `state`

### File: `state.py`

## Module: `types`

### File: `types.py`

## Module: `utils`

### File: `utils.py`

## Module: `world`

### File: `world.py`

#### Classes

##### `class World` {#class-world}
Inherits from: `ABC`

Base class representing world (environment ligthing).

::: details Methods

---
###### `set_params`

Update world-specific lighting parameters.

**Signature**

```python
@abstractmethod
def set_params(self) -> Self
```

**Arguments**


**Returns**: `Self`

---
:::

---

##### `class BasicWorld` {#class-basicworld}
Inherits from: `World`

`World` class representing a single color environmental lighting.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `color` | `Union[ColorRGBA, None]` |  |
| `strength` | `Union[float, None]` |  |

:::

::: details Methods

---
###### `set_params`

**Signature**

```python
def set_params(self, color: Union[ColorRGBA, None]=None, strength: Union[float, None]=None)
```

**Arguments**

- **`color`** : `Union[ColorRGBA, None]`
- **`strength`** : `Union[float, None]`

**Returns**: `Self`

---
:::

---

##### `class SkyWorld` {#class-skyworld}
Inherits from: `World`

`World` class representing a procedural sky environement.

For more information, view [official blender docs](https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/sky.html).

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `strength` | `Union[float, None]` |  |
| `sun_size` | `Union[float, None]` |  |
| `sun_intensity` | `Union[float, None]` |  |
| `sun_elevation` | `Union[float, None]` |  |
| `rotation_z` | `Union[float, None]` |  |
| `altitude` | `Union[float, None]` |  |
| `air` | `float` |  |
| `aerosol_density` | `float` |  |
| `ozone` | `float` |  |

:::

::: details Methods

---
###### `set_params`

**Signature**

```python
def set_params(self, strength: Union[float, None]=None, sun_size: Union[float, None]=None, sun_intensity: Union[float, None]=None, sun_elevation: Union[float, None]=None, rotation_z: Union[float, None]=None, air: Union[float, None]=None, aerosol_density: Union[float, None]=None, ozone: Union[float, None]=None)
```

**Arguments**

- **`strength`** : `Union[float, None]`
- **`sun_size`** : `Union[float, None]`
- **`sun_intensity`** : `Union[float, None]`
- **`sun_elevation`** : `Union[float, None]`
- **`rotation_z`** : `Union[float, None]`
- **`air`** : `Union[float, None]`
- **`aerosol_density`** : `Union[float, None]`
- **`ozone`** : `Union[float, None]`

**Returns**: `Self`

---
:::

---

##### `class HDRIWorld` {#class-hdriworld}
Inherits from: `World`

`World` class for importing lighting from an hdri `.exr` file.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `hdri_path` | `str` |  |
| `strength` | `Union[float, None]` |  |
| `rotation_z` | `Union[float, None]` |  |

:::

::: details Methods

---
###### `set_params`

**Signature**

```python
def set_params(self, hdri_path: Union[str, None]=None, strength: Union[float, None]=None, rotation_z: Union[float, None]=None)
```

**Arguments**

- **`hdri_path`** : `Union[str, None]`
- **`strength`** : `Union[float, None]`
- **`rotation_z`** : `Union[float, None]`

**Returns**: `Self`

---
:::

---

##### `class ImportedWorld` {#class-importedworld}
Inherits from: `World`

`World` class for importing environment lighting from a `.blend` file.

::: details Attributes

| Name | Type | Description |
| - | - | - |
| `filepath` | `str` |  |
| `world_name` | `Union[str, None]` |  |
| `params` | `dict` |  |

:::

::: details Methods

---
###### `set_params`

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
