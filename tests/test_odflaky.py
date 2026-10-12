"""Модульные тесты odflaky: python -m pytest tests"""
import json
from itertools import permutations
from pathlib import Path

import pytest

from odflaky.detect import analyze, ddmin
from odflaky.model import ModelSuite, generate
from odflaky.orders import make_orders, pair_coverage, tuscan_orders
from odflaky.pytest_suite import PytestSuite

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = json.loads((ROOT / "expected" / "example4.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("n", range(2, 31))
def test_tuscan_covers_all_pairs(n):
    tests = list(range(n))
    orders = tuscan_orders(tests)
    assert len(orders) == (n if n % 2 == 0 else n + 1)
    assert all(sorted(o) == tests for o in orders)  # каждый порядок - перестановка
    assert pair_coverage(orders, n) == 1.0
    assert {o[0] for o in orders} == set(tests)  # каждый тест хотя бы раз идёт первым


def test_random_orders_are_reproducible():
    assert make_orders("random", list(range(10)), 5, seed=3) == make_orders("random", list(range(10)), 5, seed=3)


@pytest.mark.parametrize("culprits", [{7}, {0}, {3, 12}])
def test_ddmin_finds_minimal_subset(culprits):
    found = ddmin(list(range(16)), lambda sub: culprits <= set(sub))
    assert set(found) == culprits


def test_victim_probability_formula():
    """Перебор всех 4! порядков примера: victim падает в доле p/(p+c+1) = 1/3, brittle - 1/(s+1) = 1/2."""
    suite = ModelSuite.load(ROOT / "examples" / "example4.json")
    runs = [suite.run(list(o)) for o in permutations(suite.tests)]
    assert sum(r["test_app.py::test_greet"] == "fail" for r in runs) == 8
    assert sum(r["test_app.py::test_query"] == "fail" for r in runs) == 12


def test_model_example_matches_expected():
    result = analyze(ModelSuite.load(ROOT / "examples" / "example4.json"), "tuscan", exhaustive=True)
    assert result["od_tests"] == EXPECTED["od_tests"]


def test_pytest_example_matches_model():
    """Реальные pytest-тесты examples/lang_app дают тот же результат, что и их модель."""
    result = analyze(PytestSuite(ROOT / "examples" / "lang_app"), "tuscan", exhaustive=True)
    assert result["od_tests"] == EXPECTED["od_tests"]


@pytest.mark.parametrize("seed", range(5))
def test_tuscan_detects_all_synthetic_od_tests(seed):
    data = generate(40, victims=3, brittles=2, cleaners=(0, 20), seed=seed)
    result = analyze(ModelSuite(data), "tuscan")
    found = {it["test"]: it for it in result["od_tests"]}
    assert set(found) == set(data["victims"]) | set(data["brittles"])
    for test, item in found.items():  # найденная причина действительно из модели
        spec = data["victims"].get(test, {}).get("polluters") or data["brittles"][test]["setters"]
        assert len(item["culprit"]) == 1 and item["culprit"][0] in spec


def test_random_strategy_with_tiny_budget_can_miss():
    data = {"tests": ["v", "p"] + ["c%d" % i for i in range(30)],
            "victims": {"v": {"polluters": ["p"], "cleaners": ["c%d" % i for i in range(30)]}}}
    misses = sum(not analyze(ModelSuite(data), "random", k=1, seed=s)["od_tests"] for s in range(50))
    assert misses > 40  # вероятность обнаружения за один порядок всего 1/32
    assert analyze(ModelSuite(data), "tuscan")["od_tests"]  # а тосканские порядки находят всегда
