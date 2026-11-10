"""Lab 2 — Export actual monthly DeskHive booking usage as JSON text."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

REPORT_ZONE = ZoneInfo('Europe/Paris')
_MONTH_FORMAT = re.compile(r'[0-9]{4}-[0-9]{2}')  # ASCII digits only


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    """Return [first instant, first instant of next month) in Europe/Paris.

    Accepts exactly YYYY-MM with a real calendar month; otherwise ValueError.
    """
    if not isinstance(month, str) or not _MONTH_FORMAT.fullmatch(month):
        raise ValueError('month must use the YYYY-MM format')
    year, number = int(month[:4]), int(month[5:])
    if not 1 <= number <= 12:
        raise ValueError(f'month must be between 01 and 12, got {month[5:]}')
    start = datetime(year, number, 1, tzinfo=REPORT_ZONE)
    end = datetime(year + number // 12, number % 12 + 1, 1, tzinfo=REPORT_ZONE)
    return start, end


def export_usage_report(month: str) -> str:
    """Return a JSON string for YYYY-MM in Europe/Paris timezone.

    Shape: {month, total_bookings, spaces: [{code, city, bookings, hours}]}
    Include only spaces with bookings starting in the requested month.
    Hours are decimal strings with 2 fractional digits. Sort rows by code.
    No database writes; invalid month raises ValueError.
    """
    # TODO M7-LAB2: query bookings, aggregate hours and serialize with json.
    raise NotImplementedError('M7 Lab 2: export_usage_report')
