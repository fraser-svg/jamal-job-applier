import re
import logging
from playwright.async_api import async_playwright
from scrapers.base import is_valid_location, is_valid_hours, extract_email, is_relevant_role
from config import SEARCH_KEYWORDS

log = logging.getLogger(__name__)

REED_BASE = "https://www.reed.co.uk"


async def scrape_reed():
    """Scrape Reed for matching kitchen/hospitality jobs in Glasgow."""
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for keyword in SEARCH_KEYWORDS:
            try:
                slug = keyword.replace(" ", "-")
                url = f"{REED_BASE}/jobs/{slug}-jobs-in-glasgow?parttime=true&postedin=1"
                log.info(f"Reed: searching '{keyword}'")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                cards = await page.query_selector_all("article")
                log.info(f"Reed: found {len(cards)} cards for '{keyword}'")

                for card in cards:
                    try:
                        title_el = await card.query_selector('[data-qa="job-card-title"]')
                        title = await title_el.inner_text() if title_el else None
                        if not title or not is_relevant_role(title):
                            continue

                        # Reed uses buttons not links for job titles - get link from company logo or card
                        link_el = await card.query_selector('a[href*="/jobs/"]')
                        href = None
                        if link_el:
                            href = await link_el.get_attribute("href")
                            if href and not href.startswith("http"):
                                href = REED_BASE + href

                        # Extract company from "posted by" text
                        posted_el = await card.query_selector('[data-qa="job-posted-by"]')
                        company = None
                        if posted_el:
                            posted_text = await posted_el.inner_text()
                            # Format: "3 days ago by Costa Coffee"
                            match = re.search(r'by\s+(.+)', posted_text)
                            if match:
                                company = match.group(1).strip()

                        location_el = await card.query_selector('[data-qa="job-metadata-location"]')
                        location = await location_el.inner_text() if location_el else None
                        if not is_valid_location(location):
                            continue

                        salary_el = await card.query_selector('[data-qa="job-metadata-salary"]')
                        salary = await salary_el.inner_text() if salary_el else None

                        valid_hours, hours_note = is_valid_hours(salary, "part-time")
                        if not valid_hours:
                            continue

                        description = ""
                        employer_email = None
                        if href:
                            try:
                                detail_page = await context.new_page()
                                await detail_page.goto(href, wait_until="domcontentloaded", timeout=15000)
                                await detail_page.wait_for_timeout(1000)
                                desc_el = await detail_page.query_selector('[class*="description"], [class*="job-description"]')
                                if desc_el:
                                    description = await desc_el.inner_text()
                                    employer_email = extract_email(description)
                                await detail_page.close()
                            except Exception:
                                pass

                        # If no direct link found, construct from title
                        if not href:
                            continue

                        jobs.append({
                            "source": "Reed",
                            "title": title.strip(),
                            "employer": company,
                            "location": location.strip() if location else None,
                            "url": href,
                            "hours": "Part-time",
                            "salary": salary,
                            "description": description,
                            "employer_email": employer_email,
                            "notes": hours_note,
                        })
                    except Exception as e:
                        log.warning(f"Reed: error parsing card: {e}")
                        continue

            except Exception as e:
                log.error(f"Reed: error searching '{keyword}': {e}")
                continue

        await browser.close()

    log.info(f"Reed: found {len(jobs)} matching jobs total")
    return jobs
