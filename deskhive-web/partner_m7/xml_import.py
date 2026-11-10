"""Lab 2 — Parse a trusted local corporate-contact XML file into Member."""
import re
import xml.etree.ElementTree as ET

from django.core.exceptions import ValidationError
from django.db import transaction

from bookings.models import Member

# DTDs can declare entities (external files, "billion laughs" expansion).
# The contract never needs them, so any declaration is refused up front.
_FORBIDDEN_DECLARATIONS = re.compile(rb'<!\s*(DOCTYPE|ENTITY)', re.IGNORECASE)
_CONTACT_FIELDS = ('full_name', 'email')


def _parse_contacts(xml_bytes: bytes) -> list[dict]:
    """Parse the XML contract into raw {'full_name', 'email'} dictionaries.

    Only the documented shape is accepted:
    <corporate_contacts><contact><full_name/><email/></contact>...</corporate_contacts>
    Every problem raises ValueError; nothing is written here.
    """
    if not isinstance(xml_bytes, (bytes, bytearray)):
        raise ValueError('XML input must be bytes')
    if _FORBIDDEN_DECLARATIONS.search(xml_bytes):
        raise ValueError('DTD and entity declarations are not allowed')
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f'Malformed XML: {exc}') from exc

    if root.tag != 'corporate_contacts':
        raise ValueError('Root element must be <corporate_contacts>')
    contacts = []
    for position, contact in enumerate(root, start=1):
        if contact.tag != 'contact':
            raise ValueError(f'Unexpected element <{contact.tag}> at position {position}')
        tags = [child.tag for child in contact]
        if sorted(tags) != sorted(_CONTACT_FIELDS):
            raise ValueError(f'Contact {position} must contain exactly <full_name> and <email>')
        contacts.append({tag: contact.find(tag).text for tag in _CONTACT_FIELDS})
    return contacts


def _validate_contacts(raw_contacts: list[dict]) -> list[dict]:
    """Validate every contact in memory, before any database write.

    Applies the exercise rules (required values, lowercase email, no duplicate
    email in the file) and the existing Member field constraints. Collects all
    problems and raises one ValueError if any contact is invalid.
    """
    errors, cleaned, seen = [], [], set()
    for position, raw in enumerate(raw_contacts, start=1):
        full_name = (raw['full_name'] or '').strip()
        email = (raw['email'] or '').strip().lower()
        if not full_name or not email:
            errors.append(f'Contact {position}: full_name and email are required')
            continue
        if email in seen:
            errors.append(f'Contact {position}: duplicate email {email} in this file')
            continue
        seen.add(email)
        try:
            # Existing model rules (max_length, email format). Uniqueness against
            # stored members is not an error: existing members are skipped later.
            Member(full_name=full_name, email=email).full_clean(validate_unique=False)
        except ValidationError as exc:
            errors.append(f'Contact {position}: {exc.messages}')
            continue
        cleaned.append({'full_name': full_name, 'email': email})
    if errors:
        raise ValueError('Invalid contacts: ' + '; '.join(errors))
    return cleaned


def import_corporate_contacts(xml_bytes: bytes) -> int:
    """Import contacts; return number of newly created Members.

    XML format: <corporate_contacts><contact><full_name>...</full_name>
    <email>...</email></contact>...</corporate_contacts>.
    Normalize email to lowercase. Existing emails are not duplicated.
    Reject bad XML, missing/invalid fields and duplicate emails in one file;
    do not partially import an invalid document. No schema/model migration.
    This classroom lab accepts small, locally trusted XML inputs only.
    """
    contacts = _validate_contacts(_parse_contacts(xml_bytes))  # no write before this
    existing = set(Member.objects.filter(email__in=[c['email'] for c in contacts])
                   .values_list('email', flat=True))
    created = 0
    with transaction.atomic():  # all new members are saved, or none
        for contact in contacts:
            if contact['email'] in existing:
                continue  # existing members are left unchanged, never duplicated
            Member.objects.create(**contact)
            created += 1
    return created
