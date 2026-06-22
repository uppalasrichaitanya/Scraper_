import json

from .base import BaseAdapter
from ..schemas.raw_job import RawJobSchema


class RemoteOKAdapter(BaseAdapter):
    source_name = "remoteok"
    tier = "scrapy"
    schedule_hours = 2
    API_URL = "https://remoteok.com/api"

    def get_listing_urls(self) -> list[str]:
        return [self.API_URL]

    async def parse_job(self, html: str, url: str) -> list[RawJobSchema]:
        """RemoteOK returns a JSON array. First element is metadata — skip it."""
        try:
            jobs = json.loads(html)
        except json.JSONDecodeError:
            return []

        results = []
        for item in jobs:
            if not isinstance(item, dict) or "position" not in item:
                continue
            results.append(
                RawJobSchema(
                    source_platform="remoteok",
                    source_url=item.get("url", ""),
                    title=item.get("position", ""),
                    company_name=item.get("company", ""),
                    location_raw=item.get("location", "Remote"),
                    description_raw=item.get("description", ""),
                    salary_raw=self._parse_salary_range(item),
                    skills_raw=item.get("tags", []),
                    is_remote=True,
                    posted_at_raw=item.get("date"),
                )
            )
        return results

    def _parse_salary_range(self, item: dict) -> str | None:
        lo, hi = item.get("salary_min"), item.get("salary_max")
        if lo and hi:
            return f"${lo}–${hi}"
        return None
