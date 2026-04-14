# Generator Example

This example shows how to generate a texture outside Blender with Pillow and use it
inside a scene through `self.generators`.

The scene calls:

```python
generator = self.generators.init("uv run ./gen.py")
texture_path = generator.generate("seed_texture")
```

`rv` passes the current scene seed to `gen.py` in the JSON request on `stdin`. The
generator renders that seed as a single number into a PNG and returns the generated
file path on `stdout`.

Run it from the repository root:

```bash
rv render examples/9_generator/scene.py --cwd examples/9_generator --seed seq -n 3
```

For live preview:

```bash
rv preview examples/9_generator/scene.py --cwd examples/9_generator
```
