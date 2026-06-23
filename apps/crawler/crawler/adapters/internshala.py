import re
from bs4 import BeautifulSoup
from .base import BaseAdapter
from ..schemas.raw_job import RawJobSchema

class InternshalaAdapter(BaseAdapter):
    source_name = "internshala"
    tier = "scrapy"
    schedule_hours = 6
    max_pages = 10

    def get_listing_urls(self) -> list[str]:
        return [f"https://internshala.com/jobs/page-{i}/" for i in range(1, self.max_pages + 1)]

    async def parse_job(self, html: str, url: str) -> list[RawJobSchema]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        
        # Internshala job cards are usually inside divs with class 'individual_internship'
        cards = soup.find_all("div", class_=re.compile("individual_internship|job_card"))
        
        for card in cards:
            title_elem = card.find("h3", class_=re.compile("heading_4_5|job-title"))
            company_elem = card.find("div", class_=re.compile("heading_6|company-name"))
            location_elem = card.find("a", class_="location_link")
            
            # Find salary (usually inside item_detail)
            salary_elem = card.find("span", class_="item_detail")
            
            # Link is usually the parent of the title or an a tag with class view_detail_button
            link_elem = card.find("a", class_="view_detail_button")
            if not link_elem and title_elem and title_elem.parent.name == "a":
                link_elem = title_elem.parent
                
            title = title_elem.get_text(strip=True) if title_elem else None
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            location = location_elem.get_text(strip=True) if location_elem else None
            salary = salary_elem.get_text(strip=True) if salary_elem else None
            href = link_elem["href"] if link_elem and "href" in link_elem.attrs else None
            
            if not title or not href:
                continue
                
            full_url = href if href.startswith("http") else f"https://internshala.com{href}"
            
            results.append(RawJobSchema(
                source_platform=self.source_name,
                source_url=full_url,
                title=title,
                company_name=company,
                location_raw=location,
                salary_raw=salary,
                is_remote="work from home" in (location or "").lower() or "remote" in (location or "").lower()
            ))
            
        return results
