# rv export

`rv export` allows to reuse generated scenes. It may be useful if the simulation takes a lot of time.


Export simulated scene:
```bash
rv export export.py -o exported.blend --freeze-physics
```

Preview a scene that imports results of saved simulation.
```bash
rv preview import.py
```