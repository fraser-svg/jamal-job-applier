import logging
from playwright.async_api import async_playwright
from scrapers.base import is_valid_location, is_valid_hours, extract_email, is_relevant_role
from config import SEARCH_KEYWORDS, DETAIL_PAGE_DELAY_MS, MAX_DETAIL_PAGES_PER_SCRAPER

log = logging.getLogger(__name__)

INDEED_BASE = "https://uk.indeed.com"


async def scrape_indeed():
    """Scrape Indeed for matching kitchen/hospitality jobs in Glasgow."""
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            detail_count = 0

            for keyword in SEARCH_KEYWORDS:
                try:
                    url = f"{INDEED_BASE}/jobs?q={keyword.replace(' ', '+')}&l=Glasgow&sc=0kf%3Ajt%28parttime%29%3B&fromage=1"
                    log.info(f"Indeed: searching '{keyword}'")
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    cards = await page.query_selector_all('[class*="job_seen_beacon"], [class*="resultContent"]')
                    log.info(f"Indeed: found {len(cards)} cards for '{keyword}'")

                    for card in cards:
                        if detail_count >= MAX_DETAIL_PAGES_PER_SCRAPER:
                            break
                        try:
                            title_el = await card.query_selector('h2 a, h2 span, [class*="jobTitle"] a, [class*="jobTitle"] span')
                            title = await title_el.inner_text() if title_el else None
                            if not title or not is_relevant_role(title):
                                continue

                            link_el = await card.query_selector('h2 a, [class*="jobTitle"] a')
                            href = await link_el.get_attribute("href") if link_el else None
                            if href and not href.startswith("http"):
                                href = INDEED_BASE + href

                            company_el = await card.query_selector('[data-testid="company-name"], [class*="company"]')
                            company = await company_el.inner_text() if company_el else None

                            location_el = await card.query_selector('[data-testid="text-location"], [class*="companyLocation"]')
                            location = await location_el.inner_text() if location_el else None
                            if not is_valid_location(location):
                                continue

                            snippet_el = await card.query_selector('[class*="snippet"], .job-snippet')
                            snippet = await snippet_el.inner_text() if snippet_el else ""

                            salary_el = await card.query_selector('[class*="salary"], [data-testid="attribute_snippet_testid"]')
                            salary = await salary_el.inner_text() if salary_el else None

                            valid_hours, hours_note = is_valid_hours(salary, snippet)
                            if not valid_hours:
                                continue

                            description = ""
                            employer_email = None
                            if href:
                                detail_count += 1
                                await page.wait_for_timeout(DETAIL_PAGE_DELAY_MS)
                                detail_page = await context.new_page()
                                try:
                                    await detail_page.goto(href, wait_until="domcontentloaded", timeout=15000)
                                    await detail_page.wait_for_timeout(1000)
                                    desc_el = await detail_page.query_selector('#jobDescriptionText, [class*="jobsearch-JobComponent-description"]')
                                    if desc_el:
                                        description = await desc_el.inner_text()
                                        employer_email = extract_email(description)
                                except Exception:
                                    pass
                                finally:
                                    await detail_page.close()

                            jobs.append({
                                "source": "Indeed",
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
                            log.warning(f"Indeed: error parsing card: {e}")
                            continue

                except Exception as e:
                    log.error(f"Indeed: error searching '{keyword}': {e}")
                    continue
        finally:
            await browser.close()

    log.info(f"Indeed: found {len(jobs)} matching jobs total")
    return jobs
