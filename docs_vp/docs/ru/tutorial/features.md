# Обзор возможностей

`rv` построен вокруг простой идеи: генерация сцены остается в Python, а моделирование, шейдеры, Geometry Nodes, физика и рендеринг делегируются Blender.

Примеры в [`examples/`](https://github.com/Rapid-Vision/rv/blob/main/examples) покрывают основные сценарии, которые используются на практике. На этой странице кратко описаны эти возможности и приведены ссылки на соответствующие примеры.

## Создание сцен через небольшой Python API

В основе `rv` лежит класс `Scene`. Вы создаете объекты, материалы, источники света и камеры напрямую из Python:

<<<@/snippets/1_basic_scene.py{python:line-numbers}

Это позволяет описывать сцену компактно, сохраняя доступ к нативным возможностям Blender. См. [`examples/1_primitives/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/1_primitives/scene.py).

### Поддержка IDE
Используйте команду `rv python install`, чтобы добавить `rv` в активное виртуальное окружение Python (venv). Это добавит автодополнение для `rv` в вашу IDE. Рекомендуется создать пустое virtual environment с нуля. Оно не используется в рантайме и нужно только для поддержки IDE.

## Live preview

`rv preview` отслеживает изменения в скрипте сцены, на лету отображает изменения и позволяет быстро итерировать перед окончательным рендером.

По умолчанию открывается окно Blender:

```bash
rv preview examples/1_primitives/scene.py
```

Используйте этот режим, если вам нужен обычный интерактивный просмотр Blender при работе с геометрией, материалами, освещением или камерой.

Если вы хотите, чтобы при каждом изменении на диск сохранялись рендеры для предпросмотра, включите `preview-files`:

```bash
rv preview examples/1_primitives/scene.py --preview-files
```

Этот комбинированный режим делает сразу две вещи: оставляет открытым окно Blender и одновременно сохраняет один сэмпл в `./preview_out` для предпросмотра. Вы можете изменить выходную директорию через `--preview-out`, задать размер изображения через `--resolution WIDTH,HEIGHT` и ограничить время рендера через `--time-limit`.

Предпросмотр в окне можно выключить с помощью флага `--no-window` вместе с `--preview-files`:

```bash
rv preview examples/1_primitives/scene.py --preview-files --no-window
```

В этом режиме Blender не открывается. Вместо этого файлы на диске постоянно обновляются. Это удобно для работы по ssh или когда нужны только итоговые изображения.

**Кратко:** доступны три сценария live preview:

1. По умолчанию: только окно Blender.
2. Headless: `--preview-files --no-window`.
3. Комбинированный: `--preview-files` для окна Blender и preview-файлов на диске.

## Импорт переиспользуемых ассетов из `.blend` файлов

Когда геометрия становится сложнее нескольких примитивов, ее удобнее собрать в Blender и импортировать из Python. `rv` загружает именованные объекты из `.blend` файла и возвращает `ObjectLoader`:

```python
rock_loader = self.load_object("./rock.blend", "Rock")
rock = rock_loader.create_instance()
```

См. [`examples/2_properties/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/2_properties/scene.py).

## Управление нодами

Синтетическим датасетам обычно нужна вариативность. В `rv` предпочтительный способ задать такую вариативность состоит в том, чтобы оставить процедурную логику внутри Blender, а управлять ею из Python через параметры объектов и модификаторов.

### Material nodes

Чтобы управлять материалом из Python:

1. Добавьте узел `Attribute` в граф материала.
![Attribute node](/assets/attribute_node.png)
2. Укажите имя атрибута, например `color_base`.
3. Установите **Attribute Type** в **Object**.
4. Считайте это значение в шейдере и задайте его через `set_property(...)`.

```python
obj.set_property("color_base", (0.93, 0.92, 0.91))
```

### Модификаторы

Для процедурной генерации объектов хороший подход состоит в том, чтобы держать логику моделирования внутри модификатора Geometry Nodes и параметризовать ее из Python.

Чтобы управлять модификатором Geometry Nodes из Python:

1. Добавьте объекту модификатор Geometry Nodes в Blender.
2. Откройте на интерфейсе модификатора те входы, которые хотите рандомизировать.
3. Меняйте эти входы из Python через `set_modifier_input(...)`.

Минимальный пример на стороне Python:

```python
obj.set_modifier_input("seed", 123.4)
```

Если у объекта несколько модификаторов Geometry Nodes, передайте также `modifier_name`:

```python
obj.set_modifier_input("seed", 123.4, modifier_name="RockGenerator")
```

Такой подход оставляет процедурное моделирование внутри Blender, а Python только подает случайные параметры, которые управляют модификатором.

Обратите внимание, что этот метод не ограничен модификаторами Geometry Nodes и может применяться и к другим модификаторам.

## Распределение множества объектов без ручной расстановки

`rv` включает несколько геометрических способов scatter-размещения, которые позволяют заполнить область большим количеством объектов и при этом избежать пересечений.

Создайте область:

```python
domain = rv.Domain.ellipse(center=(0, 0), radii=(12, 6), z=0.0)
```

Размещение простых инстансов:

```python
self.scatter_by_sphere(source=object_loader, count=350, domain=domain, min_gap=0.15)
```

Размещение с учетом формы меша:

```python
self.scatter_by_bvh(source=object_loader, count=300, domain=domain, min_gap=0.2)
```

Размещение процедурных инстансов с индивидуальными параметрами:

```python
self.scatter_parametric(source=source, count=30, domain=domain, strategy="bvh")
```

Доступные примеры показывают три полезных паттерна:

- [`examples/3_scattering/ellipse_2d.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/ellipse_2d.py): быстрое плоское распределение внутри эллипса.
- [`examples/3_scattering/hull_3d.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/hull_3d.py): заполнение трехмерного объема, заданного выпуклой оболочкой.
- [`examples/3_scattering/parametric_scatter.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/parametric_scatter.py): изменение каждого размещенного инстанса через пару sampler/applier.

Для многих синтетических сцен этого достаточно. Если вам нужны физически правдоподобные итоговые положения объектов, используйте симуляцию rigid body после или вместо геометрического scatter-размещения.

## Экспорт семантических масок

Теги объектов удобны для разметки на уровне инстансов, но многим датасетам также нужны маски для конкретных областей материала, например ржавчины, грязи, краски или износа. `rv` поддерживает это через shader AOV в Blender.

На стороне Blender запишите маску в узел `AOV Output` с именем `<channel>`:

```text
rust
```

![AO](/assets/aov_output.png)

Включите тот же канал в Python:

```python
self.enable_semantic_channels("rust", "clean_metal")
```

При необходимости можно управлять бинаризацией:

```python
self.set_semantic_mask_threshold(0.5)
```

При рендере `rv` экспортирует семантические маски, например `Mask_rust*.png` и `Mask_clean_metal*.png`. См. [`examples/4_semantic_aov/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/4_semantic_aov/scene.py) и [`examples/4_semantic_aov/README.md`](https://github.com/Rapid-Vision/rv/blob/main/examples/4_semantic_aov/README.md).

## Использование rigid body физики Blender, когда важен реализм размещения

Для куч, столкновений, падающих объектов и любых сцен, где важно корректное контактирование объектов, `rv` позволяет настраивать rigid body и запускать физику Blender напрямую из скрипта.

Добавление rigid body:

```python
plane.add_rigidbody(mode="box", body_type="PASSIVE", friction=0.9)
```

```python
cube.add_rigidbody(mode="box", body_type="ACTIVE", mass=0.2)
```

Запуск симуляции:

```python
rv.simulate_physics(frames=120, substeps=10, time_scale=1.0)
```

Это особенно полезно для генерации непересекающихся куч объектов и сцен с ударами. Примеры физики включают:

- [`examples/5_physics/simple.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/5_physics/simple.py): минимальная сцена с падающим объектом.
- [`examples/5_physics/scatter.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/5_physics/scatter.py): сброс множества случайных кубов в коробку.
- [`examples/5_physics/wall_break.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/5_physics/wall_break.py): симуляция удара, разрушающего стену.

## Экспорт сгенерированных сцен для повторного использования

Некоторые сцены дорого строить, особенно если они зависят от симуляции. `rv` может сохранить сгенерированный результат как `.blend` файл и затем использовать его в другом скрипте.

Экспорт сцены:

```bash
rv export examples/6_export/export.py -o examples/6_export/exported.blend --freeze-physics
```

Позже можно загрузить сохраненные объекты:

```python
loaders = self.load_objects(str(EXPORTED_BLEND), import_names=CUBE_NAMES)
```

И создавать из них столько инстансов, сколько нужно:

```python
obj = loader.create_instance()
```

Это полезно, когда вы хотите один раз выполнить симуляцию, а потом рендерить много вариантов камеры или освещения на основе сохраненного результата. См. [`examples/6_export/export.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/export.py), [`examples/6_export/import.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/import.py) и [`examples/6_export/README.md`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/README.md).

## Preview-текстуры

Экспортированные depth- и index-маски плохо воспринимаются человеком. Поэтому `rv` дополнительно экспортирует preview-версии этих масок.

<div class="image_block">
    <img alt="Preview Depth" src="/assets/depth_preview.png" style="width: 100%;" />
    <img alt="Preview Index" src="/assets/index_preview.png" style="width: 100%;" />
</div>

## Типичный порядок работы

На практике многие скрипты датасетов следуют одной и той же схеме:

1. Создать или импортировать ассеты.
2. Рандомизировать свойства объектов, которые управляют узлами Blender.
3. Разместить объекты вручную, через scatter или через физику.
4. Добавить теги, семантические каналы и проходы рендеринга.
5. Запустить `rv render` или сохранить промежуточную сцену через `rv export`.

Начните с изучения небольших примеров в [`examples/`](https://github.com/Rapid-Vision/rv/blob/main/examples), а затем переходите к [API reference](/ru/api/), когда понадобятся полные сигнатуры методов.
