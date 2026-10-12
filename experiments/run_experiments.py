"""Эксперименты для отчёта; результаты - CSV в каталоге results/.

  E1  вероятность падения OD-теста в случайном порядке: теория p/(p+c+1), 1/(s+1) vs эмпирика;
  E2  покрытие пар соседних тестов: random (эмпирика и 1-(1-1/n)^k) vs tuscan;
  E3  синтетические наборы n = 10..500: доля найденных OD-тестов при бюджете k порядков;
  E4  реальные проекты iPFlakies: original / reverse / random / tuscan; теория vs эмпирика
      и согласие модели (найденные polluter/cleaner/setter) с реальными запусками.

Запуск:  python experiments/run_experiments.py [--skip-real]
"""
import csv
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from odflaky.detect import analyze  # noqa: E402
from odflaky.model import ModelSuite, generate  # noqa: E402
from odflaky.orders import make_orders, pair_coverage  # noqa: E402
from odflaky.pytest_suite import PytestSuite  # noqa: E402

OUT = ROOT / "results"


def save(name, rows):
    with open(OUT / name, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("saved results/%s (%d rows)" % (name, len(rows)))


def e1_probability(n=100, samples=5000):
    rows, rnd = [], random.Random(1)
    tests = ["t%03d" % i for i in range(n)]
    for p, c in [(1, 0), (1, 1), (2, 1), (3, 6), (1, 5), (1, 20), (3, 20), (1, 80)]:
        suite = ModelSuite({"tests": tests, "victims": {"t000": {"polluters": tests[1:1 + p],
                                                                  "cleaners": tests[1 + p:1 + p + c]}}})
        fails = sum(suite.run(rnd.sample(tests, n))["t000"] == "fail" for _ in range(samples))
        rows.append({"kind": "victim", "p_or_s": p, "c": c, "theory": round(p / (p + c + 1), 4),
                     "empirical": round(fails / samples, 4), "samples": samples})
    for s in [1, 2, 4, 8]:
        suite = ModelSuite({"tests": tests, "brittles": {"t000": {"setters": tests[1:1 + s]}}})
        fails = sum(suite.run(rnd.sample(tests, n))["t000"] == "fail" for _ in range(samples))
        rows.append({"kind": "brittle", "p_or_s": s, "c": 0, "theory": round(1 / (s + 1), 4),
                     "empirical": round(fails / samples, 4), "samples": samples})
    save("e1_probability.csv", rows)


def e2_pair_coverage(seeds=10):
    rows = []
    for n in [20, 100]:
        tests = list(range(n))
        tuscan = make_orders("tuscan", tests)
        randoms = [make_orders("random", tests, 3 * n, seed) for seed in range(seeds)]
        for k in sorted({1, 2, 5, 10} | set(range(n // 10, 3 * n + 1, n // 10))):
            rows.append({"n": n, "k": k,
                         "random": round(sum(pair_coverage(o[:k], n) for o in randoms) / seeds, 4),
                         "random_theory": round(1 - (1 - 1 / n) ** k, 4),
                         "tuscan": round(pair_coverage(tuscan[:k], n), 4)})
    save("e2_pair_coverage.csv", rows)


def e3_synthetic(seeds=10):
    curve, scale = [], []
    for n in [10, 20, 50, 100, 200, 500]:
        stats = {"random": [], "tuscan": []}  # номера порядков, на которых найден каждый OD-тест
        times = {"random": 0.0, "tuscan": 0.0}
        for seed in range(seeds):
            data = generate(n, victims=max(1, n // 20), brittles=max(1, n // 40), cleaners=(0, n // 2), seed=seed)
            suite = ModelSuite(data)
            total = len(data["victims"]) + len(data["brittles"])
            for strategy in stats:
                start = time.perf_counter()
                k = 10 * n if strategy == "random" else None
                res = analyze(suite, strategy, k, seed)
                times[strategy] += time.perf_counter() - start
                found = [it["found_at_order"] for it in res["od_tests"]]
                stats[strategy] += found + [float("inf")] * (total - len(found))
        budget = n + n % 2  # число тосканских порядков
        for strategy, found in stats.items():
            scale.append({"n": n, "strategy": strategy, "od_tests": len(found),
                          "found_at_k1": round(sum(f <= 1 for f in found) / len(found), 3),
                          "found_at_budget": round(sum(f <= budget for f in found) / len(found), 3),
                          "orders_for_all": max(found), "time_s": round(times[strategy] / seeds, 3)})
            if n == 100:
                curve += [{"k": k, "strategy": strategy, "found": round(sum(f <= k for f in found) / len(found), 3)}
                          for k in range(0, 3 * n + 1, 5)]
    save("e3_scaling.csv", scale)
    save("e3_curve_n100.csv", curve)


PROJECTS = ("IOCynergy", "GOApy")


def e4_real(seeds=10):
    rows = []
    for name in PROJECTS:
        suite = PytestSuite(ROOT / "bench" / "repos" / name)
        for strategy, seed_list in [("original", [0]), ("reverse", [0]), ("tuscan", [0]), ("random", range(seeds))]:
            for seed in seed_list:
                start = time.perf_counter()
                res = analyze(suite, strategy, None, seed)
                rows.append({"project": name, "strategy": strategy, "seed": seed, "orders": res["orders"],
                             "od_found": len(res["od_tests"]),
                             "found_at": ";".join(str(it["found_at_order"]) for it in res["od_tests"]) or "-",
                             "detection_runs": res["detection_runs"], "total_runs": res["total_runs"],
                             "time_s": round(time.perf_counter() - start, 2)})
                print(rows[-1])
    save("e4_real.csv", rows)


def e4_probability(samples=300):
    """Доля падений OD-теста в случайных порядках: теория по найденным p, c, s vs эмпирика;
    agreement - доля порядков, где модель (ModelSuite из найденных причин) предсказала исход верно."""
    rows = []
    for name in PROJECTS:
        suite = PytestSuite(ROOT / "bench" / "repos" / name)
        ref = json.loads((OUT / ("%s_tuscan.json" % name)).read_text(encoding="utf-8"))["od_tests"][0]
        test, p = ref["test"], len(ref["culprits_all"])
        cleaners = next(iter(ref.get("cleaners", {"": []}).values()))
        if ref["type"] == "victim":
            spec, theory = {"victims": {test: {"polluters": ref["culprits_all"], "cleaners": cleaners}}}, p / (p + len(cleaners) + 1)
        else:
            spec, theory = {"brittles": {test: {"setters": ref["culprits_all"]}}}, 1 / (p + 1)
        model = ModelSuite(dict(spec, tests=suite.tests))
        rnd, fails, agree = random.Random(7), 0, 0
        for _ in range(samples):
            order = rnd.sample(suite.tests, len(suite.tests))
            actual = suite.run(order)[test]
            fails += actual == "fail"
            agree += actual == model.run(order)[test]
        rows.append({"project": name, "test": test, "type": ref["type"], "p_or_s": p, "c": len(cleaners),
                     "theory": round(theory, 4), "empirical": round(fails / samples, 4),
                     "agreement": round(agree / samples, 4), "samples": samples})
        print(rows[-1])
    save("e4_real_probability.csv", rows)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    e1_probability()
    e2_pair_coverage()
    e3_synthetic()
    if "--skip-real" not in sys.argv:
        e4_real()
        e4_probability()
