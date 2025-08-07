"""Utilities for generating simple trend plots."""
from __future__ import annotations

from pathlib import Path

import pandas as pd  # type: ignore

try:  # pragma: no cover - optional dependency
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # type: ignore


def line_plot(data: pd.DataFrame, output_path: Path) -> Path:
    """Render a line plot of ``data`` and store it at ``output_path``."""
    if plt is None:
        raise RuntimeError("matplotlib is required for plotting")
    ax = data.plot(kind="line")
    fig = ax.get_figure()
    fig.savefig(str(output_path))
    return output_path


__all__ = ["line_plot"]
