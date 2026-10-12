# odflaky: detecting order-dependent flaky tests in Python

# Authors and contributors

The main contributor is Ilya K. Yabrov, student of SPbPU ICSC.

The advisor and contributor is Vladimir A. Parkhomenko, Senior Lecturer of SPbPU ICSC.

# Introduction

An order-dependent (OD) test passes or fails depending on the order in which the tests of a suite are run.
A *victim* passes alone but fails after a *polluter* (unless a *cleaner* runs in between);
a *brittle* test fails alone and passes only after a *state-setter*.

`odflaky` compares two ways of choosing test orders:

- `random` - random permutations, as in iDFlakies [Lam et al., ICST 2019] and pytest-randomly;
- `tuscan` - Tuscan squares [Wei et al., TACAS 2021]: n orders (n+1 for odd n) in which every ordered pair
  of tests (a, b) runs consecutively at least once, so every OD test with a single polluter/setter is
  guaranteed to be found;
- `reverse` and `original` are kept as cheap baselines.

For every OD test found the tool classifies it (victim / brittle), finds a minimal polluter or state-setter
with delta debugging [Zeller, Hildebrandt, 2002], as in iFixFlakies [Shi et al., ESEC/FSE 2019], and,
with `--exhaustive`, all polluters/setters and cleaners, as in the iPFlakies dataset [Wang et al., ICSE 2022].

Test suites are given either as a real pytest project (each order runs in a fresh Python process)
or as a JSON model of a suite of any size.

# Instruction

## Prerequisites

Python 3.8-3.11 and git. All commands are run from the repository root.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on Linux/macOS
pip install -r requirements.txt -r bench/requirements.txt
```

## STEP 1. Unit tests of the tool

```bash
python -m pytest tests
```

## STEP 2. Author's illustrative example (4 tests)

`examples/lang_app` contains four real pytest tests sharing global state;
`examples/example4.json` is their JSON model. Both must give the reference output `expected/example4.json`:

```bash
python -m odflaky run --suite examples/example4.json --exhaustive --trace --expected expected/example4.json
python -m odflaky run --pytest examples/lang_app --exhaustive --trace --expected expected/example4.json
```

`--trace` prints every executed order and the failed tests (the step-by-step run used in the report).

## STEP 3. Reference benchmark from the iPFlakies dataset

```bash
python bench/setup_bench.py
python -m odflaky run --pytest bench/repos/IOCynergy --exhaustive --ipflakies data/ipflakies_subset.csv
python -m odflaky run --pytest bench/repos/GOApy --exhaustive --ipflakies data/ipflakies_subset.csv
```

`bench/setup_bench.py` clones the projects at the commits of the dataset and applies a one-line
Python 3.9+ compatibility fix to IOCynergy (see `bench/projects.json`).
`data/ipflakies_subset.csv` is the subset of `Minimized.csv` from the iPFlakies dataset
(https://doi.org/10.5281/zenodo.6176417) for these projects; the command prints `RESULT: MATCH`
when the detected OD test, its type, all polluters/setters and the cleaner coincide with the dataset.
On Windows three GOApy tests (`Automaton_test.py`) always fail because they call Unix shell commands;
they are not flaky and do not affect the result.

## STEP 4. Inputs of variable size

```bash
python -m odflaky gen --tests 500 --victims 25 --brittles 12 --max-cleaners 250 --seed 1 --out data/synthetic_500.json
python -m odflaky run --suite data/synthetic_500.json --strategy tuscan
python -m odflaky run --suite data/synthetic_500.json --strategy random --orders 500 --seed 1
```

## STEP 5. Experiments and plots

```bash
python experiments/run_experiments.py      # ~15 min; --skip-real for the synthetic part only (~1 min)
python experiments/plots.py
```

Results are written to `results/` (`e1`-`e4` CSV files, `fig_*.pdf`).

## Command line

```text
python -m odflaky run (--suite FILE.json | --pytest DIR [--python PY])
                      [--strategy original|reverse|random|tuscan] [--orders K] [--seed S]
                      [--exhaustive] [--trace] [--out FILE] [--expected FILE] [--ipflakies CSV [--project NAME]]
python -m odflaky gen --tests N [--victims V] [--brittles B] [--max-cleaners C] [--seed S] --out FILE
```

## JSON model of a test suite

```json
{
 "name": "example4",
 "tests": ["t1", "t2", "t3", "t4"],
 "victims":  {"t1": {"polluters": ["t4"], "cleaners": ["t2"]}},
 "brittles": {"t3": {"setters": ["t2"]}}
}
```

`tests` is the original order. A victim fails iff the closest preceding test among its polluters and
cleaners is a polluter; a brittle test passes iff one of its setters ran before it.

## Repository structure

```text
odflaky/            the tool
  orders.py           order strategies, Tuscan squares (Williams construction), pair coverage
  model.py            JSON model of a suite, generator of synthetic suites
  pytest_suite.py     running a real pytest project in a given order (one process per order)
  pytest_plugin.py    pytest plugin: reorders collected tests and records outcomes
  detect.py           detection, classification, delta debugging, polluters/cleaners
  __main__.py         command line
examples/           author's illustrative example (pytest project and its JSON model)
expected/           reference output for the example
data/               iPFlakies ground truth subset
bench/              benchmark projects (commits, compatibility patches, dependencies)
experiments/        experiment and plotting scripts
results/            produced CSV files and figures
tests/              unit tests of the tool
```
