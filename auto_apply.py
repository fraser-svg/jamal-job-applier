import os
import logging
from playwright.async_api import async_playwright
from cover_letter import generate_question_answer
from config import CV_PATH, PROFILE

log = logging.getLogger(__name__)


def _get_label(el_eval_result):
    """Normalise label text from element evaluation."""
    return (el_eval_result or "").strip().lower()


_LABEL_JS = """el => {
    const id = el.id || el.name;
    const label = document.querySelector(`label[for="${id}"]`);
    return label ? label.textContent : el.placeholder || el.name || '';
}"""


async def _fill_textarea_smart(textarea, cover_letter, job):
    """Fill a textarea based on its label context."""
    label = _get_label(await textarea.evaluate(_LABEL_JS))
    if any(kw in label for kw in ["cover", "letter", "message", "why", "about"]):
        await textarea.fill(cover_letter)
    elif label:
        answer = generate_question_answer(label, job)
        await textarea.fill(answer)


async def _fill_input_fields(page):
    """Fill standard input fields (name, email, phone, etc.)."""
    inputs = await page.query_selector_all(
        'input[type="text"]:not([readonly]), input:not([type]):not([readonly])'
    )
    for inp in inputs:
        value = await inp.input_value()
        if value:
            continue
        label = _get_label(await inp.evaluate(_LABEL_JS))
        if "phone" in label or "mobile" in label:
            await inp.fill(PROFILE["phone"])
        elif "name" in label and "first" in label:
            await inp.fill("Jamal")
        elif "name" in label and ("last" in label or "sur" in label):
            await inp.fill("Ben Abdellah")
        elif "name" in label:
            await inp.fill(PROFILE["name"])
        elif "email" in label:
            await inp.fill(os.getenv("APP_EMAIL", ""))
        elif "city" in label or "location" in label:
            await inp.fill("Glasgow")
        elif "post" in label and "code" in label:
            await inp.fill("G3")


async def auto_apply_indeed(job, cover_letter):
    """Attempt to auto-apply on Indeed using Easy Apply."""
    email = os.getenv("INDEED_EMAIL")
    password = os.getenv("INDEED_PASSWORD")
    if not email or not password:
        return False, "No Indeed credentials"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Login to Indeed
            await page.goto("https://secure.indeed.com/auth", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            email_input = await page.query_selector('input[type="email"], #ifl-InputFormField-3')
            if email_input:
                await email_input.fill(email)
                submit = await page.query_selector('button[type="submit"]')
                if submit:
                    await submit.click()
                    await page.wait_for_timeout(2000)

                    pass_input = await page.query_selector('input[type="password"]')
                    if pass_input:
                        await pass_input.fill(password)
                        submit2 = await page.query_selector('button[type="submit"]')
                        if submit2:
                            await submit2.click()
                            await page.wait_for_timeout(3000)

            # Check for CAPTCHA
            captcha = await page.query_selector('[class*="captcha"], #captcha, iframe[src*="captcha"]')
            if captcha:
                return False, "CAPTCHA detected"

            # Navigate to job
            await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # Click Apply button
            apply_btn = await page.query_selector(
                'button[id*="apply"], button[class*="apply"], '
                '[data-testid="applyButton"], a[class*="apply"]'
            )
            if not apply_btn:
                return False, "No apply button found"

            await apply_btn.click()
            await page.wait_for_timeout(3000)

            # Handle the apply flow
            max_steps = 10
            for step in range(max_steps):
                captcha = await page.query_selector('[class*="captcha"], #captcha')
                if captcha:
                    return False, "CAPTCHA during application"

                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(str(CV_PATH))
                    await page.wait_for_timeout(1000)

                textareas = await page.query_selector_all('textarea:not([readonly])')
                for textarea in textareas:
                    await _fill_textarea_smart(textarea, cover_letter, job)

                await _fill_input_fields(page)

                submit_btn = await page.query_selector(
                    'button[type="submit"], button[class*="continue"], '
                    'button[class*="next"], button[class*="submit"], '
                    '[data-testid*="submit"], [data-testid*="continue"]'
                )

                if submit_btn:
                    btn_text = (await submit_btn.inner_text()).lower()
                    if "submit" in btn_text or "apply" in btn_text or "send" in btn_text:
                        await submit_btn.click()
                        await page.wait_for_timeout(3000)

                        success = await page.query_selector(
                            '[class*="success"], [class*="confirmation"], '
                            '[class*="applied"], [data-testid*="success"]'
                        )
                        page_text = await page.inner_text("body")
                        if success or ("application" in page_text.lower() and "submitted" in page_text.lower()):
                            return True, "Applied via Indeed Easy Apply"

                        return False, "Submit clicked but couldn't confirm success"

                    await submit_btn.click()
                    await page.wait_for_timeout(2000)
                else:
                    break

            return False, "Ran out of steps in apply flow"

        except Exception as e:
            log.error(f"Indeed auto-apply error: {e}")
            return False, str(e)
        finally:
            await browser.close()


async def auto_apply_reed(job, cover_letter):
    """Attempt to auto-apply on Reed."""
    email = os.getenv("REED_EMAIL")
    password = os.getenv("REED_PASSWORD")
    if not email or not password:
        return False, "No Reed credentials"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Login to Reed
            await page.goto("https://www.reed.co.uk/account/signin", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            email_input = await page.query_selector('input[name="Email"], input[type="email"]')
            pass_input = await page.query_selector('input[name="Password"], input[type="password"]')
            if email_input and pass_input:
                await email_input.fill(email)
                await pass_input.fill(password)
                submit = await page.query_selector('button[type="submit"]')
                if submit:
                    await submit.click()
                    await page.wait_for_timeout(3000)

            captcha = await page.query_selector('[class*="captcha"], #captcha')
            if captcha:
                return False, "CAPTCHA detected"

            # Navigate to job and apply
            await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            apply_btn = await page.query_selector(
                'a[class*="apply"], button[class*="apply"], '
                '[data-qa="apply-button"]'
            )
            if not apply_btn:
                return False, "No apply button found"

            await apply_btn.click()
            await page.wait_for_timeout(3000)

            # Fill cover letter if present
            textareas = await page.query_selector_all('textarea:not([readonly])')
            for textarea in textareas:
                await _fill_textarea_smart(textarea, cover_letter, job)

            # Upload CV if needed
            file_input = await page.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(str(CV_PATH))
                await page.wait_for_timeout(1000)

            # Submit
            submit_btn = await page.query_selector(
                'button[type="submit"], button[class*="submit"], '
                'input[type="submit"]'
            )
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(3000)

                page_text = await page.inner_text("body")
                if any(w in page_text.lower() for w in ["applied", "success", "submitted"]):
                    return True, "Applied via Reed"

            return False, "Could not confirm application submitted"

        except Exception as e:
            log.error(f"Reed auto-apply error: {e}")
            return False, str(e)
        finally:
            await browser.close()


async def auto_apply_generic(job, cover_letter):
    """Generic auto-apply attempt for other job boards."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            apply_btn = await page.query_selector(
                'a[class*="apply" i], button[class*="apply" i], '
                'a[href*="apply"], [data-testid*="apply"]'
            )
            if not apply_btn:
                return False, "No apply button found"

            href = await apply_btn.get_attribute("href")
            if href and ("mailto:" in href):
                email_addr = href.replace("mailto:", "").split("?")[0]
                return False, f"Email application: {email_addr}"

            await apply_btn.click()
            await page.wait_for_timeout(3000)

            captcha = await page.query_selector('[class*="captcha"], #captcha')
            if captcha:
                return False, "CAPTCHA detected"

            # Fill textareas using smart detection
            textareas = await page.query_selector_all('textarea:not([readonly])')
            for textarea in textareas:
                await _fill_textarea_smart(textarea, cover_letter, job)

            file_input = await page.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(str(CV_PATH))

            await _fill_input_fields(page)

            submit_btn = await page.query_selector(
                'button[type="submit"], input[type="submit"]'
            )
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(3000)
                page_text = await page.inner_text("body")
                if any(w in page_text.lower() for w in ["applied", "success", "submitted", "thank"]):
                    return True, f"Applied via {job['source']}"

            return False, "Could not complete application"

        except Exception as e:
            log.error(f"Generic auto-apply error: {e}")
            return False, str(e)
        finally:
            await browser.close()


APPLY_HANDLERS = {
    "Indeed": auto_apply_indeed,
    "Reed": auto_apply_reed,
}


async def auto_apply(job, cover_letter):
    """Try to auto-apply for a job. Returns (success, method/reason)."""
    source = job["source"]
    handler = APPLY_HANDLERS.get(source, auto_apply_generic)
    return await handler(job, cover_letter)
