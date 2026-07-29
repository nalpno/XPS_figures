"""Publication style: rcParams, colour palettes and font handling."""

from __future__ import annotations

import matplotlib
import matplotlib.font_manager as fm
from matplotlib import rcParams

# Fonts requested most often by materials journals, in fallback order.
FONT_STACKS: dict[str, list[str]] = {
    "Arial": ["Arial", "Helvetica", "Liberation Sans", "Nimbus Sans", "DejaVu Sans"],
    "Helvetica": ["Helvetica", "Arial", "Nimbus Sans", "DejaVu Sans"],
    "Times New Roman": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "Calibri": ["Calibri", "Carlito", "Arial", "DejaVu Sans"],
    "DejaVu Sans": ["DejaVu Sans"],
}

# Line colours taken from the reference OriginPro figures.
LINE_PALETTES: dict[str, list[str]] = {
    "Origin (siyah-kırmızı-mavi-yeşil-mor)": [
        "#3F3F3F", "#E8262A", "#2B5FCB", "#2FA84F", "#A97BD9",
        "#F09B2B", "#00A0A6", "#C2185B", "#6D4C41", "#455A64",
    ],
    "Yüksek kontrast": [
        "#000000", "#D62728", "#1F77B4", "#2CA02C", "#9467BD",
        "#FF7F0E", "#17BECF", "#E377C2", "#8C564B", "#7F7F7F",
    ],
    "Renk körü dostu (Okabe-Ito)": [
        "#000000", "#D55E00", "#0072B2", "#009E73", "#CC79A7",
        "#E69F00", "#56B4E9", "#F0E442", "#666666", "#994F00",
    ],
    "Gri tonlama (baskı)": [
        "#000000", "#3D3D3D", "#666666", "#8C8C8C", "#B0B0B0",
        "#1A1A1A", "#4F4F4F", "#757575", "#9E9E9E", "#C4C4C4",
    ],
    "Viridis": [
        "#440154", "#472D7B", "#3B528B", "#2C728E", "#21908C",
        "#27AD81", "#5DC863", "#AADC32", "#FDE725", "#B5DE2B",
    ],
}

# Pastel fills used for deconvoluted components (matches the reference fits).
FILL_PALETTES: dict[str, list[str]] = {
    "Pastel (Avantage benzeri)": [
        "#B39DDB", "#F48FB1", "#9FC5F8", "#80DEEA", "#CFD8DC",
        "#EF9A9A", "#C5E1A5", "#FFCC80", "#CE93D8", "#A5D6A7",
    ],
    "Canlı": [
        "#8E7CC3", "#E06666", "#6FA8DC", "#76A5AF", "#93C47D",
        "#F6B26B", "#C27BA0", "#A2C4C9", "#B4A7D6", "#D5A6BD",
    ],
    "Soğuk": [
        "#7FB3D5", "#A9CCE3", "#5499C7", "#48C9B0", "#76D7C4",
        "#85C1E9", "#2E86C1", "#1ABC9C", "#AED6F1", "#D4E6F1",
    ],
    "Sıcak": [
        "#F5B7B1", "#F1948A", "#E59866", "#F8C471", "#F7DC6F",
        "#EDBB99", "#E6B0AA", "#FAD7A0", "#F9E79F", "#D98880",
    ],
}

DEFAULT_LINE_PALETTE = "Origin (siyah-kırmızı-mavi-yeşil-mor)"
DEFAULT_FILL_PALETTE = "Pastel (Avantage benzeri)"

BACKGROUND_COLOR = "#D62728"   # red background line, as in the reference figures
ENVELOPE_COLOR = "#000000"     # black envelope
RESIDUAL_COLOR = "#7F7F7F"


def available_fonts() -> list[str]:
    """Font stacks whose first choice is actually installed, plus the rest."""
    installed = {f.name for f in fm.fontManager.ttflist}
    ordered = [name for name in FONT_STACKS if name in installed]
    ordered += [name for name in FONT_STACKS if name not in installed]
    return ordered


def font_is_installed(name: str) -> bool:
    return name in {f.name for f in fm.fontManager.ttflist}


def apply_style(
    font: str = "Arial",
    base_size: float = 9.0,
    line_width: float = 1.2,
    axes_width: float = 1.2,
    tick_length: float = 4.0,
    tick_direction: str = "in",
) -> None:
    """Set a journal-ready global matplotlib style."""
    matplotlib.use("Agg", force=False)
    stack = FONT_STACKS.get(font, FONT_STACKS["Arial"])
    serif = "Times" in font or "Serif" in font

    rcParams.update({
        "font.family": "serif" if serif else "sans-serif",
        ("font.serif" if serif else "font.sans-serif"): stack,
        "font.size": base_size,
        "axes.titlesize": base_size,
        "axes.labelsize": base_size + 1,
        "xtick.labelsize": base_size,
        "ytick.labelsize": base_size,
        "legend.fontsize": base_size - 0.5,
        "mathtext.fontset": "custom",
        "mathtext.rm": stack[0],
        "mathtext.it": f"{stack[0]}:italic",
        "mathtext.bf": f"{stack[0]}:bold",

        "axes.linewidth": axes_width,
        "axes.edgecolor": "black",
        "axes.labelcolor": "black",
        "axes.facecolor": "white",
        "axes.grid": False,
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.unicode_minus": False,

        "lines.linewidth": line_width,
        "lines.solid_capstyle": "round",
        "lines.antialiased": True,

        "xtick.direction": tick_direction,
        "ytick.direction": tick_direction,
        "xtick.major.size": tick_length,
        "ytick.major.size": tick_length,
        "xtick.minor.size": tick_length * 0.55,
        "ytick.minor.size": tick_length * 0.55,
        "xtick.major.width": axes_width,
        "ytick.major.width": axes_width,
        "xtick.minor.width": axes_width * 0.8,
        "ytick.minor.width": axes_width * 0.8,
        "xtick.top": True,
        "ytick.right": True,
        "xtick.color": "black",
        "ytick.color": "black",

        "legend.frameon": True,
        "legend.framealpha": 1.0,
        "legend.edgecolor": "black",
        "legend.fancybox": False,
        "legend.borderpad": 0.4,
        "legend.handlelength": 1.8,
        "legend.labelspacing": 0.3,

        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,

        "pdf.fonttype": 42,   # embed TrueType so editors keep the text editable
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })


def line_colors(palette: str, n: int) -> list[str]:
    colors = LINE_PALETTES.get(palette, LINE_PALETTES[DEFAULT_LINE_PALETTE])
    return [colors[i % len(colors)] for i in range(n)]


def fill_colors(palette: str, n: int) -> list[str]:
    colors = FILL_PALETTES.get(palette, FILL_PALETTES[DEFAULT_FILL_PALETTE])
    return [colors[i % len(colors)] for i in range(n)]
