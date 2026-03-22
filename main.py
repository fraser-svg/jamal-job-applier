#!/usr/bin/env python3
"""
Jamal Job Finder - Daily automated job search and application system.

Searches multiple UK job boards for part-time kitchen/hospitality jobs
in Glasgow, generates bespoke cover letters, and auto-applies.
Sends a single daily digest email summarising all activity.
"""

import asyncio
import logging
import sys
from datetime import datetime

from config import DATA_DIR
from db import init_db, save_job, job_exists, is_duplicate, update_job_status, get_new_jobs, get_job_stats
from cover_letter import generate_cover_letter
from email_sender import send_application_email, send_daily_digest
from auto_apply import auto_apply
from scrapers import ALL_SCRAPERS
from scrapers.base import is_safe_email

# Ensure data dir exists before setting up logging
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DATA_DIR / f"job_finder_{datetime.now().strftime('%Y%m%d')}.log"),
    ],
)
log = logging.getLogger("main")


async def scrape_all_boards():
    """Run all scrapers and collect new jobs."""
    all_jobs = []
    for name, scraper in ALL_SCRAPERS:
        try:
            log.info(f"--- Scraping {name} ---")
            jobs = await scraper()
            log.info(f"{name}: found {len(jobs)} matching jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"{name}: scraper failed: {e}")
    return all_jobs


def save_new_jobs(jobs):
    """Save jobs to database, skipping duplicates."""
    new_count = 0
    for job in jobs:
        if job_exists(job["url"]):
            continue
        if is_duplicate(job["title"], job.get("employer"), job.get("location")):
            log.info(f"Skipping duplicate: {job['title']} at {job.get('employer')}")
            continue
        save_job(job)
        new_count += 1
        log.info(f"NEW: {job['title']} at {job.get('employer')} ({job['source']})")
    return new_count


async def process_new_jobs():
    """Generate cover letters and apply for all new jobs.
    Returns (applied_jobs, manual_jobs) for the daily digest."""
    applied_jobs = []
    manual_jobs = []  # list of (job, cover_letter) tuples

    jobs = get_new_jobs()
    if not jobs:
        log.info("No new jobs to process")
        return applied_jobs, manual_jobs

    log.info(f"Processing {len(jobs)} new jobs")

    for job in jobs:
        try:
            log.info(f"\n=== Processing: {job['title']} at {job.get('employer', 'Unknown')} ===")

            # Generate cover letter
            cover_letter = generate_cover_letter(job)
            update_job_status(job["url"], "new", cover_letter=cover_letter)

            applied = False

            # Method 1: Direct email if employer email found
            if job.get("employer_email") and is_safe_email(job["employer_email"]):
                log.info(f"Sending direct email to {job['employer_email']}")
                success = send_application_email(job["employer_email"], job, cover_letter)
                if success:
                    update_job_status(
                        job["url"], "applied",
                        apply_method="direct_email",
                        applied_at=datetime.now().isoformat(),
                        cover_letter=cover_letter,
                    )
                    job["apply_method"] = "direct_email"
                    applied_jobs.append(job)
                    applied = True
                    log.info("Applied via direct email")

            # Method 2: Playwright auto-apply on job board
            if not applied:
                log.info(f"Attempting auto-apply on {job['source']}")
                success, reason = await auto_apply(job, cover_letter)
                if success:
                    method = f"auto_apply_{job['source'].lower()}"
                    update_job_status(
                        job["url"], "applied",
                        apply_method=method,
                        applied_at=datetime.now().isoformat(),
                        cover_letter=cover_letter,
                    )
                    job["apply_method"] = method
                    applied_jobs.append(job)
                    applied = True
                    log.info(f"Applied: {reason}")
                else:
                    log.info(f"Auto-apply failed: {reason}")

                    # Check if the failure revealed an email address
                    if reason and "Email application:" in reason:
                        email_addr = reason.split("Email application:")[1].strip()
                        if is_safe_email(email_addr):
                            log.info(f"Found email in apply link: {email_addr}")
                            success = send_application_email(email_addr, job, cover_letter)
                            if success:
                                update_job_status(
                                    job["url"], "applied",
                                    apply_method="direct_email",
                                    applied_at=datetime.now().isoformat(),
                                    cover_letter=cover_letter,
                                )
                                job["apply_method"] = "direct_email"
                                applied_jobs.append(job)
                                applied = True

            # Method 3: Queue for manual application (included in digest)
            if not applied:
                manual_jobs.append((job, cover_letter))
                log.info("Queued for manual application in daily digest")

        except Exception as e:
            log.error(f"Error processing job '{job.get('title', '?')}': {e}")
            continue

    return applied_jobs, manual_jobs


async def run():
    """Main daily job search run."""
    log.info("=" * 60)
    log.info(f"JOB FINDER RUN: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 60)

    # Initialise database
    init_db()

    # Step 1: Scrape all boards
    jobs = await scrape_all_boards()
    log.info(f"\nTotal jobs found across all boards: {len(jobs)}")

    # Step 2: Save new jobs
    new_count = save_new_jobs(jobs)
    log.info(f"New jobs saved: {new_count}")

    # Step 3: Process and apply
    applied_jobs, manual_jobs = await process_new_jobs()

    # Step 4: Send one daily digest email, then mark manual jobs
    digest_sent = send_daily_digest(applied_jobs, manual_jobs)
    if digest_sent:
        for job, cover_letter in manual_jobs:
            update_job_status(job["url"], "emailed", cover_letter=cover_letter)
    else:
        log.warning("Digest failed to send - manual jobs kept as 'new' for retry")

    # Step 5: Summary
    stats = get_job_stats()
    log.info("\n" + "=" * 60)
    log.info("RUN COMPLETE - SUMMARY")
    log.info(f"  Total jobs in database: {stats['total']}")
    log.info(f"  Applied today: {len(applied_jobs)}")
    log.info(f"  Manual (in digest): {len(manual_jobs)}")
    log.info(f"  All-time applied: {stats['applied']}")
    log.info(f"  All-time emailed: {stats['emailed']}")
    log.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())
