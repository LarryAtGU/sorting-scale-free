#!/usr/bin/env python3
"""Generate the ten manuscript figures as publication-sized vector PDFs."""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/scn-matplotlib-cache")
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import LogFormatterMathtext

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/results"
TEMPORAL = RESULTS / "temporal-mechanism-v1"
PAPER = ROOT.parent / "over-leaf"
OUT = PAPER / "figures"

SUMMARY = list(csv.DictReader((RESULTS / "batch-paper-final-19-algorithms-summary.csv").open()))
VALIDATION = json.loads((RESULTS / "paper-final-statistical-validation.json").read_text())
ANALYSIS = json.loads((RESULTS / "paper-secondary-analysis.json").read_text())
SCIENTIFIC = json.loads((RESULTS / "paper-theory-validation.json").read_text())

BLUE, GREEN, PURPLE, ORANGE, RED, GREY = "#1769aa", "#2e7d32", "#8e24aa", "#ef6c00", "#c62828", "#546e7a"
FAMILY_COLORS = {"pivot": BLUE, "tree": GREEN, "merge": PURPLE, "network": ORANGE, "other": GREY}


def configure() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 8.5,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#344054",
        "grid.color": "#e4e7ec",
        "grid.linewidth": 0.6,
        "pdf.fonttype": 42,
    })


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", format="pdf", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)


def expected_bst_degree_counts(n: int) -> list[float]:
    cumulative = [0.0] * n
    current = [0.0] * n
    for size in range(1, n + 1):
        current = [0.0] * n
        current[size - 1] = 1.0
        for degree in range(1, size):
            current[degree] += 2 * cumulative[degree - 1] / size
        for degree in range(size):
            cumulative[degree] += current[degree]
    return current


def ccdf(values: list[float]) -> list[float]:
    total = sum(values)
    remaining = 0.0
    output = [0.0] * len(values)
    for degree in range(len(values) - 1, -1, -1):
        remaining += values[degree]
        output[degree] = remaining / total
    return output


def exact_bst() -> None:
    row = next(r for r in SUMMARY if r["algorithm"] == "tree-unbalanced" and int(r["n"]) == 4096)
    histogram = {int(k): int(v) for k, v in json.loads(row["aggregate_degree_histogram"]).items()}
    empirical = [float(histogram.get(k, 0)) for k in range(4096)]
    expected = expected_bst_degree_counts(4096)
    empirical_tail, expected_tail = ccdf(empirical), ccdf(expected)
    degrees = list(range(1, 4096))
    fig, (ax, residual) = plt.subplots(2, 1, figsize=(7.0, 4.4), gridspec_kw={"height_ratios": [3.2, 1], "hspace": 0.10}, sharex=True)
    ax.loglog(degrees, expected_tail[1:], color=RED, lw=1.7, label="Exact expectation")
    ax.loglog(degrees, empirical_tail[1:], color=BLUE, lw=0.9, label="Instrumented executions")
    ax.set_ylabel("CCDF")
    ax.set_ylim(1e-6, 1.1)
    ax.grid(axis="y")
    ax.legend(frameon=False)
    residual.plot(degrees, [(e - x) * 1e4 for e, x in zip(empirical_tail[1:], expected_tail[1:])], color=BLUE, lw=0.8)
    residual.axhline(0, color="#344054", lw=0.7)
    residual.set_xscale("log")
    residual.set_ylabel(r"CCDF diff. ($\times 10^{-4}$)")
    residual.set_xlabel(r"Total degree $k$")
    residual.grid(axis="y")
    for axis in (ax, residual):
        axis.xaxis.set_major_formatter(LogFormatterMathtext())
    save(fig, "exact-bst-ccdf")


def temporal_values(targets: list[float]) -> dict[tuple[str, float], float]:
    best = {}
    with (TEMPORAL / "snapshots.csv").open() as stream:
        for row in csv.DictReader(stream):
            if int(row["n"]) != 1024:
                continue
            progress = float(row["progress_fraction"])
            for target in targets:
                key = row["algorithm"], int(row["seed"]), target
                distance = abs(math.log(max(progress, 1e-9)) - math.log(target))
                if key not in best or distance < best[key][0]:
                    best[key] = distance, float(row["degree_gini"])
    grouped = defaultdict(list)
    for (algorithm, _, target), (_, value) in best.items():
        grouped[algorithm, target].append(value)
    return {key: sum(values) / len(values) for key, values in grouped.items()}


def temporal_concentration() -> None:
    targets = [0.2, 0.3, 0.5, 0.7, 1.0]
    values = temporal_values(targets)
    series = [("quick", "Quicksort", BLUE), ("tree-unbalanced", "Unbalanced BST", GREEN), ("merge-top-down", "Top-down Merge", PURPLE), ("heap", "Heap", ORANGE), ("bitonic-network", "Bitonic Network", RED)]
    fig, ax = plt.subplots(figsize=(7.0, 3.1))
    for algorithm, label, color in series:
        ax.plot([100*x for x in targets], [values[algorithm, x] for x in targets], marker="o", ms=3.5, lw=1.4, color=color, label=label)
    ax.set(xlabel="Fraction of comparisons completed (%)", ylabel="Degree Gini", xlim=(20, 100), ylim=(0, 1))
    ax.grid(axis="y")
    ax.legend(frameon=False, ncol=2)
    save(fig, "temporal-concentration")


def temporal_summary() -> list[dict[str, str]]:
    return [row for row in csv.DictReader((TEMPORAL / "summary.csv").open()) if int(row["n"]) == 1024]


def representative_exposure() -> None:
    rows = [r for r in temporal_summary() if float(r["representative_comparison_fraction_mean"]) > 0]
    style = {
        "binary-insertion": ("Binary insertion", GREY, "o"), "quick": ("Quick", BLUE, "o"),
        "quick-dual-pivot": ("Dual pivot", "#5e35b1", "s"), "quick-multipivot-1": ("Multi-1", "#00838f", "^"),
        "quick-multipivot-2": ("Multi-2", "#d81b60", "D"), "quick-multipivot-4": ("Multi-4", "#6a1b9a", "v"),
        "tree-avl": ("AVL", "#7cb342", "P"), "tree-unbalanced": ("BST", GREEN, "X"),
    }
    fig, ax = plt.subplots(figsize=(7.0, 3.1))
    for row in rows:
        label, color, marker = style[row["algorithm"]]
        ax.scatter(float(row["representative_exposure_gini_mean"]), float(row["degree_gini_mean"]), s=34, color=color, marker=marker, label=label, edgecolor="white", linewidth=0.4)
    ax.set(xlabel="Representative-exposure Gini", ylabel="Degree Gini", xlim=(0.55, 0.90), ylim=(0.24, 0.46))
    ax.set_xticks([0.55, 0.65, 0.75, 0.85, 0.90])
    ax.grid(axis="y")
    ax.legend(frameon=False, ncol=4, loc="upper left")
    save(fig, "representative-exposure")


def attachment_kernel() -> None:
    selected = [("quick", "Quicksort", BLUE), ("tree-unbalanced", "Unbalanced BST", GREEN), ("merge-top-down", "Top-down Merge", PURPLE), ("bitonic-network", "Bitonic Network", RED)]
    cells = defaultdict(list)
    with (TEMPORAL / "attachment-kernel.csv").open() as stream:
        for row in csv.DictReader(stream):
            if int(row["n"]) == 1024:
                cells[row["algorithm"]].append((int(row["current_strength"]), int(row["endpoint_selections"]), int(row["node_event_opportunities"])))
    fig, ax = plt.subplots(figsize=(7.0, 3.1))
    for algorithm, label, color in selected:
        buckets = defaultdict(lambda: [0, 0])
        for strength, selections, opportunities in cells[algorithm]:
            if strength >= 1:
                bucket = int(math.log2(strength)); buckets[bucket][0] += selections; buckets[bucket][1] += opportunities
        points = [(2 ** (b + 0.5), s / o) for b, (s, o) in sorted(buckets.items()) if o >= 1000 and s]
        ax.loglog([p[0] for p in points], [p[1] for p in points], lw=1.4, color=color, label=label)
    ax.set(xlabel="Current event strength", ylabel="Global endpoint-exposure rate", ylim=(1e-5, 1))
    ax.grid(axis="y")
    ax.legend(frameon=False)
    save(fig, "attachment-kernel")


def multipivot() -> None:
    all_rows = list(csv.DictReader((TEMPORAL / "summary.csv").open()))
    series = [("quick-multipivot-1", "1 pivot", BLUE), ("quick-multipivot-2", "2 pivots", "#00838f"), ("quick-multipivot-4", "4 pivots", "#6a1b9a")]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
    for ax, field, ylabel in zip(axes, ["degree_gini_mean", "degree_p80_fraction_mean"], ["Degree Gini", r"$P_{80}$ fraction"]):
        for algorithm, label, color in series:
            rows = sorted((r for r in all_rows if r["algorithm"] == algorithm), key=lambda r: int(r["n"]))
            ax.plot([int(r["n"]) for r in rows], [float(r[field]) for r in rows], marker="o", ms=3.5, lw=1.4, color=color, label=label)
        ax.set(xlabel=r"Input size $n$", ylabel=ylabel)
        ax.set_xticks([128, 256, 512, 1024])
        ax.grid(axis="y")
    axes[0].legend(frameon=False)
    fig.tight_layout(w_pad=2.2)
    save(fig, "multipivot-intervention")


def correlation_by_size() -> None:
    rows = VALIDATION["correlation_by_n"]
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    ax.plot([r["n"] for r in rows], [r["spearman"] for r in rows], marker="o", ms=4, lw=1.4, color=BLUE)
    for r in rows:
        ax.annotate(f'{r["spearman"]:.3f}', (r["n"], r["spearman"]), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7)
    ax.set_xscale("log", base=2)
    ax.set_xticks([128, 256, 512, 1024, 2048, 4096], labels=["128", "256", "512", "1024", "2048", "4096"])
    ax.set(xlabel=r"Input size $n$", ylabel="Spearman correlation", ylim=(0.65, 0.85))
    ax.grid(axis="y")
    save(fig, "correlation-by-size")


def resource_decomposition() -> None:
    correlations = ANALYSIS["resource_decomposition_by_n"][-1]["correlations"]
    labels, keys = ["Comparisons $c$", "Movements $w$", "Storage $s$", "$c+w$", "$c+s$", "$w+s$", "$c+w+s$"], ["c", "w", "s", "c+w", "c+s", "w+s", "c+w+s"]
    values = [correlations[k] for k in keys]
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    colors = [RED if value < 0 else (BLUE if key == "c+w+s" else GREY) for key, value in zip(keys, values)]
    ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.48)
    ax.axvline(0, color="#344054", lw=0.8)
    for index, value in enumerate(values[::-1]):
        ax.text(value + (0.015 if value >= 0 else -0.015), index, f"{value:.3f}", va="center", ha="left" if value >= 0 else "right", fontsize=7.5, fontweight="bold")
    ax.set(xlabel="Spearman correlation with PL-Exp mean LLR", xlim=(-0.45, 0.85))
    ax.grid(axis="x")
    save(fig, "resource-decomposition")


def family(name: str) -> str:
    if name in {"introsort", "quick", "quick-dual-pivot", "quick-median-three", "quick-random"}: return "pivot"
    if name.startswith("tree-"): return "tree"
    if name.startswith("merge-") or name == "tournament": return "merge"
    if "network" in name: return "network"
    return "other"


def efficiency_scatter() -> None:
    tail = {r["algorithm"]: r for r in VALIDATION["tail_validation"]}
    data = [(r["algorithm"], float(r["combined_efficiency_equal_weights_mean"]), tail[r["algorithm"]]["power_vs_exponential_llr_per_observation"]) for r in SUMMARY if int(r["n"]) == 4096]
    labels = {"binary-insertion":"Binary ins.", "bitonic-network":"Bitonic/Odd-even", "bubble":"Bubble/Insertion", "heap":"Heap", "merge-insertion":"Merge ins.", "quick":"Quick", "quick-dual-pivot":"Quick dual", "quick-median-three":"Quick median", "quick-random":"Quick deterministic", "introsort":"Introsort", "selection":"Selection", "shell":"Shell", "tournament":"Tournament/Merge", "tree-avl":"AVL", "tree-unbalanced":"BST"}
    annotate = set(labels)
    offsets = {"introsort":(5,-10), "quick-random":(5,-13), "heap":(5,5), "shell":(5,-9), "selection":(5,5), "bubble":(5,5), "merge-insertion":(5,7), "bitonic-network":(5,-10)}
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    used = set()
    for name, x, y in data:
        group = family(name)
        ax.scatter(x, y, s=28, color=FAMILY_COLORS[group], edgecolor="white", linewidth=0.4, label=group if group not in used else None)
        used.add(group)
        if name in annotate:
            dx, dy = offsets.get(name, (5, 5))
            ax.annotate(labels[name], (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=6.5, color=FAMILY_COLORS[group])
    ax.set(xlabel=r"Combined efficiency $\eta$ (higher is better)", ylabel="PL-Exp mean log-likelihood difference", xlim=(-0.005, 0.275), ylim=(-0.06, 0.49))
    ax.grid(axis="y")
    handles, legend_labels = ax.get_legend_handles_labels()
    display = {"pivot":"Pivot", "tree":"Tree", "merge":"Merge/tournament", "network":"Sorting network", "other":"Other"}
    ax.legend(handles, [display[x] for x in legend_labels], frameon=False, ncol=2, loc="center right")
    save(fig, "efficiency-llr-scatter")


def block_correlations() -> None:
    rows = ANALYSIS["block_design"]["correlations"]
    values = [r["spearman"] for r in rows]
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    ax.plot(range(1, 21), values, marker="o", ms=3.5, lw=1.1, color=BLUE)
    ax.set(xlabel="Seed block", ylabel="Spearman correlation", xlim=(1, 20), ylim=(0.68, 0.82))
    ax.set_xticks(range(1, 21))
    ax.grid(axis="y")
    save(fig, "block-correlations")


def finite_size_alpha() -> None:
    names = {"quick":("Historical Hoare Quick", BLUE, "o"), "tree-unbalanced":("Unbalanced BST", GREEN, "s"), "tree-avl":("AVL tree", ORANGE, "^")}
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    for name, (label, color, marker) in names.items():
        rows = sorted((r for r in ANALYSIS["finite_size_diagnostics"] if r["algorithm"] == name), key=lambda r: r["n"])
        ax.plot([r["n"] for r in rows], [r["alpha"] for r in rows], color=color, marker=marker, ms=4, lw=1.3, label=label)
    exact = SCIENTIFIC["exact_bst_tail_fits"]
    ax.plot([r["n"] for r in exact], [r["alpha"] for r in exact], color="#111827", marker="D", ms=3.5, lw=1.1, label="Exact BST fit")
    ax.set_xscale("log", base=2)
    ax.set_xticks([128, 256, 512, 1024, 2048, 4096], labels=["128", "256", "512", "1024", "2048", "4096"])
    ax.set(xlabel=r"Input size $n$", ylabel=r"Fitted $\hat{\alpha}$", ylim=(2.0, 2.7))
    ax.grid(axis="y")
    ax.legend(frameon=False, ncol=2)
    save(fig, "finite-size-alpha")


def main() -> None:
    configure()
    OUT.mkdir(exist_ok=True)
    exact_bst(); temporal_concentration(); representative_exposure(); attachment_kernel(); multipivot()
    correlation_by_size(); resource_decomposition(); efficiency_scatter(); block_correlations(); finite_size_alpha()
    print("wrote ten vector PDF figures")


if __name__ == "__main__":
    main()
