.PHONY: docs rtasks test-python-unit test-blender

rtasks:
	rrpc client --lang go -o internal -f rtasks.rrpc

docs:
	uvx rdocgen -c rvlib/rvlib/rv.py -o docs_vp/docs/en/api
	cp docs_vp/docs/en/api/index.md docs_vp/docs/ru/api/index.md

test: test-python-unit test-blender

test-python-unit:
	python3 -m unittest discover -s tests/unit -p "test*.py" -v

test-blender:
	python3 scripts/run_blender.py --background --factory-startup --python scripts/run_blender_tests.py
