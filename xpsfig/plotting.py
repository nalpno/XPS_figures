"""Figure construction for XPS survey, core-level and deconvolution plots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from matplotlib.transforms import offset_copy

from . import style as st

CM = 1 / 2.54

NORMALIZATIONS = {
    "Yok (ham şiddet)": "none",
    "Maksimum = 1": "max",
    "Min-Maks (0-1)": "minmax",
    "Alan = 1": "area",
}


# ---------------------------------------------------------------------------
# specs
# ---------------------------------------------------------------------------
@dataclass
class Curve:
    """A single line in a stacked / overlaid panel."""

    x: np.ndarray
    y: np.ndarray
    label: str = ""
    color: str = "#000000"
    linewidth: float = 1.2
    linestyle: str = "-"
    visible: bool = True


@dataclass
class DeconCurves:
    """Everything needed to draw one deconvoluted region."""

    x: np.ndarray
    raw: np.ndarray | None = None
    components: list[tuple[str, np.ndarray, str]] = field(default_factory=list)
    background: np.ndarray | None = None
    envelope: np.ndarray | None = None
    residual: np.ndarray | None = None
    sample_label: str = ""
    label_loc: str = "lower left"


@dataclass
class Panel:
    kind: str = "stack"                       # "stack" | "decon"
    curves: list[Curve] = field(default_factory=list)
    decon: DeconCurves | None = None

    letter: str = ""                          # "a", "b", ...
    inner_label: str = ""                     # "Zn2p", "O1s", ...
    xlabel: str = "Binding Energy (eV)"
    ylabel: str = "Intensity (a.u.)"
    xlim: tuple[float, float] | None = None   # given as (high, low) after reversal
    xtick_step: float | None = None
    show_ytick_labels: bool = False
    ypad_top: float = 0.08
    legend_mode: str = "none"                 # "none" | "inside" | "outside"
    legend_loc: str = "upper right"
    legend_ncol: int = 1
    label_mode: str = "legend"                # stack: "legend" | "inline" | "none"
    inline_label_x: float = 0.03              # axes fraction
    annotations: list[dict[str, Any]] = field(default_factory=list)
    grid: tuple[int, int, int, int] | None = None   # (row, col, rowspan, colspan)


@dataclass
class FigureSpec:
    panels: list[Panel] = field(default_factory=list)
    nrows: int = 1
    ncols: int = 1
    width_cm: float = 17.0
    height_cm: float = 12.0
    letter_template: str = "{letter})"
    letter_pos: tuple[float, float] = (0.03, 0.95)
    letter_weight: str = "normal"
    letter_size: float | None = None
    letter_outside: bool = False
    shared_legend: bool = False
    shared_legend_ncol: int = 5
    shared_legend_entries: list[tuple[str, str]] = field(default_factory=list)
    shared_legend_y: float = -0.02
    wspace: float = 0.28
    hspace: float = 0.35
    tight: bool = True


# ---------------------------------------------------------------------------
# maths helpers
# ---------------------------------------------------------------------------
def normalize(y: np.ndarray, mode: str) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if mode == "none" or np.all(np.isnan(y)):
        return y
    ymin, ymax = np.nanmin(y), np.nanmax(y)
    if mode == "max":
        return y / ymax if ymax not in (0, np.nan) else y
    if mode == "minmax":
        span = ymax - ymin
        return (y - ymin) / span if span else y - ymin
    if mode == "area":
        area = np.nansum(np.abs(y))
        return y / area if area else y
    return y


def stack_offsets(curves: Sequence[np.ndarray], offset_fraction: float) -> list[float]:
    """Constant vertical spacing based on the largest curve span."""
    spans = []
    for y in curves:
        if y is None or np.all(np.isnan(y)):
            continue
        spans.append(float(np.nanmax(y) - np.nanmin(y)))
    step = (max(spans) if spans else 1.0) * offset_fraction
    return [i * step for i in range(len(curves))]


def _autoscale_x(panel: Panel) -> tuple[float, float] | None:
    xs = []
    if panel.kind == "decon" and panel.decon is not None:
        xs.append(panel.decon.x)
    for c in panel.curves:
        if c.visible:
            xs.append(c.x)
    if not xs:
        return None
    lo = min(float(np.nanmin(x)) for x in xs)
    hi = max(float(np.nanmax(x)) for x in xs)
    return (hi, lo)          # reversed: binding energy decreases to the right


# ---------------------------------------------------------------------------
# panel drawing
# ---------------------------------------------------------------------------
def _finish_axes(ax, panel: Panel, letter_template: str, letter_pos, letter_weight,
                 letter_size, letter_outside: bool = False) -> None:
    if panel.xtick_step:
        ax.xaxis.set_major_locator(MultipleLocator(panel.xtick_step))
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))

    ax.set_xlabel(panel.xlabel)
    ax.set_ylabel(panel.ylabel)
    if not panel.show_ytick_labels:
        ax.set_yticks([])
    else:
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    for spine in ax.spines.values():
        spine.set_visible(True)

    if panel.letter:
        text = letter_template.format(letter=panel.letter)
        if letter_outside:
            ax.text(-0.02, 1.03, text, transform=ax.transAxes, ha="right", va="bottom",
                    fontweight=letter_weight, fontsize=letter_size)
        else:
            ax.text(letter_pos[0], letter_pos[1], text, transform=ax.transAxes,
                    ha="left", va="top", fontweight=letter_weight, fontsize=letter_size)
    if panel.inner_label:
        # offset in points, not axes fraction, so narrow panels do not collide
        transform = ax.transAxes
        if panel.letter and not letter_outside:
            transform = offset_copy(transform, fig=ax.figure, x=22, units="points")
        ax.text(
            letter_pos[0], letter_pos[1], panel.inner_label,
            transform=transform, ha="left", va="top",
        )

    for ann in panel.annotations:
        text = ann.get("text", "")
        if not text:
            continue
        x, y = ann.get("x"), ann.get("y", 0.9)
        coords = ann.get("coords", "data-axes")
        xy_text = (x, y)
        if ann.get("arrow") and ann.get("target_x") is not None:
            ax.annotate(
                text,
                xy=(ann["target_x"], ann.get("target_y", y - 0.1)),
                xytext=xy_text,
                xycoords=("data", "axes fraction") if coords == "data-axes" else "data",
                textcoords=("data", "axes fraction") if coords == "data-axes" else "data",
                ha=ann.get("ha", "center"), va="bottom",
                arrowprops=dict(arrowstyle="-", lw=0.8, color="black"),
            )
        else:
            ax.text(
                x, y, text,
                transform=ax.get_xaxis_transform() if coords == "data-axes" else ax.transData,
                ha=ann.get("ha", "center"), va="bottom",
            )


def draw_stack_panel(ax, panel: Panel, offsets: Sequence[float] | None = None) -> None:
    visible = [c for c in panel.curves if c.visible]
    offsets = list(offsets) if offsets is not None else [0.0] * len(visible)
    left, right = ax.get_xlim()

    ymins, ymaxs = [], []
    for curve, off in zip(visible, offsets):
        y = curve.y + off
        ax.plot(
            curve.x, y,
            color=curve.color, lw=curve.linewidth, ls=curve.linestyle,
            label=curve.label or "_nolegend_", solid_joinstyle="round",
        )
        if not np.all(np.isnan(y)):
            ymins.append(np.nanmin(y))
            ymaxs.append(np.nanmax(y))

        if panel.label_mode == "inline" and curve.label and y.size:
            # anchor the label to the curve just inside the left-hand edge
            anchor = left + (right - left) * (panel.inline_label_x + 0.02)
            idx = int(np.nanargmin(np.abs(curve.x - anchor)))
            y_at = y[idx] if not np.isnan(y[idx]) else np.nanmax(y)
            span = (np.nanmax(y) - np.nanmin(y)) or 1.0
            ax.text(
                panel.inline_label_x, y_at + span * 0.06, curve.label,
                transform=ax.get_yaxis_transform(), ha="left", va="bottom",
                color="black",
            )

    if ymins:
        lo, hi = min(ymins), max(ymaxs)
        pad = (hi - lo) * panel.ypad_top
        ax.set_ylim(lo - pad * 0.5, hi + pad)


def draw_decon_panel(ax, panel: Panel, *, fill_alpha: float = 0.55,
                     raw_marker_size: float = 12, show_residual: bool = False,
                     line_widths: dict[str, float] | None = None) -> None:
    d = panel.decon
    if d is None:
        return
    lw = {"component": 0.8, "background": 1.0, "envelope": 1.1, "raw": 0.6}
    lw.update(line_widths or {})

    ymins, ymaxs = [], []

    def track(y):
        if y is not None and not np.all(np.isnan(y)):
            ymins.append(np.nanmin(y))
            ymaxs.append(np.nanmax(y))

    baseline = d.background if d.background is not None else np.zeros_like(d.x)

    for name, y, color in d.components:
        ok = ~np.isnan(y)
        ax.fill_between(
            d.x, np.where(ok, y, np.nan), np.where(ok, baseline, np.nan),
            facecolor=color, alpha=fill_alpha, linewidth=0, label=name, zorder=2,
        )
        ax.plot(d.x, y, color=color, lw=lw["component"], zorder=2.5)
        track(y)

    if d.raw is not None:
        ax.plot(
            d.x, d.raw, ls="none", marker="o", ms=np.sqrt(raw_marker_size),
            mfc="none", mec="black", mew=0.55, label="Raw Data", zorder=4,
        )
        track(d.raw)
    if d.background is not None:
        ax.plot(d.x, d.background, color=st.BACKGROUND_COLOR, lw=lw["background"],
                label="Backgnd.", zorder=3)
        track(d.background)
    if d.envelope is not None:
        ax.plot(d.x, d.envelope, color=st.ENVELOPE_COLOR, lw=lw["envelope"],
                label="Envelope", zorder=3.5)
        track(d.envelope)
    if show_residual and d.residual is not None:
        top = max(ymaxs) if ymaxs else 1.0
        span = (top - min(ymins)) if ymins else 1.0
        ax.plot(d.x, d.residual + top + span * 0.08, color=st.RESIDUAL_COLOR,
                lw=0.7, label="Residuals", zorder=3)
        track(d.residual + top + span * 0.08)

    if ymins:
        lo, hi = min(ymins), max(ymaxs)
        pad = (hi - lo) * panel.ypad_top
        ax.set_ylim(lo - pad * 0.6, hi + pad)

    if d.sample_label:
        positions = {
            "lower left": (0.03, 0.05, "left", "bottom"),
            "lower right": (0.97, 0.05, "right", "bottom"),
            "upper left": (0.03, 0.95, "left", "top"),
            "upper right": (0.97, 0.95, "right", "top"),
        }
        x, y, ha, va = positions.get(d.label_loc, positions["lower left"])
        ax.text(
            x, y, d.sample_label, transform=ax.transAxes, ha=ha, va=va, zorder=6,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.5),
        )


def _add_legend(ax, panel: Panel, show_residual: bool = False) -> None:
    if panel.kind == "decon" and panel.decon is not None:
        # keep the journal ordering: raw data, components, background, envelope
        h2, l2 = decon_legend_handles(panel.decon, show_residual)
    else:
        handles, labels = ax.get_legend_handles_labels()
        seen, h2, l2 = set(), [], []
        for h, l in zip(handles, labels):
            if l and not l.startswith("_") and l not in seen:
                seen.add(l)
                h2.append(h)
                l2.append(l)
    if not h2:
        return
    if panel.legend_mode == "inside":
        ax.legend(h2, l2, loc=panel.legend_loc, ncol=panel.legend_ncol)
    elif panel.legend_mode == "outside":
        ax.legend(h2, l2, loc="upper left", bbox_to_anchor=(1.02, 1.0),
                  ncol=panel.legend_ncol, borderaxespad=0)


# ---------------------------------------------------------------------------
# figure assembly
# ---------------------------------------------------------------------------
def render_figure(spec: FigureSpec, *, decon_options: dict[str, Any] | None = None,
                  stack_offsets_map: dict[int, list[float]] | None = None) -> Figure:
    fig = Figure(figsize=(spec.width_cm * CM, spec.height_cm * CM))
    gs = fig.add_gridspec(spec.nrows, spec.ncols)
    axes = []

    for i, panel in enumerate(spec.panels):
        if panel.grid:
            row, col, rowspan, colspan = panel.grid
        else:
            row, col, rowspan, colspan = divmod(i, spec.ncols) + (1, 1)
        row = min(row, spec.nrows - 1)
        col = min(col, spec.ncols - 1)
        rowspan = max(1, min(rowspan, spec.nrows - row))
        colspan = max(1, min(colspan, spec.ncols - col))
        ax = fig.add_subplot(gs[row:row + rowspan, col:col + colspan])
        axes.append(ax)

        xlim = panel.xlim or _autoscale_x(panel)
        if xlim:
            ax.set_xlim(xlim)

        if panel.kind == "decon":
            draw_decon_panel(ax, panel, **(decon_options or {}))
        else:
            offsets = (stack_offsets_map or {}).get(i)
            draw_stack_panel(ax, panel, offsets)

        _finish_axes(
            ax, panel, spec.letter_template, spec.letter_pos,
            spec.letter_weight, spec.letter_size, spec.letter_outside,
        )
        if panel.legend_mode != "none":
            _add_legend(ax, panel, bool((decon_options or {}).get("show_residual")))

    if spec.tight:
        fig.tight_layout()
    fig.subplots_adjust(wspace=spec.wspace, hspace=spec.hspace)

    if spec.shared_legend and spec.shared_legend_entries:
        handles = [Line2D([0], [0], color=color, lw=1.6) for _, color in spec.shared_legend_entries]
        labels = [label for label, _ in spec.shared_legend_entries]
        fig.legend(
            handles, labels, loc="upper center",
            bbox_to_anchor=(0.5, spec.shared_legend_y),
            ncol=spec.shared_legend_ncol, frameon=True, edgecolor="black",
            fancybox=False, borderaxespad=0,
        )

    return fig


def decon_legend_handles(d: DeconCurves, show_residual: bool = False):
    """Handles in the order used by the reference figures."""
    handles = [Line2D([0], [0], ls="none", marker="o", mfc="none", mec="black", mew=0.6, ms=4)]
    labels = ["Raw Data"]
    for name, _, color in d.components:
        handles.append(Patch(facecolor=color, alpha=0.55, edgecolor=color))
        labels.append(name)
    if d.background is not None:
        handles.append(Line2D([0], [0], color=st.BACKGROUND_COLOR, lw=1.2))
        labels.append("Backgnd.")
    if d.envelope is not None:
        handles.append(Line2D([0], [0], color=st.ENVELOPE_COLOR, lw=1.2))
        labels.append("Envelope")
    if show_residual and d.residual is not None:
        handles.append(Line2D([0], [0], color=st.RESIDUAL_COLOR, lw=1.0))
        labels.append("Residuals")
    return handles, labels
