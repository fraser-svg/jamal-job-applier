import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from config import APP_EMAIL, APP_EMAIL_PASSWORD, JAMAL_EMAIL, CV_PATH
from scrapers.base import is_safe_email
from cover_letter_pdf import generate_cover_letter_pdf

log = logging.getLogger(__name__)


def _attach_cover_letter_pdf(msg, cover_letter_text, job):
    """Generate and attach a formatted cover letter PDF."""
    try:
        pdf_bytes = generate_cover_letter_pdf(cover_letter_text, job)
        clean_title = "_".join(job.get("title", "Role").split())
        filename = f"Cover_Letter_{clean_title}.pdf"
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_attachment.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(pdf_attachment)
    except Exception as e:
        log.error(f"Failed to generate cover letter PDF: {e}")


def send_application_email(to_email, job, cover_letter):
    """Send a job application email directly to an employer."""
    if not is_safe_email(to_email):
        log.warning(f"Rejected unsafe email address: {to_email}")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"Jamal Ben Abdellah <{APP_EMAIL}>"
    msg["To"] = to_email
    msg["Reply-To"] = JAMAL_EMAIL
    clean_title = " ".join(job["title"].split())
    msg["Subject"] = f"Application – {clean_title} – Jamal Ben Abdellah"

    if not APP_EMAIL or not APP_EMAIL_PASSWORD:
        log.error("Email credentials not configured - cannot send application")
        return False

    msg.attach(MIMEText(cover_letter, "plain"))

    # Attach CV
    if CV_PATH.exists():
        with open(CV_PATH, "rb") as f:
            cv = MIMEApplication(f.read(), _subtype="pdf")
            cv.add_header("Content-Disposition", "attachment", filename="Jamal_Ben_Abdellah_CV.pdf")
            msg.attach(cv)

    # Attach cover letter as formatted PDF
    _attach_cover_letter_pdf(msg, cover_letter, job)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)
        log.info(f"Sent application email to {to_email} for {job['title']}")
        return True
    except Exception as e:
        log.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_daily_digest(applied_jobs, manual_jobs):
    """Send a single daily summary email listing all jobs applied to and any needing manual action."""
    total = len(applied_jobs) + len(manual_jobs)
    if total == 0:
        log.info("No jobs to report today - skipping digest email")
        return True

    today = datetime.now().strftime("%A %d %B")

    # Build the applied section
    applied_section = ""
    if applied_jobs:
        applied_section = f"I applied to {len(applied_jobs)} job{'s' if len(applied_jobs) != 1 else ''} for you today:\n\n"
        for i, job in enumerate(applied_jobs, 1):
            clean_title = " ".join((job.get("title") or "").split())
            employer = " ".join((job.get("employer") or "Unknown").split())
            location = job.get("location", "Glasgow")
            method = job.get("apply_method", "")
            if "email" in method:
                how = "sent your CV and cover letter by email"
            else:
                how = "applied through the job board"
            applied_section += f"  {i}. {clean_title} at {employer} ({location})\n     - {how}\n\n"

    # Build the manual section
    manual_section = ""
    if manual_jobs:
        manual_section = f"\nThere {'is' if len(manual_jobs) == 1 else 'are'} {len(manual_jobs)} job{'s' if len(manual_jobs) != 1 else ''} I could not apply to automatically. You will need to click the link and apply yourself. Your cover letter for each one is attached as a PDF.\n\n"
        for i, (job, cover_letter) in enumerate(manual_jobs, 1):
            clean_title = " ".join((job.get("title") or "").split())
            employer = " ".join((job.get("employer") or "Unknown").split())
            location = job.get("location", "Glasgow")
            salary = job.get("salary", "")
            salary_line = f"\n     Pay: {salary}" if salary else ""
            notes = job.get("notes", "")
            notes_line = f"\n     Note: {notes}" if notes else ""
            manual_section += (
                f"  {i}. {clean_title} at {employer} ({location}){salary_line}{notes_line}\n"
                f"     Link: {job['url']}\n\n"
            )

    body = f"""Hi Jamal,

Here is your job update for {today}.

{applied_section}{manual_section}
Keep going - good things are coming!
"""

    msg = MIMEMultipart()
    msg["From"] = f"Jamal Job Finder <{APP_EMAIL}>"
    msg["To"] = JAMAL_EMAIL
    msg["Subject"] = f"Your daily job update - {today}"

    if not APP_EMAIL or not APP_EMAIL_PASSWORD:
        log.error("Email credentials not configured - cannot send digest")
        return False

    msg.attach(MIMEText(body, "plain"))

    # Attach CV so it's always handy for the manual applications
    if manual_jobs and CV_PATH.exists():
        with open(CV_PATH, "rb") as f:
            cv = MIMEApplication(f.read(), _subtype="pdf")
            cv.add_header("Content-Disposition", "attachment", filename="Jamal_Ben_Abdellah_CV.pdf")
            msg.attach(cv)

    # Attach a cover letter PDF for each manual job
    for job, cover_letter in manual_jobs:
        _attach_cover_letter_pdf(msg, cover_letter, job)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)
        log.info(f"Sent daily digest: {len(applied_jobs)} applied, {len(manual_jobs)} manual")
        return True
    except Exception as e:
        log.error(f"Failed to send daily digest: {e}")
        return False
