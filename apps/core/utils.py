"""Fast, pandas-native Excel ingestion helpers shared by every bulk-upload view.

Uses pandas with the `calamine` engine (a Rust-based reader via the
python-calamine package) instead of openpyxl for reading, since it is
significantly faster on large workbooks (files with 500k+ rows are an
expected use case for this app's Sales Data uploads). All row-level
cleaning (whitespace stripping, blank-row removal) is done as vectorized
pandas operations rather than a Python loop, and the resulting DataFrame
is handed to callers in fixed-size chunks so database writes can be
batched - see apps.core.mixins.ExcelUploadView.
"""
import logging

import pandas as pd

logger = logging.getLogger("apps.core.utils")


class ExcelParseError(Exception):
    """Raised when an uploaded workbook cannot be parsed at all."""


def load_excel(file_obj):
    """Reads the first sheet of the uploaded workbook into a header-less
    DataFrame (every cell as data, no assumptions about where headers are).
    """
    try:
        return pd.read_excel(file_obj, header=None, engine="calamine")
    except Exception as exc:  # noqa: BLE001 - surface any parse failure uniformly
        logger.exception("Failed to read uploaded workbook")
        raise ExcelParseError(f"Could not read the uploaded file: {exc}") from exc


def extract_pre_header_text(df, header_row):
    """Returns every non-empty cell value (stringified) from rows 1..header_row-1,
    across all columns, from an already-loaded DataFrame (see `load_excel`).

    Useful for pulling metadata (report titles, period banners, notes) that
    sits above the real header row of an uploaded spreadsheet.
    """
    if header_row <= 1:
        return []
    texts = []
    for _, row in df.iloc[: header_row - 1].iterrows():
        for value in row:
            if pd.notna(value) and str(value).strip() != "":
                texts.append(str(value))
    return texts


def build_data_frame(df, header_row=1, start_col=1):
    """Slices the raw header-less DataFrame (from `load_excel`) into a
    properly-headered, cleaned data DataFrame:

    - `header_row`: 1-indexed row number containing the column headers.
      Data is assumed to start on the very next row.
    - `start_col`: 1-indexed column number where headers/data begin
      (1 = column A). Any columns before this are ignored entirely.

    Column names are normalised to lowercase, stripped strings. String
    cell values are stripped of surrounding whitespace and fully-blank
    rows are dropped - all as vectorized pandas operations. The returned
    DataFrame's index holds each row's original 1-indexed Excel row
    number, so error messages can still point back to the source file.
    """
    header_idx = header_row - 1
    col_idx = start_col - 1

    if header_idx >= len(df) or col_idx >= df.shape[1]:
        raise ExcelParseError(f"Header row {header_row} was not found in the uploaded file.")

    header_values = df.iloc[header_idx, col_idx:]
    headers = [str(h).strip().lower().replace(" ", "_") if pd.notna(h) else "" for h in header_values]
    if not any(headers):
        raise ExcelParseError(f"Header row {header_row} appears to be empty. Check the Header Row setting.")

    data = df.iloc[header_idx + 1 :, col_idx:].copy()
    data.columns = headers
    data.index = range(header_row + 1, header_row + 1 + len(data))

    # Strip whitespace on every object (string-ish) column - vectorized.
    for col in data.columns:
        if data[col].dtype == object:
            data[col] = data[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    # Drop rows that are entirely blank (all NaN or all empty strings).
    blank_mask = data.apply(lambda row: all(pd.isna(v) or v == "" for v in row), axis=1)
    data = data[~blank_mask]

    return data


def chunk_dataframe(df, chunk_size):
    """Yields successive `chunk_size`-row slices of the DataFrame, preserving
    the original Excel-row-number index on each slice.
    """
    for start in range(0, len(df), chunk_size):
        yield df.iloc[start : start + chunk_size]
