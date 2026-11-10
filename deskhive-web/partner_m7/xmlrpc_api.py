"""Lab 1 — Complete the XML-RPC partner availability functions."""
from bookings.services import is_available
from spaces.models import Space
from bookings.intervals import local_interval
from deskhive_core.booking import validate_booking
from datetime import datetime
from django.core.exceptions import ValidationError


def _parse_interval(start_iso: str, end_iso: str) -> tuple[datetime, datetime]:
    """Parse two offset-aware ISO-8601 strings and validate the interval.

    Reuses the existing DeskHive rules (local_interval + validate_booking).
    Every invalid input is reported as ValueError (an XML-RPC Fault).
    """
    try:
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso)
    except (TypeError, ValueError) as exc:
        raise ValueError('start and end must be ISO-8601 datetime strings') from exc
    if start.utcoffset() is None or end.utcoffset() is None:
        raise ValueError('start and end must include a UTC offset')
    try:
        validate_booking(*local_interval(start, end))
    except ValidationError as exc:  # raised by local_interval (clock change)
        raise ValueError('; '.join(exc.messages)) from exc
    # InvalidBookingError from validate_booking is already a ValueError.
    return start, end


def list_available_spaces(start_iso: str, end_iso: str) -> list[dict]:
    """Return available spaces as XML-RPC-safe dictionaries.

    Output fields: code, name, city, kind, hourly_rate (decimal as str).
    Dates must be offset-aware ISO-8601 strings; validate using the existing
    DeskHive interval rules. No writes. Invalid input raises ValueError.
    """
    start, end = _parse_interval(start_iso, end_iso)
    spaces = Space.objects.select_related('location').order_by('code')
    return [
        {
            'code': space.code,
            'name': space.name,
            'city': space.location.city,
            'kind': space.kind,
            'hourly_rate': str(space.hourly_rate),  # Decimal is not XML-RPC-safe
        }
        for space in spaces
        if is_available(space, start, end)  # existing overlap rule, whole interval
    ]

def get_space_availability(code: str, start_iso: str, end_iso: str) -> bool:
    """Return availability for an existing Space.code and interval.

    Unknown codes / invalid date ranges raise ValueError.
    """
    # TODO M7-LAB1: find the space by code and reuse availability rules.
    raise NotImplementedError('M7 Lab 1: get_space_availability')
