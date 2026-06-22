import asyncio
from playwright.async_api import async_playwright, Page
from .base import BaseAdapter
from ..schemas.raw_job import RawJobSchema
import hashlib

class NaukriAdapter(BaseAdapter):
    source_name = "naukri"
    tier = "playwright"

    SEARCH_URLS = [
        "/python-jobs",
        "/software-engineer-jobs",
        "/data-engineer-jobs",
        "/backend-developer-jobs",
        "/react-jobs",
    ]

    def get_listing_urls(self) -> list[str]:
        return []

    async def parse_job(self, html: str, url: str) -> list[RawJobSchema]:
        return []

    async def crawl(self) -> list[RawJobSchema]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-IN",
            )
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            for path in self.SEARCH_URLS:
                page = await context.new_page()
                try:
                    await page.goto(f"https://www.naukri.com{path}", wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_selector(".jobTuple", timeout=15000)
                    await self._random_scroll(page)

                    job_cards = await page.query_selector_all(".jobTuple")
                    for card in job_cards[:50]:
                        job = await self._parse_card(card)
                        if job:
                            results.append(job)

                    await asyncio.sleep(self._jitter(3, 7))
                except Exception as e:
                    print(f"naukri_crawl_error on {path}: {e}")
                finally:
                    await page.close()

            await browser.close()
        return results

    async def _parse_card(self, card) -> RawJobSchema | None:
        try:
            title = await card.query_selector(".title")
            company = await card.query_selector(".companyInfo .subTitle")
            location = await card.query_selector(".location li")
            salary = await card.query_selector(".salary")
            link = await card.query_selector("a.title")

            title_text = await title.inner_text() if title else None
            company_text = await company.inner_text() if company else None
            location_text = await location.inner_text() if location else None
            salary_text = await salary.inner_text() if salary else None
            url = await link.get_attribute("href") if link else None

            if not title_text or not url:
                return None

            return RawJobSchema(
                source_platform=self.source_name,
                source_url=url if url.startswith("http") else f"https://www.naukri.com{url}",
                title=title_text.strip(),
                company_name=company_text.strip() if company_text else "Unknown",
                location_raw=location_text,
                salary_raw=salary_text,
                is_remote="remote" in (location_text or "").lower()
            )
        except Exception as e:
            print(f"naukri_parse_error: {e}")
            return None

    async def _random_scroll(self, page: Page):
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 0.7)")
            await asyncio.sleep(self._jitter(0.5, 1.5))

    def _jitter(self, min_s: float, max_s: float) -> float:
        import random
        return random.uniform(min_s, max_s)
