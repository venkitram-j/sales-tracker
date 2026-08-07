"""Parses the "Report Period" banner line that some source spreadsheets
place above their real header row, e.g.:

    Report Period From :- 01-09-2025,  To :- 30-09-2025

This is intentionally decoupled from the generic Excel utilities in
apps.core.utils since the exact banner text/format is specific to the
Sales Data upload.
"""
import re
from datetime import datetime

REPORT_PERIOD_PATTERN = re.compile(
    r"Report\s+Period\s+From\s*:-\s*(\d{1,2}-\d{1,2}-\d{4})\s*,?\s*To\s*:-\s*(\d{1,2}-\d{1,2}-\d{4})",
    re.IGNORECASE,
)

DATE_INPUT_FORMAT = "%d-%m-%Y"


def parse_report_period(texts):
    """Given a list of strings (cell values), find and parse the report period banner.

    Returns (start_date, end_date) as `datetime.date` objects, or
    (None, None) if no matching banner was found in any of the strings.
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
