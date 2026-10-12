# odflaky: обнаружение order-dependent флаки-тестов в Python

[English version](README.md)

# Авторы

Основной автор — Ябров Илья Константинович, студент ИКНК СПбПУ.

Руководитель — Пархоменко Владимир Андреевич, старший преподаватель ИКНК СПбПУ.

# Введение

Order-dependent (OD) тест проходит или падает в зависимости от порядка, в котором запускаются тесты набора.
*Victim* проходит в изоляции, но падает после теста-*polluter* (если между ними не выполнился *cleaner*);
*brittle*-тест падает в изоляции и проходит только после теста-*state-setter*.

`odflaky` сравнивает способы выбора порядков запуска:

- `random` — случайные перестановки, как в iDFlakies [Lam et al., ICST 2019] и pytest-randomly;
- `tuscan` — тосканские квадраты [Wei et al., TACAS 2021]: n порядков (n+1 при нечётном n), в которых каждая
  упорядоченная пара тестов (a, b) хотя бы раз выполняется подряд, поэтому любой OD-тест с единственным
  polluter/state-setter гарантированно обнаруживается;
- `reverse` и `original` оставлены как дешёвые базовые варианты.

Для каждого найденного OD-теста инструмент определяет его вид (victim / brittle), находит минимальный polluter
или state-setter дельта-отладкой [Zeller, Hildebrandt, 2002], как в iFixFlakies [Shi et al., ESEC/FSE 2019], а с
флагом `--exhaustive` — все polluter/state-setter и cleaner, как в наборе данных iPFlakies [Wang et al., ICSE 2022].

Набор тестов задаётся либо реальным pytest-проектом (каждый порядок выполняется в новом процессе Python),
либо JSON-моделью набора произвольного размера.

# Инструкция

## Требования

Python 3.8–3.11 и git. Все команды выполняются из корня репозитория.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate в Linux/macOS
pip install -r requirements.txt -r bench/requirements.txt
```

## ШАГ 1. Модульные тесты инструмента

```bash
python -m pytest tests
```

## ШАГ 2. Авторский иллюстративный пример (4 теста)

`examples/lang_app` содержит четыре настоящих pytest-теста с общим глобальным состоянием;
`examples/example4.json` — их JSON-модель. Оба варианта должны дать эталонный выход `expected/example4.json`:

```bash
python -m odflaky run --suite examples/example4.json --exhaustive --trace --expected expected/example4.json
python -m odflaky run --pytest examples/lang_app --exhaustive --trace --expected expected/example4.json
```

`--trace` печатает каждый выполненный порядок и упавшие тесты (пошаговое выполнение, приведённое в отчёте).

## ШАГ 3. Эталонный бенчмарк из набора данных iPFlakies

```bash
python bench/setup_bench.py
python -m odflaky run --pytest bench/repos/IOCynergy --exhaustive --ipflakies data/ipflakies_subset.csv
python -m odflaky run --pytest bench/repos/GOApy --exhaustive --ipflakies data/ipflakies_subset.csv
```

`bench/setup_bench.py` клонирует проекты на коммитах из набора данных и применяет к IOCynergy однострочное
исправление совместимости с Python 3.9+ (см. `bench/projects.json`).
`data/ipflakies_subset.csv` — строки `Minimized.csv` из набора данных iPFlakies
(https://doi.org/10.5281/zenodo.6176417) для этих проектов; команда печатает `RESULT: MATCH`, если найденный
OD-тест, его вид, все polluter/state-setter и cleaner совпадают с разметкой.
В Windows три теста GOApy (`Automaton_test.py`) падают всегда, потому что вызывают команды Unix-оболочки;
они не являются флаки-тестами и на результат не влияют.

## ШАГ 4. Входные данные переменного объёма

```bash
python -m odflaky gen --tests 500 --victims 25 --brittles 12 --max-cleaners 250 --seed 1 --out data/synthetic_500.json
python -m odflaky run --suite data/synthetic_500.json --strategy tuscan
python -m odflaky run --suite data/synthetic_500.json --strategy random --orders 500 --seed 1
```

## ШАГ 5. Эксперименты и графики

```bash
python experiments/run_experiments.py      # ~15 мин; --skip-real — только синтетическая часть (~1 мин)
python experiments/plots.py
```

Результаты сохраняются в `results/` (CSV-файлы `e1`–`e4`, графики `fig_*.pdf`).

## Командная строка

```text
python -m odflaky run (--suite FILE.json | --pytest DIR [--python PY])
                      [--strategy original|reverse|random|tuscan] [--orders K] [--seed S]
                      [--exhaustive] [--trace] [--out FILE] [--expected FILE] [--ipflakies CSV [--project NAME]]
python -m odflaky gen --tests N [--victims V] [--brittles B] [--max-cleaners C] [--seed S] --out FILE
```

## JSON-модель набора тестов

```json
{
 "name": "example4",
 "tests": ["t1", "t2", "t3", "t4"],
 "victims":  {"t1": {"polluters": ["t4"], "cleaners": ["t2"]}},
 "brittles": {"t3": {"setters": ["t2"]}}
}
```

`tests` — исходный порядок. Victim падает тогда и только тогда, когда ближайший предшествующий ему тест из его
polluter'ов и cleaner'ов является polluter'ом; brittle-тест проходит, если до него выполнялся хотя бы один
его state-setter.

## Структура репозитория

```text
odflaky/            инструмент
  orders.py           стратегии порядков, тосканские квадраты (построение Уильямса), покрытие пар
  model.py            JSON-модель набора тестов, генератор синтетических наборов
  pytest_suite.py     запуск реального pytest-проекта в заданном порядке (процесс на порядок)
  pytest_plugin.py    плагин pytest: переупорядочивает собранные тесты и записывает исходы
  detect.py           обнаружение, классификация, дельта-отладка, polluter'ы и cleaner'ы
  __main__.py         командная строка
examples/           авторский иллюстративный пример (pytest-проект и его JSON-модель)
expected/           эталонный выход для примера
data/               подмножество разметки iPFlakies, синтетический набор из 500 тестов
bench/              проекты бенчмарка (коммиты, патчи совместимости, зависимости)
experiments/        скрипты экспериментов и графиков
results/            полученные CSV-файлы и графики
tests/              модульные тесты инструмента
```
