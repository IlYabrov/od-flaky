"""Подготовка бенчмарка: клонирует проекты из набора данных iPFlakies на зафиксированных
коммитах в bench/repos и применяет патчи совместимости из bench/projects.json."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

for project in json.loads((HERE / "projects.json").read_text(encoding="utf-8")):
    repo = HERE / "repos" / project["name"]
    if not repo.exists():
        subprocess.run(["git", "clone", "-q", project["url"], str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", "-f", project["commit"]], check=True)
    for patch in project["patches"]:
        path = repo / patch["file"]
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        if patch["old"] in text:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text.replace(patch["old"], patch["new"]))
        print("  patched %s: %s" % (patch["file"], patch["why"]))
    print("%s ready at %s (%s)" % (project["name"], repo, project["commit"][:10]))
