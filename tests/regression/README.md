# Regression Tests

This suite renders example scenes with:

```bash
go run ../.. render
```

and compares the resulting images against golden outputs using OpenCV.

The comparison is intentionally forgiving:
- render at a small fixed resolution
- downscale again before comparison
- round-trip through JPEG
- compare pixel deltas with generous thresholds

## Commands

From `tests/regression/`:

```bash
uv run main.py list_tests
uv run main.py test
uv run main.py test --case 1_primitives_scene
uv run main.py regenerate
```

Golden files live in `golden/`. Diff artifacts for failed comparisons are written to
`artifacts/`.
