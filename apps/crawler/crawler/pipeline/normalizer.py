import re

from .salary_parser import parse_salary
from .skill_extractor import extract_skills
from .deduplicator import compute_canonical_id
from ..schemas.raw_job import RawJobSchema
from ..schemas.normalized_job import NormalizedJobSchema

JOB_TYPE_MAP = {
    "full.?time": "full_time",
    "part.?time": "part_time",
    "contract": "contract",
    "intern": "internship",
    "freelance": "freelance",
}


def normalize(raw: RawJobSchema) -> NormalizedJobSchema:
    salary_min, salary_max = parse_salary(raw.salary_raw)
    skill_names = extract_skills(
        (raw.title or "")
        + " "
        + (raw.description_raw or "")
        + " "
        + " ".join(raw.skills_raw)
    )
    city = _parse_city(raw.location_raw)
    canonical_id = compute_canonical_id(raw.title, raw.company_name, city or "")

    return NormalizedJobSchema(
        canonical_id=canonical_id,
        source_platform=raw.source_platform,
        source_url=raw.source_url,
        title_raw=raw.title,
        title_normalized=_normalize_title(raw.title),
        company_name=raw.company_name,
        location_city=city,
        salary_min=salary_min,
        salary_max=salary_max,
        salary_raw_text=raw.salary_raw,
        job_type=_detect_job_type(raw.job_type_raw or raw.title),
        is_remote=raw.is_remote or _detect_remote(raw.title, raw.location_raw),
        experience_min_years=_parse_exp(raw.description_raw)[0],
        experience_max_years=_parse_exp(raw.description_raw)[1],
        skill_names=skill_names,
        description_raw=raw.description_raw,
    )


def _parse_city(loc: str | None) -> str | None:
    if not loc:
        return None
    # Strip country names, pin codes, "India" etc.
    loc = re.sub(r"\b(india|IN|\d{6})\b", "", loc, flags=re.IGNORECASE)
    parts = [p.strip() for p in re.split(r"[,/|]", loc) if p.strip()]
    return parts[0].title() if parts else None


def _detect_remote(title: str, loc: str | None) -> bool:
    combined = f"{title} {loc or ''}".lower()
    return bool(re.search(r"\bremote\b", combined))


def _detect_job_type(text: str) -> str | None:
    for pattern, jtype in JOB_TYPE_MAP.items():
        if re.search(pattern, text, re.IGNORECASE):
            return jtype
    return "full_time"  # safe default


def _parse_exp(description: str | None) -> tuple[int | None, int | None]:
    if not description:
        return None, None
    m = re.search(r"(\d+)\s*[-\u2013to]+\s*(\d+)\s*(?:years?|yrs?)", description, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)\+?\s*(?:years?|yrs?)", description, re.IGNORECASE)
    if m:
        return int(m.group(1)), None
    return None, None


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower().strip())
