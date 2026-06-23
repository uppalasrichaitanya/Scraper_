import asyncio
import os
import random
from playwright.async_api import async_playwright, Page
from .base import BaseAdapter
from ..schemas.raw_job import RawJobSchema

class LinkedInAdapter(BaseAdapter):
    source_name = "linkedin"
    tier = "playwright"
    schedule_hours = 6

    SEARCH_URLS = [
        "https://www.linkedin.com/jobs/search?keywords=Software%20Engineer&location=India",
        "https://www.linkedin.com/jobs/search?keywords=Data%20Engineer&location=India",
        "https://www.linkedin.com/jobs/search?keywords=Frontend%20Developer&location=India",
    ]

    def get_listing_urls(self) -> list[str]:
        return []

    async def parse_job(self, html: str, url: str) -> list[RawJobSchema]:
        return []

    async def crawl(self) -> list[RawJobSchema]:
        results = []
        use_proxy = os.getenv("LINKEDIN_USE_PROXY", "false").lower() == "true"
        proxy_config = None
        if use_proxy:
            proxy_config = {
                "server": os.getenv("PROXY_HOST", ""),
                "username": os.getenv("PROXY_USERNAME", ""),
                "password": os.getenv("PROXY_PASSWORD", ""),
            }

        async with async_playwright() as p:
            launch_args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            
            browser = await p.chromium.launch(
                headless=True,
                args=launch_args,
                proxy=proxy_config if proxy_config and proxy_config.get("server") else None
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-IN",
            )
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            shuffled_urls = list(self.SEARCH_URLS)
            random.shuffle(shuffled_urls)

            for url in shuffled_urls:
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # LinkedIn public search page
                    await page.wait_for_selector(".jobs-search__results-list", timeout=15000)
                    await self._random_scroll(page)
                    
                    job_cards = await page.query_selector_all(".jobs-search__results-list > li")
                    
                    for card in job_cards[:25]:
                        job = await self._parse_card(card)
                        if job:
                            results.append(job)

                    await asyncio.sleep(self._jitter(8, 12))
                except Exception as e:
                    print(f"linkedin_crawl_error on {url}: {e}")
                finally:
                    await page.close()

            await browser.close()
        return results

    async def _parse_card(self, card) -> RawJobSchema | None:
        try:
            title_el = await card.query_selector("h3.base-search-card__title")
            company_el = await card.query_selector("h4.base-search-card__subtitle")
            location_el = await card.query_selector("span.job-search-card__location")
            link_el = await card.query_selector("a.base-card__full-link")
            
            # Alternative layout elements
            if not title_el:
                title_el = await card.query_selector(".base-card__title")
            if not link_el:
                link_el = await card.query_selector("a.base-card")

            title_text = await title_el.inner_text() if title_el else None
            company_text = await company_el.inner_text() if company_el else None
            location_text = await location_el.inner_text() if location_el else None
            url = await link_el.get_attribute("href") if link_el else None

            if not title_text or not url:
                return None

            # Clean URL to remove tracking params
            url = url.split("?")[0]

            return RawJobSchema(
                source_platform=self.source_name,
                source_url=url,
                title=title_text.strip(),
                company_name=company_text.strip() if company_text else "Unknown",
                location_raw=location_text.strip() if location_text else None,
                is_remote="remote" in (location_text or "").lower()
            )
        except Exception as e:
            print(f"linkedin_parse_error: {e}")
            return None

    async def _random_scroll(self, page: Page):
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.5)")
            await asyncio.sleep(self._jitter(1, 2))

    def _jitter(self, min_s: float, max_s: float) -> float:
        return random.uniform(min_s, max_s)
