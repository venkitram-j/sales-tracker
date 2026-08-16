"""Parses the reporting-period banner that sits above the real header row
of a Sales Data upload spreadsheet, in the format:

    Report Period From :- 01-09-2025,  To :- 30-09-2025

This line may be split across several adjacent cells on the same row due
to source-file formatting quirks - see
apps.core.utils.extract_pre_header_row_texts, which joins each row's
cells into one string before this pattern is matched, so a split banner
still matches correctly.
"""
import re
from datetime import datetime

REPORT_PERIOD_PATTERN = re.compile(
    r"Report\s+Period\s+From\s*:-\s*(\d{1,2}-\d{1,2}-\d{4})\s*,?\s*To\s*:-\s*(\d{1,2}-\d{1,2}-\d{4})",
    re.IGNORECASE,
)

DATE_INPUT_FORMAT = "%d-%m-%Y"


def parse_report_period(texts):
    """Given a list of strings (one per pre-header row - see
    `extract_pre_header_row_texts`), find and parse the report period banner.

    Returns (start_date, end_date) as `datetime.date` objects, or
    (None, None) if no matching banner was found.
    """
    for text in texts:
        match = REPORT_PERIOD_PATTERN.search(text)
        if match:
            start_str, end_str = match.groups()
            try:
                start_date = datetime.strptime(start_str, DATE_INPUT_FORMAT).date()
                end_date = datetime.strptime(end_str, DATE_INPUT_FORMAT).date()
            except ValueError:
                continue
            return start_date, end_date
    return None, None
