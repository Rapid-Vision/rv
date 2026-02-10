.PHONY: docs rtasks

rtasks:
	rrpc client --lang go -o internal -f rtasks.rrpc

docs:
	rdocgen -c rvlib/rvlib/rv.py -o vitepress/docs/api