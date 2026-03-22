import logging
from playwright.async_api import async_playwright
from scrapers.base import is_valid_location, is_valid_hours, extract_email, is_relevant_role
from config import SEARCH_KEYWORDS

log = logging.getLogger(__name__)

S1JOBS_BASE = "https://www.s1jobs.com"


async def scrape_s1jobs():
    """Scrape S1Jobs for matching kitchen/hospitality jobs in Glasgow."""
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for keyword in SEARCH_KEYWORDS:
            try:
                url = f"{S1JOBS_BASE}/jobs/glasgow/{keyword.replace(' ', '-')}/?jobType=part-time"
                log.info(f"S1Jobs: searching '{keyword}'")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                cards = await page.query_selector_all('[class*="job-card"], [class*="search-result"], .vacancy')
                log.info(f"S1Jobs: found {len(cards)} cards for '{keyword}'")

                for card in cards:
                    try:
                        title_el = await card.query_selector('h2 a, [class*="title"] a, a[class*="job"]')
                        title = await title_el.inner_text() if title_el else None
                        if not title or not is_relevant_role(title):
                            continue

                        href = await title_el.get_attribute("href") if title_el else None
                        if href and not href.startswith("http"):
                            href = S1JOBS_BASE + href

                        company_el = await card.query_selector('[class*="company"], [class*="employer"]')
                        company = await company_el.inner_text() if company_el else None

                        location_el = await card.query_selector('[class*="location"]')
                        location = await location_el.inner_text() if location_el else None
                        if not is_valid_location(location):
                            continue

                        salary_el = await card.query_selector('[class*="salary"]')
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
                                desc_el = await detail_page.query_selector('[class*="description"], [class*="details"], .vacancy-description')
                                if desc_el:
                                    description = await desc_el.inner_text()
                                    employer_email = extract_email(description)
                                await detail_page.close()
                            except Exception:
                                pass

                        jobs.append({
                            "source": "S1Jobs",
                            "title": title.strip(),
                            "employer": company.strip() if company else None,
                            "location": location.strip() if location else None,
                            "url": href,
                            "hours": "Part-time",
                            "salary": salary,
                            "description": description,
                            "employer_email": employer_email,
                            "notes": hours_note,
                        })
                    except Exception as e:
                        log.warning(f"S1Jobs: error parsing card: {e}")
                        continue

            except Exception as e:
                log.error(f"S1Jobs: error searching '{keyword}': {e}")
                continue

        await browser.close()

    log.info(f"S1Jobs: found {len(jobs)} matching jobs total")
    return jobs
