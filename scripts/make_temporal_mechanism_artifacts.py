#!/usr/bin/env python3
"""Create manuscript figures and tables for the frozen mechanism experiment."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/results/temporal-mechanism-v1"
PAPER = ROOT.parent / "over-leaf"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
COLORS = {
    "quick": "#1769aa",
    "quick-dual-pivot": "#1976d2",
    "tree-unbalanced": "#2e7d32",
    "tree-avl": "#43a047",
    "merge-top-down": "#8e24aa",
    "binary-insertion": "#546e7a",
    "heap": "#ef6c00",
    "bitonic-network": "#c62828",
    "quick-multipivot-1": "#1565c0",
    "quick-multipivot-2": "#00838f",
    "quick-multipivot-4": "#6a1b9a",
}


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def canvas(title: str, subtitle: str):
    image = Image.new("RGB", (1800, 1100), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 35), title, fill="#172033", font=font(38, True))
    draw.text((80, 87), subtitle, fill="#667085", font=font(22))
    return image, draw


def line_axes(draw, box, *, x_ticks, y_ticks, xlabel: str, ylabel: str):
    left, top, right, bottom = box
    draw.line((left, bottom, right, bottom), fill="#344054", width=3)
    draw.line((left, top, left, bottom), fill="#344054", width=3)
    for label, position in x_ticks:
        x = left + position * (right - left)
        draw.line((x, bottom, x, bottom + 8), fill="#344054", width=2)
        width = draw.textlength(label, font=font(19))
        draw.text((x - width / 2, bottom + 12), label, fill="#344054", font=font(19))
    for label, position in y_ticks:
        y = bottom - position * (bottom - top)
        draw.line((left, y, right, y), fill="#e4e7ec", width=2)
        width = draw.textlength(label, font=font(19))
        draw.text((left - width - 14, y - 11), label, fill="#344054", font=font(19))
    draw.text(((left + right) / 2 - 80, bottom + 58), xlabel, fill="#172033", font=font(23))
    draw.text((left, top - 38), ylabel, fill="#172033", font=font(23))


def read_summary():
    with (RESULTS / "summary.csv").open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def closest_temporal_points(targets: list[float]):
    best: dict[tuple[str, int, float], tuple[float, dict[str, str]]] = {}
    with (RESULTS / "snapshots.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if int(row["n"]) != 1024:
                continue
            progress = float(row["progress_fraction"])
            for target in targets:
                key = (row["algorithm"], int(row["seed"]), target)
                distance = abs(math.log(max(progress, 1e-9)) - math.log(target))
                if key not in best or distance < best[key][0]:
                    best[key] = (distance, row)
    grouped: dict[tuple[str, float], list[float]] = defaultdict(list)
    for (algorithm, _, target), (_, row) in best.items():
        grouped[algorithm, target].append(float(row["degree_gini"]))
    return {key: sum(values) / len(values) for key, values in grouped.items()}


def temporal_figure() -> None:
    targets = [0.2, 0.3, 0.5, 0.7, 1.0]
    values = closest_temporal_points(targets)
    selected = ["quick", "tree-unbalanced", "merge-top-down", "heap", "bitonic-network"]
    labels = {
        "quick": "Quicksort",
        "tree-unbalanced": "Unbalanced BST",
        "merge-top-down": "Top-down merge",
        "heap": "Heap",
        "bitonic-network": "Bitonic network",
    }
    image, draw = canvas(
        "Late-stage degree concentration during sorting",
        "Mean over 200 matched permutations at n = 1024; first 20% omitted",
    )
    box = (190, 165, 1690, 920)
    line_axes(
        draw,
        box,
        x_ticks=[(f"{int(100 * x)}%", (x - 0.2) / 0.8) for x in targets],
        y_ticks=[(f"{x:.1f}", x) for x in (0, 0.2, 0.4, 0.6, 0.8, 1.0)],
        xlabel="Fraction of comparisons completed",
        ylabel="Degree Gini",
    )
    for index, algorithm in enumerate(selected):
        points = []
        for target in targets:
            x = box[0] + (target - 0.2) / 0.8 * (box[2] - box[0])
            y = box[3] - values[algorithm, target] * (box[3] - box[1])
            points.append((x, y))
        draw.line(points, fill=COLORS[algorithm], width=6)
        for x, y in points:
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=COLORS[algorithm])
        y = 180 + index * 42
        draw.line((1160, y, 1220, y), fill=COLORS[algorithm], width=6)
        draw.text((1235, y - 14), labels[algorithm], fill=COLORS[algorithm], font=font(21, True))
    image.save(PAPER / "figures/temporal-concentration.png", dpi=(180, 180))


def mechanism_scatter() -> None:
    rows = [row for row in read_summary() if int(row["n"]) == 1024]
    selected = [row for row in rows if float(row["representative_comparison_fraction_mean"]) > 0]
    labels = {
        "binary-insertion": "Binary insertion",
        "quick": "Quick",
        "quick-dual-pivot": "Dual pivot",
        "quick-multipivot-1": "Multi-1",
        "quick-multipivot-2": "Multi-2",
        "quick-multipivot-4": "Multi-4",
        "tree-avl": "AVL",
        "tree-unbalanced": "BST",
    }
    image, draw = canvas(
        "Concentrated representative exposure predicts concentrated degree",
        "Algorithm means over 200 matched permutations at n = 1024",
    )
    box = (210, 165, 1680, 920)
    xmin, xmax, ymin, ymax = 0.55, 0.88, 0.24, 0.45
    line_axes(
        draw,
        box,
        x_ticks=[(f"{x:.2f}", (x - xmin) / (xmax - xmin)) for x in (0.55, 0.65, 0.75, 0.85)],
        y_ticks=[(f"{y:.2f}", (y - ymin) / (ymax - ymin)) for y in (0.25, 0.30, 0.35, 0.40, 0.45)],
        xlabel="Representative-exposure Gini",
        ylabel="Degree Gini",
    )
    for row in selected:
        algorithm = row["algorithm"]
        xvalue = float(row["representative_exposure_gini_mean"])
        yvalue = float(row["degree_gini_mean"])
        x = box[0] + (xvalue - xmin) / (xmax - xmin) * (box[2] - box[0])
        y = box[3] - (yvalue - ymin) / (ymax - ymin) * (box[3] - box[1])
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=COLORS[algorithm])
    for index, algorithm in enumerate(labels):
        column, row_index = divmod(index, 4)
        x, y = 650 + 310 * column, 210 + 38 * row_index
        draw.ellipse((x, y, x + 15, y + 15), fill=COLORS[algorithm])
        draw.text((x + 24, y - 5), labels[algorithm], fill=COLORS[algorithm], font=font(17, True))
    image.save(PAPER / "figures/representative-exposure.png", dpi=(180, 180))


def attachment_figure() -> None:
    selected = ["quick", "tree-unbalanced", "merge-top-down", "bitonic-network"]
    labels = {
        "quick": "Quicksort",
        "tree-unbalanced": "Unbalanced BST",
        "merge-top-down": "Top-down merge",
        "bitonic-network": "Bitonic network",
    }
    cells: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    with (RESULTS / "attachment-kernel.csv").open(encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if int(row["n"]) == 1024 and row["algorithm"] in selected:
                cells[row["algorithm"]].append(
                    (
                        int(row["current_strength"]),
                        int(row["endpoint_selections"]),
                        int(row["node_event_opportunities"]),
                    )
                )
    binned: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for algorithm, values in cells.items():
        buckets: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        for strength, selections, opportunities in values:
            if strength < 1:
                continue
            bucket = int(math.log2(strength))
            buckets[bucket][0] += selections
            buckets[bucket][1] += opportunities
        for bucket, (selections, opportunities) in sorted(buckets.items()):
            if opportunities >= 1000 and selections:
                binned[algorithm].append((2 ** (bucket + 0.5), selections / opportunities))
    image, draw = canvas(
        "Global endpoint-exposure rate",
        "Pooled descriptive rate at n = 1024; eligibility is not conditioned out",
    )
    box = (220, 165, 1680, 920)
    xmin, xmax, ymin, ymax = 0, 3.4, -5, 0
    line_axes(
        draw,
        box,
        x_ticks=[(f"10^{x}", (x - xmin) / (xmax - xmin)) for x in range(4)],
        y_ticks=[(f"10^{y}", (y - ymin) / (ymax - ymin)) for y in range(-5, 1)],
        xlabel="Current event strength (log scale)",
        ylabel="Selection rate",
    )
    for index, algorithm in enumerate(selected):
        points = []
        for strength, rate in binned[algorithm]:
            xlog, ylog = math.log10(strength), math.log10(rate)
            if xmin <= xlog <= xmax and ymin <= ylog <= ymax:
                points.append(
                    (
                        box[0] + (xlog - xmin) / (xmax - xmin) * (box[2] - box[0]),
                        box[3] - (ylog - ymin) / (ymax - ymin) * (box[3] - box[1]),
                    )
                )
        draw.line(points, fill=COLORS[algorithm], width=6)
        y = 185 + index * 42
        draw.line((1190, y, 1250, y), fill=COLORS[algorithm], width=6)
        draw.text((1265, y - 14), labels[algorithm], fill=COLORS[algorithm], font=font(21, True))
    image.save(PAPER / "figures/attachment-kernel.png", dpi=(180, 180))


def intervention_figure() -> None:
    rows = read_summary()
    selected = ["quick-multipivot-1", "quick-multipivot-2", "quick-multipivot-4"]
    labels = {
        "quick-multipivot-1": "1 pivot",
        "quick-multipivot-2": "2 pivots",
        "quick-multipivot-4": "4 pivots",
    }
    image, draw = canvas(
        "Multi-pivot intervention produces only modest dispersion",
        "Mean degree concentration over 200 matched permutations per size",
    )
    panels = [
        ((220, 190, 860, 900), "degree_gini_mean", 0.34, 0.44, "Degree Gini"),
        ((1060, 190, 1700, 900), "degree_p80_fraction_mean", 0.58, 0.63, "P80 fraction"),
    ]
    sizes = [128, 256, 512, 1024]
    for box, field, ymin, ymax, ylabel in panels:
        line_axes(
            draw,
            box,
            x_ticks=[(str(n), i / 3) for i, n in enumerate(sizes)],
            y_ticks=[
                (f"{y:.2f}", (y - ymin) / (ymax - ymin))
                for y in (
                    [0.34, 0.36, 0.38, 0.40, 0.42, 0.44]
                    if field == "degree_gini_mean"
                    else [0.58, 0.59, 0.60, 0.61, 0.62, 0.63]
                )
            ],
            xlabel="Input size n",
            ylabel=ylabel,
        )
        for index, algorithm in enumerate(selected):
            algorithm_rows = sorted(
                (r for r in rows if r["algorithm"] == algorithm), key=lambda r: int(r["n"])
            )
            points = []
            for i, row in enumerate(algorithm_rows):
                value = float(row[field])
                points.append(
                    (
                        box[0] + i / 3 * (box[2] - box[0]),
                        box[3] - (value - ymin) / (ymax - ymin) * (box[3] - box[1]),
                    )
                )
            draw.line(points, fill=COLORS[algorithm], width=6)
            for x, y in points:
                draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=COLORS[algorithm])
            if box[0] < 500:
                y = 210 + index * 40
                draw.line((550, y, 605, y), fill=COLORS[algorithm], width=6)
                draw.text(
                    (620, y - 13), labels[algorithm], fill=COLORS[algorithm], font=font(19, True)
                )
    image.save(PAPER / "figures/multipivot-intervention.png", dpi=(180, 180))


def mechanism_table() -> None:
    rows = [row for row in read_summary() if int(row["n"]) == 1024]
    order = [
        "binary-insertion",
        "bitonic-network",
        "heap",
        "merge-top-down",
        "quick",
        "quick-dual-pivot",
        "tree-avl",
        "tree-unbalanced",
        "quick-multipivot-1",
        "quick-multipivot-2",
        "quick-multipivot-4",
    ]
    labels = {
        "binary-insertion": "Binary insertion",
        "bitonic-network": "Bitonic network",
        "heap": "Heap",
        "merge-top-down": "Merge top-down",
        "quick": "Quick (Hoare)",
        "quick-dual-pivot": "Quick dual-pivot",
        "tree-avl": "AVL tree",
        "tree-unbalanced": "Unbalanced BST",
        "quick-multipivot-1": "Multi-pivot 1",
        "quick-multipivot-2": "Multi-pivot 2",
        "quick-multipivot-4": "Multi-pivot 4",
    }
    lookup = {row["algorithm"]: row for row in rows}
    lines = [
        r"\begin{table*}[tbp]",
        r"\centering",
        r"\small",
        r"\caption{Temporal-mechanism results at $n=1024$, averaged over 200 matched permutations. Smaller $P_{80}$ means greater concentration. $\bar S_R$ is mean represented span, $\bar L_R$ is mean normalized representative lifetime, and $r_{Sd}$ correlates a representative's mean span with final degree. Dashes denote algorithms for which no representative role is defined.}",
        r"\label{tab:mechanism-results}",
        r"\begin{tabular}{lrrrrrrr}",
        r"\toprule",
        r"Algorithm & $G_d$ & $P_{80}$ & $G_R$ & rep. nodes & $\bar S_R$ & $\bar L_R$ & $r_{Sd}$\\",
        r"\midrule",
    ]
    for algorithm in order:
        row = lookup[algorithm]
        prefix = f"{labels[algorithm]} & {float(row['degree_gini_mean']):.3f} & {float(row['degree_p80_fraction_mean']):.3f}"
        if float(row["representative_node_fraction_mean"]) == 0:
            lines.append(prefix + r" & --- & --- & --- & --- & ---\\")
        else:
            lines.append(
                prefix
                + f" & {float(row['representative_exposure_gini_mean']):.3f} & {100 * float(row['representative_node_fraction_mean']):.1f}\\% & {float(row['mean_represented_span_mean']):.1f} & {float(row['mean_representative_lifetime_fraction_mean']):.4f} & {float(row['mean_span_degree_correlation_mean']):.3f}"
                + r"\\"
            )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    (PAPER / "tables/mechanism-results.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    (PAPER / "figures").mkdir(exist_ok=True)
    (PAPER / "tables").mkdir(exist_ok=True)
    temporal_figure()
    mechanism_scatter()
    attachment_figure()
    intervention_figure()
    mechanism_table()
    print("wrote four mechanism figures and one table")


if __name__ == "__main__":
    main()
