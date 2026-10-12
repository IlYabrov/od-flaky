"""Реальный набор pytest-тестов: каждый порядок исполняется в отдельном процессе Python,
поэтому глобальное состояние (модули, синглтоны, файлы в памяти) между порядками не переносится."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGE_ROOT = str(Path(__file__).resolve().parent.parent)


class PytestSuite:
    def __init__(self, project, python=sys.executable, paths=()):
        self.project = Path(project).resolve()
        self.name = self.project.name
        self.python = python
        self.paths = list(paths)
        self.tests = self._pytest(None)  # исходный порядок = порядок сбора pytest

    def run(self, order):
        return self._pytest(list(order))

    def _pytest(self, order):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp, "out.json")
            env = dict(os.environ, ODFLAKY_OUT=str(out), PYTHONDONTWRITEBYTECODE="1",
                       PYTHONPATH=os.pathsep.join(filter(None, [PACKAGE_ROOT, os.environ.get("PYTHONPATH")])))
            args = [self.python, "-m", "pytest", "-q", "--rootdir", str(self.project),
                    "-p", "odflaky.pytest_plugin", "-p", "no:cacheprovider", "-p", "no:randomly"]
            if order is None:
                args += ["--collect-only"] + self.paths
            else:
                Path(tmp, "order.json").write_text(json.dumps(order), encoding="utf-8")
                env["ODFLAKY_ORDER"] = str(Path(tmp, "order.json"))
                args += sorted({t.split("::")[0] for t in order})  # файлы, содержащие нужные тесты
            proc = subprocess.run(args, cwd=self.project, env=env, capture_output=True,
                                  encoding="utf-8", errors="replace")
            # 0 - все прошли, 1 - есть падения; иное (ошибки сбора, внутренние ошибки) - отказ запуска
            if proc.returncode not in (0, 1) or not out.exists():
                raise RuntimeError("pytest failed (exit %d):\n%s\n%s" % (proc.returncode, proc.stdout[-3000:], proc.stderr[-3000:]))
            return json.loads(out.read_text(encoding="utf-8"))
