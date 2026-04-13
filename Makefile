.PHONY: docs rtasks test-python-unit test-blender test-go test-regression regen-regression mypy ruff radon staticcheck

# Python verification
mypy:
	uvx mypy --ignore-missing-imports rvlib/rvlib/

radon:
	uvx radon cc rvlib/rvlib/rv -nc

ruff:
	uvx ruff check rvlib/rvlib/ 

# Go verification
staticcheck:
	staticcheck ./...

# Codegen
rtasks:
	rrpc client --lang go -o internal -f rtasks.rrpc

docs:
	uvx rdocgen -c rvlib/rvlib/rv/ --flatten -o docs_vp/docs/en/api
	cp docs_vp/docs/en/api/index.md docs_vp/docs/ru/api/index.md

# Tests

test: test-python-unit test-blender test-go

test-go:
	go test ./...

test-python-unit:
	python3 -m unittest discover -s tests/unit -p "test*.py" -v

test-blender:
	python3 scripts/run_blender.py --background --factory-startup --python scripts/run_blender_tests.py

test-regression:
	cd tests/regression && uv run main.py test

regen-regression:
	cd tests/regression && uv run main.py regenerate
