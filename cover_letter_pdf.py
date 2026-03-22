import io
import re
from datetime import datetime
from fpdf import FPDF
from config import PROFILE


def _sanitise_text(text):
    """Replace unicode characters that Helvetica can't render."""
    replacements = {
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
        "\u00a0": " ",   # non-breaking space
        "\u2022": "-",   # bullet
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def generate_cover_letter_pdf(cover_letter_text, job):
    """Generate a professionally formatted cover letter PDF.
    Returns the PDF as bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)

    # Margins
    pdf.set_left_margin(25)
    pdf.set_right_margin(25)

    # Header: Jamal's contact info
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, PROFILE["name"].upper(), new_x="LMARGIN", new_y="NEXT", align="L")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 5, f"{PROFILE['phone']}  |  {PROFILE.get('location', 'Glasgow')}", new_x="LMARGIN", new_y="NEXT", align="L")

    # Thin line under header
    pdf.set_draw_color(180, 180, 180)
    y = pdf.get_y() + 3
    pdf.line(25, y, 185, y)
    pdf.set_y(y + 8)

    # Date
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    today = datetime.now().strftime("%d %B %Y")
    pdf.cell(0, 6, today, new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(3)

    # Employer info if available
    employer = job.get("employer")
    if employer:
        employer_clean = _sanitise_text(" ".join(employer.split()))
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, employer_clean, new_x="LMARGIN", new_y="NEXT", align="L")
        location = job.get("location", "")
        if location:
            location_clean = _sanitise_text(" ".join(location.split()))
            pdf.cell(0, 6, location_clean, new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.ln(4)

    # Cover letter body
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 30, 30)

    # Sanitise text for Helvetica compatibility
    clean_text = _sanitise_text(cover_letter_text)

    # Split into paragraphs and render
    paragraphs = clean_text.strip().split("\n\n")
    for i, para in enumerate(paragraphs):
        # Clean up whitespace within paragraph
        lines = para.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if it's the greeting (Dear...) or sign-off (Kind regards)
            if line.startswith("Dear "):
                pdf.set_font("Helvetica", "", 10.5)
                pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT", align="L")
                pdf.ln(3)
            elif line.startswith("Kind regards") or line.startswith("Yours"):
                pdf.ln(3)
                pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT", align="L")
            elif line == PROFILE["name"] or line == PROFILE["phone"]:
                # Name and phone in sign-off
                pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT", align="L")
            else:
                # Regular paragraph text
                pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT", align="L")

        # Space between paragraphs
        if i < len(paragraphs) - 1:
            pdf.ln(2)

    return pdf.output()
