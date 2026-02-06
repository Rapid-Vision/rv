.PHONY: docs rtasks

rtasks:
	rrpc client --lang go -o cmd/internal -f rtasks.rrpc

docs:
	rdocgen -c rvlib/rvlib/rv.py -o vitepress/docs/api