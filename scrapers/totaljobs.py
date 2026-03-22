import logging
from playwright.async_api import async_playwright
from scrapers.base import is_valid_location, is_valid_hours, extract_email, is_relevant_role
from config import SEARCH_KEYWORDS, DETAIL_PAGE_DELAY_MS, MAX_DETAIL_PAGES_PER_SCRAPER

log = logging.getLogger(__name__)


async def scrape_totaljobs():
    """Scrape Totaljobs for matching kitchen/hospitality jobs in Glasgow."""
    jobs = []
    seen_urls = set()
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
                    url = f"https://www.totaljobs.com/jobs/{keyword.replace(' ', '-')}/in-glasgow?worktypeid=part-time&postedwithin=1"
                    log.info(f"Totaljobs: searching '{keyword}'")
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(3000)

                    job_data = await page.eval_on_selector_all(
                        'a[href*="/job/"]',
                        """els => els.map(a => ({
                            title: a.textContent.trim(),
                            url: a.href,
                        }))"""
                    )
                    log.info(f"Totaljobs: found {len(job_data)} job links for '{keyword}'")

                    for jd in job_data:
                        if detail_count >= MAX_DETAIL_PAGES_PER_SCRAPER:
                            break
                        try:
                            title = jd.get("title", "")
                            href = jd.get("url", "")

                            if not title or not is_relevant_role(title):
                                continue
                            if href in seen_urls:
                                continue
                            seen_urls.add(href)

                            description = ""
                            employer = None
                            location = None
                            salary = None
                            employer_email = None

                            detail_count += 1
                            await page.wait_for_timeout(DETAIL_PAGE_DELAY_MS)
                            detail_page = await context.new_page()
                            try:
                                await detail_page.goto(href, wait_until="domcontentloaded", timeout=15000)
                                await detail_page.wait_for_timeout(1500)

                                company_el = await detail_page.query_selector('[data-testid*="company"], [class*="company"], a[href*="/jobs/"]')
                                if company_el:
                                    employer = (await company_el.inner_text()).strip()

                                loc_el = await detail_page.query_selector('[data-testid*="location"], [class*="location"]')
                                if loc_el:
                                    location = (await loc_el.inner_text()).strip()

                                sal_el = await detail_page.query_selector('[data-testid*="salary"], [class*="salary"]')
                                if sal_el:
                                    salary = (await sal_el.inner_text()).strip()

                                desc_el = await detail_page.query_selector('[class*="description"], [class*="job-description"]')
                                if desc_el:
                                    description = await desc_el.inner_text()
                                    employer_email = extract_email(description)
                            except Exception:
                                pass
                            finally:
                                await detail_page.close()

                            if not location or not is_valid_location(location):
                                continue

                            valid_hours, hours_note = is_valid_hours(salary, description)
                            if not valid_hours:
                                continue

                            jobs.append({
                                "source": "Totaljobs",
                                "title": title.strip(),
                                "employer": employer,
                                "location": location,
                                "url": href,
                                "hours": "Part-time",
                                "salary": salary,
                                "description": description,
                                "employer_email": employer_email,
                                "notes": hours_note,
                            })
                        except Exception as e:
                            log.warning(f"Totaljobs: error parsing job: {e}")
                            continue

                except Exception as e:
                    log.error(f"Totaljobs: error searching '{keyword}': {e}")
                    continue
        finally:
            await browser.close()

    log.info(f"Totaljobs: found {len(jobs)} matching jobs total")
    return jobs
