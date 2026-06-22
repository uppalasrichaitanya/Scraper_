import hashlib
import re

_TITLE_ALIASES = {
    "sr": "senior",
    "jr": "junior",
    "swe": "software engineer",
    "sde": "software engineer",
    "dev": "developer",
    "mgr": "manager",
    "eng": "engineer",
}


def compute_canonical_id(title: str, company_name: str, city: str) -> str:
    """Compute a stable SHA-256 fingerprint for deduplication across sources."""
    normalized = _normalize(title) + "|" + _normalize(company_name) + "|" + _normalize(city)
    return hashlib.sha256(normalized.encode()).hexdigest()


def _normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\.", "", s)   # strip periods — handles "Sr." "Jr." "Dr."
    s = re.sub(r"[^\w\s]", "", s)  # strip remaining punctuation
    s = re.sub(r"\s+", " ", s)  # collapse whitespace
    # Title alias normalisation — must apply after lowercasing
    for variant, canonical in _TITLE_ALIASES.items():
        s = re.sub(rf"\b{re.escape(variant)}\b", canonical, s)
    return s
