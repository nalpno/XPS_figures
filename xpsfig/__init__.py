"""XPS Figure Studio - Avantage .xlsx to publication-ready figures and tables."""

from .parser import (
    BACKGROUND,
    COMPONENT,
    ENVELOPE,
    RAW,
    RESIDUAL,
    Dataset,
    PeakRow,
    Region,
    Series,
    load_workbook_dataset,
    merge_datasets,
)

__all__ = [
    "Dataset", "Region", "Series", "PeakRow",
    "load_workbook_dataset", "merge_datasets",
    "RAW", "BACKGROUND", "ENVELOPE", "RESIDUAL", "COMPONENT",
]

__version__ = "1.0.0"
