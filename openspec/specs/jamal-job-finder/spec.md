# Spec: Jamal Job Finder

## What We're Building

An automated system that searches job boards every day for part-time kitchen and hospitality jobs in Glasgow city centre, writes a bespoke cover letter for each match, and applies on Jamal's behalf using browser automation (Playwright). Where auto-apply hits a wall (CAPTCHA, unusual form), it falls back to emailing Jamal with the job details, cover letter, and CV attached. The whole thing runs hands-off once set up.

## Done Looks Like

- Every day, the system checks multiple job boards for new kitchen/hospitality jobs in Glasgow
- Jobs that match (part-time, 16 hours or under, within 50 minutes of Garnethill) are picked up
- For each match, a short cover letter is written specifically for that job, drawing on Jamal's real experience
- The system logs into Jamal's job board accounts and submits applications automatically via Playwright
- Where auto-apply fails (CAPTCHA, unusual form), an email goes to Jamal with everything packaged up and a direct link
- A log is kept of every job found, applied to, or flagged, so nothing gets duplicated
- The system runs daily without anyone needing to touch it

## Requirements

- The system SHALL search Indeed, Reed, S1Jobs, Caterer.com, CV-Library, Totaljobs, and Google Jobs for relevant listings
- The system SHALL filter jobs by: Glasgow / Glasgow city centre location, part-time or hours that fit within 16 per week, kitchen/hospitality/catering roles
- The system SHALL generate a bespoke cover letter for each matching job using Jamal's CV, interview, and personal details as source material
- The system SHALL auto-apply via Playwright browser automation: log into job board accounts, fill forms, upload CV, paste cover letter, and submit
- The system SHALL auto-apply by direct email where a listing provides an employer email address
- The system SHALL fall back to emailing Jamal (with CV, cover letter, and job link attached) when auto-apply is blocked by CAPTCHA, unusual forms, or other barriers
- The system SHALL track all jobs seen, applied to, and flagged to prevent duplicate applications
- The system SHALL run automatically once per day on a schedule
- The system SHALL answer custom employer questions (e.g. "Why do you want this role?") using Jamal's profile and experience
- The system SHALL NOT apply to jobs requiring more than 50 minutes travel from Garnethill
- The system SHALL NOT apply to jobs requiring more than 16 hours per week
- The system SHALL NOT apply to jobs outside kitchen, catering, hospitality, or food service

## Scenarios

### Happy Path: Kitchen porter job on Indeed Easy Apply
- GIVEN a new part-time kitchen porter listing appears on Indeed for a Glasgow city centre restaurant
- WHEN the daily job search runs
- THEN the system logs into Jamal's Indeed account via Playwright, clicks Easy Apply, fills in his details, uploads CV, pastes the bespoke cover letter, and submits. Jamal receives a confirmation email from Indeed.

### Happy Path: Catering job on Reed Quick Apply
- GIVEN a new part-time catering assistant listing appears on Reed with Quick Apply
- WHEN the daily job search runs
- THEN the system logs into Jamal's Reed account, completes the Quick Apply form, attaches CV and cover letter, and submits.

### Happy Path: Job listing with employer email
- GIVEN a listing on S1Jobs includes the employer's direct email address
- WHEN the daily job search runs
- THEN the system sends a professional email from Jamal's Gmail with CV and bespoke cover letter attached.

### Fallback: CAPTCHA blocks auto-apply
- GIVEN a listing on Totaljobs presents a CAPTCHA during the apply flow
- WHEN Playwright cannot proceed
- THEN the system emails Jamal the job link, pre-written cover letter, and CV with a note: "This one needs you to apply manually. Everything's attached."

### Edge Case: Custom employer questions
- GIVEN an Indeed listing asks "Why do you want to work here?" and "Do you have food hygiene certification?"
- WHEN the system encounters these fields during auto-apply
- THEN it generates appropriate answers (referencing his kitchen experience and willingness to complete certification) and fills them in.

### Edge Case: Full-time job that mentions part-time flexibility
- GIVEN a listing says "full-time, part-time hours considered"
- WHEN the daily job search runs
- THEN the system includes it as a match, applies, and the cover letter mentions Jamal's 16-hour availability upfront.

### Edge Case: Duplicate listing across boards
- GIVEN the same job appears on Indeed and Reed
- WHEN the daily job search runs
- THEN the system recognises it as a duplicate (by title, employer, and location) and only processes it once.

### Edge Case: Job in East Kilbride (too far)
- GIVEN a kitchen job is listed in East Kilbride
- WHEN the daily job search runs
- THEN the system skips it because it's outside the travel radius.

## Configuration

- **Jamal's email:** (set in .env as JAMAL_EMAIL)
- **Jamal's phone:** (set in data/profile.json)
- **Location:** Garnethill, Glasgow
- **Max hours:** 16 per week
- **Max travel:** 50 minutes by bus/bike/foot
- **Preferred roles:** Kitchen porter, kitchen assistant, commis chef, catering assistant, dishwasher, food service assistant, front-of-house (hospitality)
- **Available:** Immediately, flexible on days
- **Job board accounts needed:** Indeed, Reed, S1Jobs, Caterer.com, CV-Library, Totaljobs (credentials stored securely in .env)

## Out of Scope

- Building a web dashboard or app (this runs in the background)
- Interview scheduling or follow-up tracking
- Jobs outside Glasgow / outside hospitality
- WhatsApp or SMS notifications (email only for fallback)

## Status: building
