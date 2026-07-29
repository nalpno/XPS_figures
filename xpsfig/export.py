"""Figure export helpers (raster + vector, journal resolutions)."""

from __future__ import annotations

import io
import zipfile

from matplotlib.figure import Figure

FORMATS = {
    "PNG": {"ext": "png", "vector": False, "mime": "image/png"},
    "TIFF": {"ext": "tiff", "vector": False, "mime": "image/tiff"},
    "PDF": {"ext": "pdf", "vector": True, "mime": "application/pdf"},
    "SVG": {"ext": "svg", "vector": True, "mime": "image/svg+xml"},
    "EPS": {"ext": "eps", "vector": True, "mime": "application/postscript"},
}

DPI_CHOICES = [150, 300, 600, 1200]


def figure_bytes(fig: Figure, fmt: str = "PNG", dpi: int = 300,
                 transparent: bool = False) -> bytes:
    """Serialise *fig*; TIFF is written with LZW compression as journals ask."""
    info = FORMATS[fmt]
    buffer = io.BytesIO()
    kwargs = {
        "format": info["ext"],
        "dpi": dpi,
        "bbox_inches": "tight",
        "pad_inches": 0.05,
        "transparent": transparent,
    }
    if fmt == "TIFF":
        kwargs["pil_kwargs"] = {"compression": "tiff_lzw"}
    fig.savefig(buffer, **kwargs)
    return buffer.getvalue()


def bundle(fig: Figure, basename: str, formats: list[str], dpis: list[int],
           transparent: bool = False) -> bytes:
    """Zip every requested format/resolution combination in one archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fmt in formats:
            info = FORMATS[fmt]
            if info["vector"]:
                zf.writestr(f"{basename}.{info['ext']}",
                            figure_bytes(fig, fmt, 300, transparent))
            else:
                for dpi in dpis:
                    zf.writestr(f"{basename}_{dpi}dpi.{info['ext']}",
                                figure_bytes(fig, fmt, dpi, transparent))
    return buffer.getvalue()


def suggest_filename(base: str, fmt: str, dpi: int | None = None) -> str:
    info = FORMATS[fmt]
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in base).strip("_") or "figure"
    if info["vector"] or dpi is None:
        return f"{safe}.{info['ext']}"
    return f"{safe}_{dpi}dpi.{info['ext']}"
