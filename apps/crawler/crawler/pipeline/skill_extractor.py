import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_cache: dict[str, str] = {}  # alias → canonical_name, loaded once at worker startup


async def load_skill_cache(db: "AsyncSession") -> None:
    """Call once at worker startup to populate alias → canonical name mapping."""
    global _cache
    from sqlalchemy import select  # runtime-only import
    from apps.api.models import Skill

    result = await db.execute(select(Skill))
    new_cache: dict[str, str] = {}
    for skill in result.scalars():
        new_cache[skill.name.lower()] = skill.name
        for alias in (skill.aliases or []):
            new_cache[alias.lower()] = skill.name
    _cache = new_cache


def extract_skills(text: str) -> list[str]:
    """Return sorted list of canonical skill names found in text using word-boundary matching."""
    if not _cache:
        return []
    text_lower = text.lower()
    found: set[str] = set()
    for alias, canonical in _cache.items():
        # Word boundary match — avoids "java" matching inside "javascript"
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            found.add(canonical)
    return sorted(found)
