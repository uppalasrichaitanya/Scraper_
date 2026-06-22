import feedparser

from .base import BaseAdapter
from ..schemas.raw_job import RawJobSchema


class WWRAdapter(BaseAdapter):
    source_name = "weworkremotely"
    tier = "scrapy"
    schedule_hours = 4
    BASE_URL = "https://weworkremotely.com"
    LISTING_URL = "https://weworkremotely.com/remote-jobs.rss"  # RSS is more stable than scraping HTML

    def get_listing_urls(self) -> list[str]:
        return [self.LISTING_URL]

    async def parse_job(self, html: str, url: str) -> list[RawJobSchema]:
        """Parse RSS feed — more stable than scraping HTML directly."""
        feed = feedparser.parse(html)
        results = []
        for entry in feed.entries:
            # Entry title is usually "Job Title at Company Name"
            title_parts = entry.title.split(" at ", 1)
            title = title_parts[0].strip() if len(title_parts) > 1 else entry.title
            company = title_parts[1].strip() if len(title_parts) > 1 else ""
            results.append(
                RawJobSchema(
                    source_platform="weworkremotely",
                    source_url=entry.get("link", url),
                    title=title,
                    company_name=company,
                    location_raw="Remote",
                    description_raw=entry.get("summary", ""),
                    is_remote=True,
                    posted_at_raw=entry.get("published"),
                )
            )
        return results
