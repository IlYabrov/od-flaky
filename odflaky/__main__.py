"""Командная строка odflaky.

  python -m odflaky run --suite examples/example4.json --exhaustive --trace
  python -m odflaky run --pytest examples/lang_app --expected expected/example4.json
  python -m odflaky run --pytest bench/repos/IOCynergy --exhaustive --ipflakies data/ipflakies_subset.csv
  python -m odflaky gen --tests 200 --victims 5 --brittles 3 --seed 1 --out data/synthetic_200.json
"""
import argparse
import csv
import json
import sys

from .detect import analyze
from .model import ModelSuite, generate
from .pytest_suite import PytestSuite


def short(test):
    return test.split("::")[-1]


def print_trace(run, order, result):
    failed = [short(t) for t in order if result.get(t) == "fail"]
    print("  run %3d: %s  ->  fail: %s" % (run, " ".join(short(t) for t in order), ", ".join(failed) or "-"),
          file=sys.stderr)


def check_expected(result, path):
    """Сравнение с эталонным выходом (JSON): тип, найденный порядок, polluter/setter, cleaner'ы."""
    with open(path, encoding="utf-8") as f:
        expected = {it["test"]: it for it in json.load(f)["od_tests"]}
    actual = {it["test"]: it for it in result["od_tests"]}
    ok = set(expected) == set(actual)
    for test, exp in expected.items():
        act = actual.get(test, {})
        diff = [key for key in exp if key != "test" and act.get(key) != exp[key]]
        ok &= not diff
        print("  %-40s %s" % (short(test), "OK" if not diff else "MISMATCH " + ", ".join(diff)))
    return ok


def check_ipflakies(result, path, project):
    """Сравнение с разметкой набора данных iPFlakies (Wang et al., ICSE 2022, Minimized.csv)."""
    with open(path, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["Project_Name"] == project]
    actual = {it["test"]: it for it in result["od_tests"]}
    ok = bool(rows)
    for test in sorted({r["Test_id"] for r in rows}):
        truth = [r for r in rows if r["Test_id"] == test]
        act = actual.get(test, {})
        checks = {"detected": bool(act),
                  "type": act.get("type") == truth[0]["OD_Type"],
                  "culprits": set(act.get("culprits_all", [])) == {r["Polluter_or_Setter"] for r in truth},
                  "cleaners": all(r["Cleaner"] in act.get("cleaners", {}).get(r["Polluter_or_Setter"], [])
                                  for r in truth if r["Cleaner"])}
        ok &= all(checks.values())
        print("  %-60s %s" % (test, " ".join("%s=%s" % (k, "OK" if v else "NO") for k, v in checks.items())))
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(prog="odflaky", description="Detect order-dependent flaky tests")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="detect OD tests and their polluters/setters")
    src = run.add_mutually_exclusive_group(required=True)
    src.add_argument("--suite", help="JSON model of a test suite")
    src.add_argument("--pytest", help="directory of a pytest project")
    run.add_argument("--python", default=sys.executable, help="interpreter for the pytest project")
    run.add_argument("--strategy", default="tuscan", choices=["original", "reverse", "random", "tuscan"])
    run.add_argument("--orders", type=int, help="limit the number of orders (run budget)")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--exhaustive", action="store_true", help="find all polluters/setters and cleaners")
    run.add_argument("--trace", action="store_true", help="print every executed order")
    run.add_argument("--out", help="write result JSON to the file")
    run.add_argument("--expected", help="reference output JSON to compare with")
    run.add_argument("--ipflakies", help="iPFlakies CSV with ground truth for the project")
    run.add_argument("--project", help="project name in the iPFlakies CSV (default: directory name)")
    gen = sub.add_parser("gen", help="generate a synthetic JSON suite of a given size")
    gen.add_argument("--tests", type=int, required=True)
    gen.add_argument("--victims", type=int, default=3)
    gen.add_argument("--brittles", type=int, default=2)
    gen.add_argument("--max-cleaners", type=int, default=10)
    gen.add_argument("--seed", type=int, default=0)
    gen.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "gen":
        data = generate(args.tests, args.victims, args.brittles, cleaners=(0, args.max_cleaners), seed=args.seed)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
        print("written %s: %d tests" % (args.out, args.tests))
        return 0

    suite = ModelSuite.load(args.suite) if args.suite else PytestSuite(args.pytest, args.python)
    print("suite %s: %d tests, strategy %s" % (suite.name, len(suite.tests), args.strategy), file=sys.stderr)
    result = analyze(suite, args.strategy, args.orders, args.seed, args.exhaustive,
                     print_trace if args.trace else None)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    ok = True
    if args.expected:
        print("compare with", args.expected)
        ok &= check_expected(result, args.expected)
    if args.ipflakies:
        print("compare with", args.ipflakies)
        ok &= check_ipflakies(result, args.ipflakies, args.project or suite.name)
    if args.expected or args.ipflakies:
        print("RESULT:", "MATCH" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
