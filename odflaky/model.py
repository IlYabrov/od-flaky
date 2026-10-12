"""Модельный (синтетический) набор тестов, заданный в JSON.

Исход каждого теста определяется только порядком запуска (модель Wei et al., 2021):
  victim  v проходит в изоляции и падает, если ближайший предшествующий ему тест из
          polluters(v) U cleaners(v) является polluter'ом;
  brittle b падает в изоляции и проходит, если до него запускался хотя бы один setter;
  остальные тесты всегда проходят.

Формат файла:
{
  "name": "...",
  "tests": ["t1", "t2", ...],                                   # исходный порядок
  "victims":  {"t1": {"polluters": ["t4"], "cleaners": ["t2"]}},
  "brittles": {"t3": {"setters": ["t2"]}}
}
"""
import json
import random
from collections import defaultdict


class ModelSuite:
    def __init__(self, data):
        self.name = data.get("name", "model")
        self.tests = list(data["tests"])
        self.victims = data.get("victims", {})
        self.brittles = data.get("brittles", {})
        # effects[t] - как тест t меняет общее состояние: (действие, затронутый тест)
        self.effects = defaultdict(list)
        for v, spec in self.victims.items():
            for p in spec["polluters"]:
                self.effects[p].append(("pollute", v))
            for c in spec.get("cleaners", []):
                self.effects[c].append(("clean", v))
        for b, spec in self.brittles.items():
            for s in spec["setters"]:
                self.effects[s].append(("set", b))

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def run(self, order):
        """Выполнить тесты в заданном порядке «с чистого листа»; вернуть {тест: pass|fail}."""
        dirty, ready, result = set(), set(), {}
        for t in order:
            if t in self.victims:
                result[t] = "fail" if t in dirty else "pass"
            elif t in self.brittles:
                result[t] = "pass" if t in ready else "fail"
            else:
                result[t] = "pass"
            for action, target in self.effects.get(t, ()):
                if action == "pollute":
                    dirty.add(target)
                elif action == "clean":
                    dirty.discard(target)
                else:
                    ready.add(target)
        return result


def generate(n, victims=3, brittles=2, polluters=(1, 3), cleaners=(0, 10), setters=(1, 3), seed=0):
    """Случайный модельный набор из n тестов (входные данные переменного объёма)."""
    rnd = random.Random(seed)
    tests = ["t%03d" % i for i in range(n)]
    od = rnd.sample(tests, victims + brittles)

    def pick(pool, bounds):
        return sorted(rnd.sample(pool, min(len(pool), rnd.randint(*bounds))))

    data = {"name": "synthetic-n%d-s%d" % (n, seed), "tests": tests, "victims": {}, "brittles": {}}
    for v in od[:victims]:
        ps = pick([t for t in tests if t not in od], polluters)
        cs = pick([t for t in tests if t not in od and t not in ps], cleaners)
        data["victims"][v] = {"polluters": ps, "cleaners": cs}
    for b in od[victims:]:
        data["brittles"][b] = {"setters": pick([t for t in tests if t not in od], setters)}
    return data
