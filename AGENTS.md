# Repository Guidelines

## Project Structure & Module Organization
- `main.go` boots the `rv` CLI and wires commands in `cmd/`.
- `cmd/` contains Cobra commands; shared helpers live in `cmd/internal/`.
- `rvlib/` bundles the Python-side runtime and Blender template assets (`rvlib/rvlib/*.py`, `template.blend`).
- `examples/` includes runnable scene scripts and sample outputs.
- `export_docs.py` generates documentation assets.

## Build, Test, and Development Commands
- `go build ./...`: compile the CLI and verify Go packages build.
- `go run . preview examples/1_primitives/scene.py`: run the live preview using a sample scene.
- `go run . render examples/1_primitives/scene.py -n 10 -p 2 -o ./out`: render a dataset to `./out`.
- `go install github.com/Rapid-Vision/rv@latest`: install the released CLI (requires Go and network).

## Coding Style & Naming Conventions
- Go code: `gofmt`-formatted tabs, idiomatic Go naming, and exported symbols in `CamelCase`.
- Python code in `rvlib/rvlib`: follow PEP 8 (4-space indent) and keep public APIs stable.
- Filenames: keep Go source in `*.go` and tests (when added) in `*_test.go`.

## Testing Guidelines
- No automated tests are present yet; add Go tests under the package they cover.
- Use standard Go tooling: `go test ./...`.
- Prefer table-driven tests and minimal Blender dependencies in unit tests.

## Commit & Pull Request Guidelines
- Prefix commit messages with correct commit type (feat, fix, git, docs, refactor, test, etc); use short, imperative commit subjects (e.g., "feat: Add render flag validation").
- PRs should include: a brief summary, rationale, and test commands run.
- For CLI behavior changes, include example commands and expected output.

## Dependencies & Configuration
- Requires Go `1.24.4` (see `go.mod`) and Blender installed and discoverable on PATH.
- Example scenes live in `examples/`; start there when validating new features.
