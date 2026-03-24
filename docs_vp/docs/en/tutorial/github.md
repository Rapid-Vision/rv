# Building from source

<Steps>

<Step title="Install dependencies">

Install [Go](https://go.dev/doc/install) and [Blender](https://www.blender.org/download/).

</Step>

<Step title="Clone repository">

```bash
git clone https://github.com/Rapid-Vision/rv.git
```

</Step>

<Step title="Install libraries">

```bash
go mod tidy
```

</Step>

<Step title="Build the project">

```bash
go build
```

</Step>

<Step title="Try it out">

Interactively preview the scene.
```bash
./rv preview examples/1_primitives/scene.py
```

Render final dataset:
```bash
./rv render examples/1_primitives/scene.py -n 100
```

</Step>

</Steps>
