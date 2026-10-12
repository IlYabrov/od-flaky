"""Графики для отчёта и презентации из results/*.csv (нужен matplotlib).

Запуск:  python experiments/plots.py   ->  results/fig_*.pdf и results/fig_*.png
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "results"
TUSCAN, RANDOM, THEORY = "#2a78d6", "#eb6834", "#52514e"  # одинаковые цвета стратегий на всех графиках
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                     "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
                     "lines.linewidth": 2, "legend.frameon": False})


def read(name):
    with open(OUT / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / ("%s.%s" % (name, ext)), dpi=200)
    plt.close(fig)
    print("saved results/%s.pdf" % name)


def pair_coverage(n=100):
    rows = [r for r in read("e2_pair_coverage.csv") if int(r["n"]) == n]
    k = [int(r["k"]) for r in rows]
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.plot(k, [100 * float(r["tuscan"]) for r in rows], color=TUSCAN, label="тосканские порядки")
    ax.plot(k, [100 * float(r["random_theory"]) for r in rows], color=THEORY, linestyle="--", linewidth=1.2,
            label=r"теория $1-(1-1/n)^k$")
    ax.plot(k, [100 * float(r["random"]) for r in rows], "o", color=RANDOM, markersize=4, label="случайные порядки")
    ax.axvline(n, color=THEORY, linewidth=0.8, linestyle=":")
    ax.set(xlabel="число порядков $k$", ylabel="покрыто пар соседей, %", ylim=(0, 102))
    ax.legend(loc="lower right")
    save(fig, "fig_pair_coverage")


def detection_curve(n=100):
    rows = read("e3_curve_n100.csv")
    fig, ax = plt.subplots(figsize=(6, 3.4))
    for strategy, color, label in [("tuscan", TUSCAN, "тосканские порядки"), ("random", RANDOM, "случайные порядки")]:
        sel = [r for r in rows if r["strategy"] == strategy]
        ax.step([int(r["k"]) for r in sel], [100 * float(r["found"]) for r in sel], where="post", color=color,
                label=label)
    ax.axvline(n, color=THEORY, linewidth=0.8, linestyle=":")
    ax.set(xlabel="число порядков $k$ (кроме исходного)", ylabel="найдено OD-тестов, %", ylim=(0, 102))
    ax.legend(loc="lower right")
    save(fig, "fig_detection_n100")


def probability():
    synth, real = read("e1_probability.csv"), read("e4_real_probability.csv")
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    ax.plot([0, 0.55], [0, 0.55], color=THEORY, linestyle="--", linewidth=1.2, label="эмпирика = теория")
    ax.plot([float(r["theory"]) for r in synth], [float(r["empirical"]) for r in synth], "o", color=TUSCAN,
            markersize=6, label="модель, 5000 порядков")
    ax.plot([float(r["theory"]) for r in real], [float(r["empirical"]) for r in real], "s", color=RANDOM,
            markersize=7, label="IOCynergy, GOApy, 300 порядков")
    ax.set(xlabel="теоретическая вероятность падения", ylabel="наблюдаемая доля падений", xlim=(0, 0.55),
           ylim=(0, 0.55))
    ax.legend(loc="upper left", fontsize=8)
    save(fig, "fig_probability")


def orders_for_all():
    rows = read("e3_scaling.csv")
    fig, ax = plt.subplots(figsize=(6, 3.4))
    for strategy, color, label in [("tuscan", TUSCAN, "тосканские порядки"), ("random", RANDOM, "случайные порядки")]:
        sel = [r for r in rows if r["strategy"] == strategy]
        ax.plot([int(r["n"]) for r in sel], [float(r["orders_for_all"]) for r in sel], "o-", color=color,
                markersize=5, label=label)
    ns = sorted({int(r["n"]) for r in rows})
    ax.plot(ns, ns, color=THEORY, linestyle="--", linewidth=1.2, label="$k = n$")
    ax.set(xscale="log", yscale="log", xlabel="число тестов $n$", ylabel="порядков до обнаружения всех")
    ax.legend(loc="upper left")
    save(fig, "fig_orders_for_all")


if __name__ == "__main__":
    pair_coverage()
    detection_curve()
    probability()
    orders_for_all()
