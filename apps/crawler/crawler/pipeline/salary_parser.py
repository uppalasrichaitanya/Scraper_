import re
from typing import Optional

MULTIPLIERS = {
    "lpa": 100_000,
    "lakh": 100_000,
    "lac": 100_000,
    "cr": 10_000_000,
    "crore": 10_000_000,
    "k": 1_000,
    "m": 1_000_000,
}


def parse_salary(raw: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Returns (min_inr_annual, max_inr_annual) or (None, None)."""
    if not raw:
        return None, None
    text = raw.lower().strip()

    # Detect currency — USD gets converted at ~83
    is_usd = "$" in text or "usd" in text
    multiplier = 83 if is_usd else 1

    # Handle ₹/month pattern before general number extraction
    is_monthly = bool(re.search(r"month|pm\b|p\.m\.", text))

    # Find all numbers (handles "12.5", "12,50,000")
    nums = [float(n.replace(",", "")) for n in re.findall(r"[\d,]+\.?\d*", text)]
    if not nums:
        return None, None

    # Find suffix multiplier
    unit = None
    if re.search(r"\b(lpa|lakhs?|lacs?)\b", text):
        unit = 100_000
    elif re.search(r"\b(cr|crores?)\b", text):
        unit = 10_000_000
    elif re.search(r"(?:\d|\b)m\b", text):
        unit = 1_000_000
    elif re.search(r"(?:\d|\b)k\b", text):
        unit = 1_000

    if unit is None:
        if is_monthly:
            # Monthly salary in INR — annualise
            unit = 12
        elif nums[0] < 1_000:
            # Bare small numbers → treat as LPA
            unit = 100_000
        elif nums[0] < 200_000:
            # Likely monthly (e.g. 50000) → annualise
            unit = 12
        else:
            # Large bare number — assume already annual INR
            unit = 1

    lo = int(nums[0] * unit * multiplier)
    hi = int(nums[-1] * unit * multiplier) if len(nums) > 1 else lo

    # Sanity check — reject clearly wrong values
    if lo > 500_000_000 or hi < 10_000:
        return None, None
    return lo, hi
