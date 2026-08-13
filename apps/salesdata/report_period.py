"""Parses metadata that sits above the real header row of a Sales Data
upload spreadsheet - specifically the reporting period and the branch
name, neither of which are per-row columns.

Reporting period format (as previously confirmed):

    Report Period From :- 01-09-2025,  To :- 30-09-2025

Branch name format: since a sample file confirming the exact wording
hasn't been reviewed yet, this uses a flexible pattern - any line
starting with "Branch" followed by ":" and/or "-" and the branch name,
e.g. "Branch :- Downtown", "Branch Name: Downtown", "Branch - Downtown".
If the real file uses a different format, update BRANCH_LINE_PATTERN
below to match it exactly.
"""
import re
from datetime import datetime

REPORT_PERIOD_PATTERN = re.compile(
    r"Report\s+Period\s+From\s*:-\s*(\d{1,2}-\d{1,2}-\d{4})\s*,?\s*To\s*:-\s*(\d{1,2}-\d{1,2}-\d{4})",
    re.IGNORECASE,
)

BRANCH_LINE_PATTERN = re.compile(
    r"^\s*Branch\s*(?:Name)?\s*[:\-]+\s*(.+?)\s*$",
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


def parse_branch_name(texts):
    """Given a list of strings (cell values), find and parse the branch-name
    banner line. Returns the branch name (stripped), or None if not found.
    """
    for text in texts:
        match = BRANCH_LINE_PATTERN.match(text)
        if match:
            name = match.group(1).strip()
            if name:
                return name
    return None
