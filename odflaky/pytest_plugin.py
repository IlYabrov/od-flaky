"""Плагин pytest, подключаемый через `-p odflaky.pytest_plugin`.

Без переменной ODFLAKY_ORDER плагин записывает в ODFLAKY_OUT список собранных тестов
(исходный порядок). С ODFLAKY_ORDER (JSON-список node id) - оставляет только эти
тесты, выполняет их строго в заданном порядке и записывает {node id: pass|fail|skip}.
"""
import json
import os

_results = {}


def _dump(obj):
    with open(os.environ["ODFLAKY_OUT"], "w", encoding="utf-8") as f:
        json.dump(obj, f)


def pytest_collection_modifyitems(config, items):
    path = os.environ.get("ODFLAKY_ORDER")
    if not path:
        return
    with open(path, encoding="utf-8") as f:
        position = {test: i for i, test in enumerate(json.load(f))}
    config.hook.pytest_deselected(items=[it for it in items if it.nodeid not in position])
    items[:] = sorted((it for it in items if it.nodeid in position), key=lambda it: position[it.nodeid])


def pytest_collection_finish(session):
    if not os.environ.get("ODFLAKY_ORDER"):
        _dump([it.nodeid for it in session.items])


def pytest_runtest_logreport(report):
    # Падение на любой фазе (setup / call / teardown) считается падением теста.
    if report.failed:
        _results[report.nodeid] = "fail"
    elif report.skipped:
        _results[report.nodeid] = "skip"
    else:
        _results.setdefault(report.nodeid, "pass")


def pytest_sessionfinish(session):
    if os.environ.get("ODFLAKY_ORDER"):
        _dump(_results)
