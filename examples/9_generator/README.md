# Generator Example

This example shows how to generate a texture outside Blender with Pillow and use it
inside a scene through `self.generators`.

The scene calls:

```python
generator = self.generators.init("uv run ./gen.py")
texture_path = generator.generate("seed_texture")
```

`rv` passes the current scene seed plus `root_dir` and `work_dir` to `gen.py` in the
JSON request on `stdin`. `root_dir` is the scene runtime directory, and `work_dir`
is a per-run directory under `generated/` by default, or under `--gen-dir` when
provided. The generator renders that seed as a single number into a PNG inside
`work_dir` and returns the generated file path on `stdout`.

Run it from the repository root:

```bash
rv render examples/9_generator/scene.py --cwd examples/9_generator --seed seq -n 3
```

To place generator outputs somewhere else:

```bash
rv render examples/9_generator/scene.py --cwd examples/9_generator --gen-dir ./tmp/gen --seed seq -n 3
```

For live preview:

```bash
rv preview examples/9_generator/scene.py --cwd examples/9_generator
```
