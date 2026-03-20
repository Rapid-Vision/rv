# Сборка из исходников

<Steps>

<Step title="Установите зависимости">

Установите [Go](https://go.dev/doc/install) и [Blender](https://www.blender.org/download/).

</Step>

<Step title="Склонируйте репозиторий">

```bash
git clone https://github.com/Rapid-Vision/rv.git
```

</Step>

<Step title="Установите библиотеки">

```bash
go mod tidy
```

</Step>

<Step title="Соберите проект">

```bash
go build
```

</Step>

<Step title="Попробуйте">

Откройте интерактивный предпросмотр сцены.

```bash
./rv preview examples/1_primitives/scene.py
```

Отрендерите итоговый датасет:

```bash
./rv render examples/1_primitives/scene.py -n 100
```

</Step>

</Steps>