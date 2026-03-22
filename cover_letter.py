import json
import logging
import time
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, PROFILE

log = logging.getLogger(__name__)

client = None
if ANTHROPIC_API_KEY:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Only send safe fields to the API - no NI number, share code, DOB, emails
_COVER_LETTER_FIELDS = {
    "name", "preferred_name", "phone", "location",
    "max_hours_per_week", "experience_summary", "work_history",
    "personal_strengths", "languages", "willing_to_complete",
    "references", "available",
}
# Explicitly exclude: nationality, right_to_work, ni_number, share_code,
# date_of_birth, personal_email, application_email, transport, target_roles
_SAFE_PROFILE = {k: v for k, v in PROFILE.items() if k in _COVER_LETTER_FIELDS}


def generate_cover_letter(job, max_retries=3):
    """Generate a bespoke cover letter for a specific job using Claude."""
    if not client:
        log.warning("No Anthropic API key set - using template cover letter")
        return _template_cover_letter(job)

    prompt = f"""Write a short, warm cover letter for Jamal Ben Abdellah applying for this job.

JOB DETAILS:
- Title: {job['title']}
- Employer: {job.get('employer', 'Unknown')}
- Location: {job.get('location', 'Glasgow')}
- Description: {job.get('description', 'No description available')[:2000]}

JAMAL'S PROFILE:
{json.dumps(_SAFE_PROFILE, indent=2)}

TONE:
- Warm, professional, friendly, human, eager, enthusiastic, energetic.
- The reader should feel like Jamal genuinely wants this job and would be great to have around.
- Think: the kind of cover letter that makes a manager smile and think "I want to meet this person."

RULES:
- Maximum 200 words. Keep it short and genuine.
- Write in first person as Jamal.
- Mention his 6 years of kitchen experience in Morocco (porter to chef).
- Mention his current volunteering at Glasgow City Mission (5 days/week, over six months).
- Mention he's available for up to 16 hours per week and can start immediately.
- If the job description mentions specific requirements, address them directly.
- Sound natural, not robotic. Jamal is warm, hardworking, and humble.
- Show genuine enthusiasm for the specific role and place. If the employer name is known, reference it naturally.
- Do NOT use fancy vocabulary - keep language simple, clear, and conversational.
- Do NOT use cliches like "I believe I would be a great fit" or "I am writing to express my interest."
- NEVER use em dashes (—) or en dashes (–). Use commas, full stops, or restructure the sentence instead.
- Do NOT include a subject line, just the letter body.
- Start with "Dear" followed by the employer name or "Hiring Manager".
- End with "Kind regards, Jamal Ben Abdellah" and his phone number {PROFILE['phone']}.
- Use British English throughout.
"""

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            if "rate" in str(e).lower() and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                log.warning(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                log.error(f"Cover letter generation failed: {e}")
                log.warning("Falling back to template cover letter")
                return _template_cover_letter(job)

    return _template_cover_letter(job)


def generate_question_answer(question, job):
    """Generate an answer to a custom employer question."""
    if not client:
        return _default_answer(question)

    prompt = f"""Answer this employer question for a job application on behalf of Jamal Ben Abdellah.

QUESTION: {question}

JOB: {job['title']} at {job.get('employer', 'Unknown')}

JAMAL'S PROFILE:
{json.dumps(_SAFE_PROFILE, indent=2)}

RULES:
- Answer in first person as Jamal.
- Keep it brief (1-3 sentences).
- Be honest. If he doesn't have something (like food hygiene cert), say he's willing to get it.
- Simple, clear language.
"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        log.error(f"Question answer generation failed: {e}")
        return _default_answer(question)


def _template_cover_letter(job):
    """Fallback template when Claude API isn't available."""
    employer = job.get("employer", "Hiring Manager")
    title = job["title"]
    phone = PROFILE["phone"]
    return f"""Dear {employer},

I am writing to apply for the {title} position.

I have six years of kitchen experience from working in restaurants and hotels in Morocco, where I progressed from Kitchen Porter to Commis Chef. I am currently volunteering five days a week at Glasgow City Mission, preparing and serving meals for people experiencing homelessness. I have been doing this consistently for over six months.

I am available to work up to 16 hours per week and can start immediately. I am reliable, hardworking, and always bring a positive attitude to my work. I am also willing to complete food hygiene certification.

I would welcome the opportunity to discuss this role further.

Kind regards,
Jamal Ben Abdellah
{phone}"""


def _default_answer(question):
    """Generic answer for common employer questions."""
    q = question.lower()
    if "food hygiene" in q or "certification" in q or "certificate" in q:
        return "I do not currently hold a food hygiene certificate but I am willing to complete the certification straight away."
    if "why" in q and ("want" in q or "apply" in q or "interest" in q):
        return "I have six years of kitchen experience and I love working in kitchens. I am currently volunteering at Glasgow City Mission and I want to build a career in hospitality in Glasgow."
    if "experience" in q:
        return "I have six years of kitchen experience in Morocco, working in restaurants and a hotel. I progressed from Kitchen Porter to Commis Chef. I am currently volunteering at Glasgow City Mission five days a week."
    if "available" in q or "start" in q or "hours" in q:
        return "I am available to start immediately and can work up to 16 hours per week. I am flexible on days and shift patterns."
    if "right to work" in q or "visa" in q or "eligible" in q:
        return "Yes, I have the full right to work in the UK. My share code is available on request."
    return "I am a hardworking and reliable kitchen professional with six years of experience. I am available immediately and happy to discuss any questions you may have."
