# Repository Guidelines

## Project Structure & Module Organization
- `main.go` boots the `rv` CLI and wires Cobra commands from `cmd/`.
- `internal/` contains shared Go packages for rendering, preview, seed parsing, logging, and path resolution used by the CLI.
- `rvlib/` bundles the embedded Python runtime and Blender template assets (`rvlib/rvlib/**/*.py`, `rvlib/template.blend`).
- `scripts/` contains Blender-oriented test runners and helper entrypoints.
- `tests/` contains Python unit tests; keep Blender-free coverage there and reserve Blender-backed checks for the scripted integration path.
- `examples/` contains runnable sample scenes and example assets for manual validation.
- `utils/` contains auxiliary documentation; generated API docs are produced through the `docs` make target into `docs_vp/`.

## Build, Test, and Development Commands
- `go build ./...`: compile the CLI and verify all Go packages build.
- `go test ./...`: run the Go test suite.
- `make test-go`: run Go tests through the project make target.
- `make test-python-unit`: run Python unit tests from `tests/unit` without Blender.
- `make test-blender`: run Blender integration tests via `scripts/run_blender.py` and `scripts/run_blender_tests.py`.
- `go run . preview examples/1_primitives/scene.py`: launch live preview for a sample scene.
- `go run . preview examples/1_primitives/scene.py --preview-files --no-window --preview-out ./preview_out`: run file-only preview output without opening the Blender UI.
- `go run . render examples/1_primitives/scene.py -n 10 -p 2 -o ./out`: render a dataset to `./out`.
- `make lint`: run Python and Go lint targets.
- `make docs`: generate api docs. Never edit them by hand.

## Coding Style & Naming Conventions
- Go code: keep files `gofmt`-formatted, use idiomatic package structure, and expose public identifiers in `CamelCase`.
- Python under `rvlib/rvlib/`: follow PEP 8 with 4-space indentation and avoid breaking the public `rv` API surface.
- Tests: name Go tests `*_test.go`; keep Python test files under `tests/` with `test*.py` naming.
- CLI flags and user-facing command behavior should stay consistent with the existing Cobra command patterns in `cmd/`.

## Testing Guidelines
- Add Go tests close to the package they cover and prefer table-driven tests for flag parsing, path resolution, and command validation.
- Keep unit tests Blender-free where possible; use `make test-blender` only for integration paths that require the embedded runtime or Blender process behavior.
- When changing preview/render behavior, run the narrowest relevant test target first, then `go test ./...` before finishing.

## Commit & Pull Request Guidelines
- Prefix commit messages with a conventional type such as `feat`, `fix`, `docs`, `refactor`, or `test`, followed by a short imperative summary.
- PRs should include a concise summary, the reason for the change, and the commands used to validate it.
- For CLI behavior changes, include example invocations and expected output or side effects.

## Dependencies & Configuration
- Requires Go `1.24.4` as declared in `go.mod`.
- Blender must be installed and discoverable; test/runtime resolution checks `BLENDER_PATH`, then `blender` on `PATH`, then OS-specific fallback locations.
- Some maintenance targets use external tools such as `uvx`, `staticcheck`, `golangci-lint`, and `rrpc`; install them before running lint, docs, or code generation targets.
