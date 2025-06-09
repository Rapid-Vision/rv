# Rapid Vision

Project website: https://rapid-vision.github.io/

**Rapid Vision (`rv`)** is a lightweight tool for generating labeled synthetic image datasets with just a few commands.

## Goals

1. Provide a simple and intuitive API to define procedural scenes with custom random distributions and automatic labeling using [Blender](https://www.blender.org/)
2. Enable live preview to instantly visualize code changes.
3. Support parallel, resumable dataset generation with a single command.
4. Serve as a bridge between Blender and other procedural generation tools.

## Usage

Create a script to generate a scene and save labeling.

```python
import rv
from random import choice

def render_scene():
    rv.set_resolution([640, 640])
    rv.set_mode("classification")
    rv.set_classes(["sphere", "cube"])

    current_class = choice(["sphere", "cube"])
    rv.set_class(current_class)

    if current_class == "sphere":
        obj = rv.add_sphere()
    else:
        obj = rv.add_cube()

    obj.set_rotation(rv.random_rotation())
```

Live preview generated scene

```bash
$ rv preview examples/scene.py
```

Render final images with labeling

```bash
$ rv render examples/scene.py -n 1000
```

## Building project

Project provides a single binary `rv` and python library for blender.

```
$ go build
```
