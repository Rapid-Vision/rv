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

## Seed

Каждому вызову `Scene.generate(...)` передается значение `seed`. Используйте его, чтобы управлять рандомизацией воспроизводимым способом:

```python
import random

class BasicScene(rv.Scene):
    def generate(self, seed):
        rng = random.Random(seed)
```

Это рекомендуемый паттерн для управления вариативностью сцены. Фиксированный seed воспроизводит одну и ту же сгенерированную сцену, а разные seed дают разные наборы параметров.

Управлять seed можно из CLI для `render`, `preview` и `export`:

```bash
rv render scene.py --seed rand
rv render scene.py --seed seq
rv render scene.py --seed 42
```

- `rand`: случайный seed для каждого запуска.
- `seq`: детерминированная последовательность seed для набора выходных данных.
- `<integer>`: один конкретный seed для воспроизводимого результата. При его использовании имеет смысл только генерация единственного сэмпла, так как все результаты все равно будут одинаковыми.

Простой пример паттерна `random.Random(seed)` см. в [`examples/2_properties/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/2_properties/scene.py).

## Генерация вспомогательных ассетов вне blender

Некоторые ассеты проще вне Blender. Например, это могут быть текстуры с текстом или ассеты, для получения которых нужны сложные вычисления. Для этого в `rv` есть механизм генераторов.

Генератор это программа, которая получает JSON-запрос через `stdin` с текущим seed сцены, `root_dir`, `work_dir` и любыми именованными параметрами, которые вы передаете из Python. В `stdout` она должна вернуть JSON вида `{"result": ...}`.

Вызов генератора выглядит так:

```python
generator = self.generators.init("uv run ./gen.py")
texture_path = generator.generate_path()
```

Используйте:

- `generate(...)` для любого JSON-совместимого результата.
- `generate_path(...)` для генераторов, которые создают файлы.
- `generate_str(...)` для строковых результатов.
- `generate_num(...)` для числовых результатов.

Такой подход позволяет оставить основной скрипт сфокусированным на сборке сцены внутри Blender, а генерацию вспомогательных ассетов вынести в отдельные программы на любом языке программирования с любыми зависимостями.

По умолчанию каждый запуск получает собственную рабочую директорию в `<root_dir>/generated`. Можно указать другое расположение с помощью `--gen-dir`:

```bash
rv render examples/9_generator/scene.py --cwd examples/9_generator --gen-dir ./tmp/gen
```

Удаление артефактов регулируется флагом `--gen-retain`:

- `all`: сохранить все рабочие директории генератора.
- `last`: сохранить только последнюю рабочую директорию.
- `none`: удалить все рабочие директории генератора после завершения работы команды.

Значения по умолчанию выбраны под типичные сценарии:

- `rv preview`: `last`, чтобы можно было посмотреть последние артефакты предпросмотра.
- `rv render`: `none`, чтобы пакетный рендер не накапливал временные файлы.
- `rv export`: `all`, чтобы экспортированная сцена по умолчанию сохраняла все связанные с ней сгенерированные ассеты. Для получения переносимого файла можно использовать `--pack-resources --gen-retain none`.

См. [`examples/9_generator/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/9_generator/scene.py) и [`examples/9_generator/README.md`](https://github.com/Rapid-Vision/rv/blob/main/examples/9_generator/README.md).

## Импорт переиспользуемых ассетов из `.blend` файлов

Когда геометрия становится сложнее нескольких примитивов, ее удобнее собрать в Blender и импортировать из Python. `rv` загружает именованные объекты из `.blend` файла и возвращает `ObjectLoader`:

```python
rock_loader = self.assets.object("./rock.blend", "Rock")
rock = rock_loader.create_instance()
```

См. [`examples/2_properties/scene.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/2_properties/scene.py).

## Построение графа шейдера

`rv` позволяет собирать графы шейдеров Blender напрямую из кода.

<<<@/snippets/8_shader_graph.py{python:line-numbers}

Эта возможность все еще находится в разработке. Большинство нод пока недоступны.


## Параметризация сценты 

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
- [`examples/3_scattering/custom_domain.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/3_scattering/custom_domain.py): пользовательский трехмерный домен для области `abs(z) > x^2 + y^2`.

Можно определить и собственный scatter-домен, передав функции проверки принадлежности и ограничивающего bounding box:

```python
domain = rv.Domain.custom(
    dimension=3,
    contains_point=lambda point, margin: (
        (point.z * point.z) < (point.x * point.x + point.y * point.y)
    ),
    aabb=lambda inset_margin: (
        rv.Vector((-10.0, -10.0, -6.0)),
        rv.Vector((10.0, 10.0, 6.0)),
    ),
)
```

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
cube.add_rigidbody(
    mode="box",
    body_type="ACTIVE",
    mass=0.2,
    collision_margin=0.01,
    use_deactivation=True,
    deactivate_linear_velocity=0.15,
    deactivate_angular_velocity=0.2,
)
```

Запуск симуляции:

```python
rv.simulate_physics(
    frames=120,
    substeps=12,
    solver_iterations=30,
    use_split_impulse=True,
    time_scale=1.0,
)
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
loaders = self.assets.objects("exported.blend", import_names=CUBE_NAMES)
```

И создавать из них столько инстансов, сколько нужно:

```python
obj = loader.create_instance()
```

Это полезно, когда вы хотите один раз выполнить симуляцию, а потом рендерить много вариантов камеры или освещения на основе сохраненного результата. См. [`examples/6_export/export.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/export.py), [`examples/6_export/import.py`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/import.py) и [`examples/6_export/README.md`](https://github.com/Rapid-Vision/rv/blob/main/examples/6_export/README.md).

## Человекочитаемый результат

Экспортированные depth- и index-маски плохо воспринимаются человеком. Поэтому `rv` дополнительно экспортирует человекочитаемые версии этих масок.

<div class="image_block">
    <img alt="Preview Depth" src="/assets/depth_preview.png" style="width: 100%;" />
    <img alt="Preview Index" src="/assets/index_preview.png" style="width: 100%;" />
</div>

## Дополнительные материалы
Начните с изучения небольших примеров в [`examples/`](https://github.com/Rapid-Vision/rv/blob/main/examples), а затем переходите к [API reference](/ru/api/), когда понадобятся полные сигнатуры методов.
