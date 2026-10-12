"""Обнаружение order-dependent (OD) тестов и поиск их причин.

Этапы (по iDFlakies / iFixFlakies / iPFlakies):
  1) detect   - прогнать исходный порядок и порядки выбранной стратегии; OD-тест - тот,
                у которого наблюдались и pass, и fail;
  2) classify - запуск в изоляции: проходит -> victim, падает -> brittle;
  3) culprit  - delta debugging по префиксу «свидетельского» порядка: минимальный polluter
                (для victim) или state-setter (для brittle);
  4) exhaustive (необязательно) - все polluter'ы/setter'ы парами [u, t] и все cleaner'ы
                тройками [p, c, v] - как в наборе данных iPFlakies.
"""
from .orders import make_orders, pair_coverage


class Runner:
    """Исполнитель порядков с кэшем: одинаковый порядок не запускается повторно."""

    def __init__(self, suite, trace=None):
        self.suite, self.trace = suite, trace
        self.cache, self.runs = {}, 0

    def __call__(self, order):
        key = tuple(order)
        if key not in self.cache:
            self.cache[key] = self.suite.run(list(order))
            self.runs += 1
            if self.trace:
                self.trace(self.runs, order, self.cache[key])
        return self.cache[key]

    def outcome(self, prefix, test):
        """Исход теста test, запущенного после тестов prefix."""
        return self([*prefix, test])[test]


def detect(runner, orders):
    """Алгоритм 1. Возвращает {тест: (номер порядка обнаружения, порядок с pass, порядок с fail)}."""
    witness, found = {}, {}
    for k, order in enumerate(orders):
        for test, outcome in runner(order).items():
            if outcome in ("pass", "fail"):
                witness.setdefault(test, {}).setdefault(outcome, order)
                if test not in found and len(witness[test]) == 2:
                    found[test] = k
    return {t: (k, witness[t]["pass"], witness[t]["fail"]) for t, k in found.items()}


def ddmin(items, reproduces):
    """Алгоритм 2. Delta debugging (Zeller, Hildebrandt, 2002): 1-минимальное подмножество
    items (с сохранением порядка), на котором эффект ещё воспроизводится."""
    n = 2
    while len(items) >= 2:
        size = len(items)
        chunks = [items[size * i // n: size * (i + 1) // n] for i in range(n)]
        subset = next((c for c in chunks if reproduces(c)), None)
        if subset is not None:  # эффект даёт одна из частей - продолжаем с ней
            items, n = subset, 2
            continue
        complements = ([x for c in chunks if c is not ch for x in c] for ch in chunks) if n > 2 else ()
        subset = next((c for c in complements if reproduces(c)), None)
        if subset is not None:  # эффект даёт дополнение к одной из частей
            items, n = subset, max(n - 1, 2)
            continue
        if n >= size:
            break
        n = min(2 * n, size)  # дробим мельче
    return items


def analyze(suite, strategy="tuscan", k=None, seed=0, exhaustive=False, trace=None):
    runner = Runner(suite, trace)
    tests = suite.tests
    orders = [tests] + make_orders(strategy, tests, k, seed)  # порядок 0 - исходный
    found = detect(runner, orders)
    detection_runs = runner.runs
    od_tests = []
    for test in sorted(found, key=tests.index):
        k_found, pass_order, fail_order = found[test]
        kind = "victim" if runner.outcome([], test) == "pass" else "brittle"
        # victim: ищем polluter в префиксе падающего порядка; brittle: setter в префиксе проходящего
        want, order = ("fail", fail_order) if kind == "victim" else ("pass", pass_order)
        prefix = list(order[:order.index(test)])
        item = {"test": test, "type": kind, "found_at_order": k_found,
                "culprit": ddmin(prefix, lambda sub: runner.outcome(sub, test) == want)}
        if exhaustive:
            item["culprits_all"] = [u for u in tests if u != test and runner.outcome([u], test) == want]
            if kind == "victim":
                item["cleaners"] = {p: [c for c in tests if c not in (test, p) and runner.outcome([p, c], test) == "pass"]
                                    for p in item["culprits_all"]}
        od_tests.append(item)
    return {"suite": suite.name, "tests": len(tests), "strategy": strategy, "seed": seed,
            "orders": len(orders), "pair_coverage": round(pair_coverage(orders, len(tests)), 4),
            "detection_runs": detection_runs, "total_runs": runner.runs, "od_tests": od_tests}
