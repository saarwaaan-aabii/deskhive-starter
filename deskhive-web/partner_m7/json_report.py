"""Lab 2 — Export actual monthly DeskHive booking usage as JSON text."""
import json
import re
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from bookings.models import Booking

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
    start, end = _month_bounds(month)
    # Real bookings whose *start* falls in the month (read-only query).
    bookings = (Booking.objects
                .filter(start__gte=start, start__lt=end)
                .select_related('space__location'))
    rows = {}
    for booking in bookings:
        row = rows.setdefault(booking.space.code, {
            'code': booking.space.code,
            'city': booking.space.location.city,
            'bookings': 0,
            'seconds': 0,
        })
        row['bookings'] += 1
        row['seconds'] += int((booking.end - booking.start).total_seconds())
    spaces = [
        {
            'code': row['code'],
            'city': row['city'],
            'bookings': row['bookings'],
            # Decimal avoids float rounding; string keeps it JSON-safe.
            'hours': str((Decimal(row['seconds']) / 3600).quantize(Decimal('0.01'))),
        }
        for row in sorted(rows.values(), key=lambda r: r['code'])
    ]
    report = {
        'month': month,
        'total_bookings': sum(row['bookings'] for row in spaces),
        'spaces': spaces,
    }
    return json.dumps(report)
