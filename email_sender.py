import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from config import APP_EMAIL, APP_EMAIL_PASSWORD, JAMAL_EMAIL, CV_PATH
from scrapers.base import is_safe_email

log = logging.getLogger(__name__)


def send_application_email(to_email, job, cover_letter):
    """Send a job application email directly to an employer."""
    if not is_safe_email(to_email):
        log.warning(f"Rejected unsafe email address: {to_email}")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"Jamal Ben Abdellah <{APP_EMAIL}>"
    msg["To"] = to_email
    msg["Reply-To"] = JAMAL_EMAIL
    msg["Subject"] = f"Application – {job['title']} – Jamal Ben Abdellah"

    msg.attach(MIMEText(cover_letter, "plain"))

    # Attach CV
    if CV_PATH.exists():
        with open(CV_PATH, "rb") as f:
            cv = MIMEApplication(f.read(), _subtype="pdf")
            cv.add_header("Content-Disposition", "attachment", filename="Jamal_Ben_Abdellah_CV.pdf")
            msg.attach(cv)

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


def send_fallback_email(job, cover_letter):
    """Send job details + cover letter to Jamal when auto-apply fails."""
    msg = MIMEMultipart()
    msg["From"] = f"Jamal Job Finder <{APP_EMAIL}>"
    msg["To"] = JAMAL_EMAIL
    msg["Subject"] = f"Job found: {job['title']} at {job.get('employer', 'Unknown')}"

    notes = job.get("notes", "")
    notes_line = f"\nNote: {notes}\n" if notes else ""

    body = f"""Hi Jamal,

I found a job that looks like a good match for you:

Job: {job['title']}
Employer: {job.get('employer', 'Unknown')}
Location: {job.get('location', 'Glasgow')}
{f"Pay: {job['salary']}" if job.get('salary') else ""}
{notes_line}
Link to apply: {job['url']}

I could not apply automatically for this one, so you will need to click the link above and apply.
Your cover letter is below and your CV is attached.

---

{cover_letter}

---

Good luck!
"""
    msg.attach(MIMEText(body, "plain"))

    # Attach CV
    if CV_PATH.exists():
        with open(CV_PATH, "rb") as f:
            cv = MIMEApplication(f.read(), _subtype="pdf")
            cv.add_header("Content-Disposition", "attachment", filename="Jamal_Ben_Abdellah_CV.pdf")
            msg.attach(cv)

    # Attach cover letter as a text file too
    cl_attachment = MIMEText(cover_letter)
    cl_attachment.add_header("Content-Disposition", "attachment", filename="Cover_Letter.txt")
    msg.attach(cl_attachment)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(APP_EMAIL, APP_EMAIL_PASSWORD)
            server.send_message(msg)
        log.info(f"Sent fallback email to Jamal for {job['title']}")
        return True
    except Exception as e:
        log.error(f"Failed to send fallback email: {e}")
        return False
