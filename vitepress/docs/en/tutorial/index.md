# Rapid Vision

**Rapid Vision (`rv`)** is a lightweight toolset for generating labeled synthetic image datasets with just a few lines of code.

## Advantages
1. Photorealistic results using [Cycles](https://www.blender.org/features/rendering/#cycles) rendering engine
2. Simple and clean Python API
3. Automatic segmentation labeling creation
3. Completely open source
4. Seamless integration with [Blender's](https://www.blender.org/) rich procedural toolset.


## Getting started

<Steps>

<Step title="Install dependencies">

Install [Go](https://go.dev/doc/install) and [Blender](https://www.blender.org/download/).

</Step>

<Step title="Install the rv tool">

```bash
go install github.com/Rapid-Vision/rv@latest
```

</Step>


<Step title="Create scene script">

<<<@/snippets/1_basic_scene.py{python:line-numbers}

</Step>

<Step title="Preview the scene">

```bash
rv preview scene.py
```
Don't close the preview window yet.

</Step>



<Step title="Randomize the scene">

See how the preview changes on each file save.

<<<@/snippets/2_randomized.py{python:line-numbers}

</Step>

<Step title="Render the final result">

```bash
rv render scene.py
```

</Step>


<Step title="See the resulting dataset">

Resulting dataset has following directory structure:

<<<@/snippets/3_files.txt{text}

|                  Name                  | Description                                                                                                                                         |
| :------------------------------------: | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
|                 `out`                  | Root directroy containing results of all runs                                                                                                       |
|                  `1`                   | Directory containing results of a single rendering run. Number increases sequentially                                                               |
| `424702d4-b28e-4082-b5e5-5499f9a49065` | Directory with resulting image, labeling and additional render passes                                                                               |
|              `_meta.json`              | Labeling information                                                                                                                                |
|            `Image0001.png`             | Resulting image                                                                                                                                     |
|        `PreviewIndexOB0001.png`        | Preview for the segmentation masks                                                                                                                  |
|           `IndexOB0001.png`            | Segmentation masks. It is a 16-bit black and with image with each pixel corresponding to the `index` field of each object in the `_meta.json` file. |
|                 Other                  | Other rendering passes that can be useful for computer vision tasks and can be additionaly enabled by the `Scene.set_passes` method.                |

</Step>


<Step title="Use rv for generating your next synthetic dataset">

For more information view the [API reference](/en/api/).

</Step>

</Steps>
