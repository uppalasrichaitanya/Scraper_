from abc import ABC, abstractmethod
from typing import Literal

from ..schemas.raw_job import RawJobSchema


class BaseAdapter(ABC):
    source_name: str
    tier: Literal["scrapy", "playwright"]
    schedule_hours: int = 6
    max_pages: int = 50

    @abstractmethod
    def get_listing_urls(self) -> list[str]: ...

    @abstractmethod
    async def parse_job(self, html: str, url: str) -> list[RawJobSchema]:
        """Parse raw HTML/JSON and return a list of RawJobSchema instances.

        Return an empty list if the page contains no valid job listings.
        """
        ...

    def next_page_url(self, current_url: str, page: int) -> str | None:
        """Return the URL for the next page, or None to stop pagination."""
        return None

    def health_check(self) -> dict:
        return {"source": self.source_name, "status": "ok"}
