"""Генерация порядков запуска тестов.

Стратегии:
  original - исходный порядок (как его выдаёт pytest);
  reverse  - обратный порядок (iDFlakies, Lam et al., 2019);
  random   - случайные перестановки (iDFlakies, pytest-randomly);
  tuscan   - тосканский квадрат (Wei et al., TACAS 2021): каждая упорядоченная
             пара соседних тестов (a, b), a != b, встречается хотя бы в одном порядке.
"""
import random


def williams_rows(n):
    """Строчно-полный латинский квадрат n x n для чётного n (построение Уильямса, 1949).

    Первая строка 0, 1, n-1, 2, n-2, ...; строка i получается прибавлением i по модулю n.
    Разности соседей в первой строке (+1, -2, +3, -4, ...) попарно различны по модулю n,
    поэтому каждая упорядоченная пара (a, b), a != b, стоит рядом ровно в одной строке.
    """
    first, lo, hi = [0], 1, n - 1
    while len(first) < n:
        first.append(lo)
        lo += 1
        if len(first) < n:
            first.append(hi)
            hi -= 1
    return [[(x + i) % n for x in first] for i in range(n)]


def tuscan_orders(tests):
    """Порядки, покрывающие все n(n-1) пар соседей: n порядков (n чётно) или n+1 (n нечётно).

    Для нечётного n строится квадрат для n+1 элементов с фиктивным тестом n, который
    затем вычёркивается: пары соседних реальных тестов при этом сохраняются.
    """
    n = len(tests)
    if n < 2:
        return [list(tests)]
    m = n if n % 2 == 0 else n + 1
    return [[tests[i] for i in row if i < n] for row in williams_rows(m)]


def make_orders(strategy, tests, k=None, seed=0):
    """Список порядков для стратегии; k ограничивает их число (бюджет запусков)."""
    tests = list(tests)
    if strategy == "original":
        orders = [tests]
    elif strategy == "reverse":
        orders = [tests[::-1]]
    elif strategy == "random":
        rnd = random.Random(seed)
        orders = [rnd.sample(tests, len(tests)) for _ in range(k or len(tests))]
    elif strategy == "tuscan":
        orders = tuscan_orders(tests)
    else:
        raise ValueError("unknown strategy: " + strategy)
    return orders[:k] if k else orders


def pair_coverage(orders, n):
    """Доля покрытых упорядоченных пар соседних тестов среди всех n(n-1) пар."""
    pairs = {(a, b) for order in orders for a, b in zip(order, order[1:])}
    return len(pairs) / (n * (n - 1)) if n > 1 else 1.0
