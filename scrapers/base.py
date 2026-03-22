import re
from config import VALID_AREAS, EXCLUDED_AREAS, MAX_HOURS

_SAFE_EMAIL = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def is_valid_location(location_text):
    """Check if a job location is within Jamal's travel range."""
    if not location_text:
        return False
    loc = location_text.lower()
    for excluded in EXCLUDED_AREAS:
        if excluded in loc:
            return False
    # Check postcodes - G1-G4, G11, G12, G20 are close enough
    # Match Glasgow postcodes (G1, G2, etc.) but not DG1, EG1 etc.
    postcode_match = re.search(r'(?<![a-z])g(\d+)', loc)
    if postcode_match:
        district = int(postcode_match.group(1))
        # G1-G4 = city centre, G5 = Gorbals, G11 = Partick/Thornwood,
        # G12 = Hillhead/Kelvinside, G20 = North Kelvin, G31 = Dennistoun
        # G41 = Shawlands/Pollokshields (borderline but reachable)
        # G51 = Govan/Ibrox (reachable by subway)
        if district in (1, 2, 3, 4, 5, 11, 12, 20, 31, 41, 51):
            return True
        return False

    for valid in VALID_AREAS:
        # Use word-boundary-aware matching for short postcode prefixes
        if re.search(r'(?<![a-z])' + re.escape(valid) + r'(?![a-z])', loc):
            return True
    return False


def is_valid_hours(hours_text, description_text=""):
    """Check if job hours fit within 16 per week. Returns (valid, note)."""
    text = f"{hours_text or ''} {description_text or ''}".lower()

    # Explicit part-time markers
    if "part-time" in text or "part time" in text:
        return True, None

    # Look for specific hour counts
    hour_matches = re.findall(r'(\d+)\s*(?:hours?|hrs?)\s*(?:per|a|/)\s*week', text)
    for h in hour_matches:
        if int(h) <= MAX_HOURS:
            return True, None
        elif int(h) <= 24:
            return True, f"Listed as {h} hours/week - slightly over 16, worth checking"

    # Full-time with part-time mention
    if "full-time" in text or "full time" in text:
        if "part-time" in text or "part time" in text or "flexible" in text:
            return True, "Listed as full-time but mentions part-time/flexible. Worth a look."
        return False, None

    # If hours aren't specified, include it (many kitchen jobs don't specify)
    if not hour_matches:
        return True, "Hours not specified - may need to confirm 16hrs/week is possible"

    return False, None


def is_safe_email(addr):
    """Validate an email address is safe to send to."""
    if not addr:
        return False
    return bool(_SAFE_EMAIL.match(addr)) and '\n' not in addr and '\r' not in addr


def extract_email(text):
    """Extract employer email from job description if present."""
    if not text:
        return None
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    # Filter out common non-employer emails
    for email in emails:
        lower = email.lower()
        if not any(skip in lower for skip in [
            'indeed', 'reed', 'totaljobs', 'caterer', 'cvlibrary',
            's1jobs', 'noreply', 'no-reply', 'example.com'
        ]):
            if is_safe_email(email):
                return email
    return None


def is_relevant_role(title):
    """Check if a job title is relevant to kitchen/hospitality."""
    title_lower = title.lower()
    relevant_terms = [
        "kitchen", "chef", "cook", "porter", "dishwash",
        "catering", "hospitality", "food", "restaurant",
        "waiter", "waitress", "waiting", "front of house",
        "barista", "cafe", "café", "canteen", "dining",
        "breakfast", "sous", "commis", "prep",
    ]
    return any(term in title_lower for term in relevant_terms)
