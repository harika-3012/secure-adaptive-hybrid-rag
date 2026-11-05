"""Comparison charts (matplotlib, light surface). Palette: validated categorical slots 1-4 in fixed order."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from experiments.summarize import METHOD_LABELS, METHOD_ORDER  # noqa: E402

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
# blue, orange, aqua, yellow (fixed order per method; colour follows the method, never its rank)
COLORS = {"bm25": "#2a78d6", "dense": "#eb6834", "fixed_hybrid": "#1baf7a", "adaptive_hybrid": "#eda100"}
METRIC_LABELS = {"precision": "Precision@K", "recall": "Recall@K", "mrr": "MRR", "ndcg": "NDCG@K"}
TYPE_LABELS = {
    "exact_keyword": "Exact keyword",
    "identifier": "Identifier",
    "conceptual": "Conceptual",
    "paraphrased": "Paraphrased",
    "mixed": "Mixed",
}


def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _grouped(ax, groups: list[str], series: dict[str, list[float]], fmt: str) -> None:
    n = len(series)
    width = 0.8 / n
    x = np.arange(len(groups))
    for i, (method, vals) in enumerate(series.items()):
        pos = x - 0.4 + width * (i + 0.5)
        bars = ax.bar(pos, vals, width * 0.88, color=COLORS[method], label=METHOD_LABELS[method])
        for b, v in zip(bars, vals):
            if not np.isnan(v):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.012, format(v, fmt), ha="center", va="bottom",
                        fontsize=7, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, color=INK)


def make_charts(summary: dict[str, pd.DataFrame], out_dir: Path, k: int, n_answerable: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    overall, by_type = summary["overall"], summary["by_type"]
    methods = [m for m in METHOD_ORDER if m in overall.index]
    note = f"Preliminary: {n_answerable} answerable questions, synthetic corpus, K={k}"
    paths: list[Path] = []

    # 1. Overall retrieval quality
    fig, ax = plt.subplots(figsize=(9, 4.6), facecolor=SURFACE)
    _style(ax)
    metrics = list(METRIC_LABELS)
    _grouped(ax, [METRIC_LABELS[m] for m in metrics], {m: [overall.loc[m, x] for x in metrics] for m in methods}, ".2f")
    ax.set_ylim(0, 1.12)
    ax.set_title("Retrieval quality by method", loc="left", color=INK, fontsize=13)
    fig.text(0.01, 0.01, note, color=INK_2, fontsize=8)
    ax.legend(ncol=len(methods), frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), labelcolor=INK_2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    p = out_dir / "overall_metrics.png"
    fig.savefig(p, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    paths.append(p)

    # 2. MRR by query type
    types = [t for t in TYPE_LABELS if t in by_type.index.get_level_values(0)]
    if types:
        fig, ax = plt.subplots(figsize=(9, 4.6), facecolor=SURFACE)
        _style(ax)
        series = {m: [by_type.loc[(t, m), "mrr"] for t in types] for m in methods}
        _grouped(ax, [TYPE_LABELS[t] for t in types], series, ".2f")
        ax.set_ylim(0, 1.12)
        ax.set_title("Mean reciprocal rank by query type", loc="left", color=INK, fontsize=13)
        fig.text(0.01, 0.01, note + " (4 questions per type: read as indicative only)", color=INK_2, fontsize=8)
        ax.legend(ncol=len(methods), frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), labelcolor=INK_2)
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        p = out_dir / "mrr_by_query_type.png"
        fig.savefig(p, dpi=200, facecolor=SURFACE)
        plt.close(fig)
        paths.append(p)

    # 3. Latency (single measure -> single hue per method, labelled)
    fig, ax = plt.subplots(figsize=(7, 4), facecolor=SURFACE)
    _style(ax)
    vals = [overall.loc[m, "latency_mean_ms"] for m in methods]
    bars = ax.bar([METHOD_LABELS[m] for m in methods], vals, 0.55, color=[COLORS[m] for m in methods])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f} ms", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_ylabel("Mean retrieval latency (ms)", color=INK_2)
    ax.set_title("Retrieval latency by method", loc="left", color=INK, fontsize=13)
    fig.tight_layout()
    p = out_dir / "latency.png"
    fig.savefig(p, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    paths.append(p)
    return paths
