import argparse
import html
import re
import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle


def inline_markup(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def wrap_code(code, width=108):
    wrapped = []
    for line in code.splitlines():
        if not line:
            wrapped.append("")
            continue
        indent = len(line) - len(line.lstrip())
        wrapped.extend(textwrap.wrap(
            line,
            width=width,
            subsequent_indent=" " * min(indent + 2, 16),
            break_long_words=True,
            break_on_hyphens=False,
        ))
    return "\n".join(wrapped)


def make_story(markdown, available_width):
    palette = {
        "ink": colors.HexColor("#18323A"),
        "teal": colors.HexColor("#176B67"),
        "muted": colors.HexColor("#586B70"),
        "rule": colors.HexColor("#D8E2E0"),
        "code_bg": colors.HexColor("#F1F5F3"),
    }
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "GuideTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=23, leading=28, textColor=palette["ink"], alignment=1,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "SectionHeading", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=15, leading=19, textColor=palette["teal"], spaceBefore=12,
            spaceAfter=7, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Subheading", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=11, leading=14, textColor=palette["ink"], spaceBefore=8,
            spaceAfter=4, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "GuideBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.5, leading=13.5, textColor=palette["ink"], spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "GuideBullet", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.5, leading=13, textColor=palette["ink"], leftIndent=14,
            firstLineIndent=-9, spaceAfter=3,
        ),
        "quote": ParagraphStyle(
            "GuideQuote", parent=base["BodyText"], fontName="Helvetica-Oblique",
            fontSize=9.5, leading=14, textColor=palette["muted"], leftIndent=12,
            borderColor=palette["teal"], borderWidth=2, borderPadding=7,
            spaceBefore=4, spaceAfter=9,
        ),
        "code": ParagraphStyle(
            "CodeBlock", fontName="Courier", fontSize=7.6, leading=10.2,
            textColor=palette["ink"],
        ),
        "code_label": ParagraphStyle(
            "CodeLabel", fontName="Helvetica-Bold", fontSize=7,
            textColor=palette["teal"], spaceAfter=3,
        ),
    }

    story = []
    lines = markdown.splitlines()
    in_code = False
    code_language = ""
    code_lines = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            if in_code:
                code = Preformatted(wrap_code("\n".join(code_lines)), styles["code"])
                block = Table([[code]], colWidths=[available_width])
                block.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), palette["code_bg"]),
                    ("BOX", (0, 0), (-1, -1), 0.5, palette["rule"]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]))
                if code_language:
                    story.append(Paragraph(html.escape(code_language.upper()), styles["code_label"]))
                story.extend([block, Spacer(1, 6)])
                code_lines = []
                in_code = False
            else:
                in_code = True
                code_language = line[3:].strip()
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue

        if line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["title"]))
            subtitle = ParagraphStyle(
                "Subtitle", parent=styles["body"], alignment=1,
                textColor=palette["muted"], fontSize=10, spaceAfter=14,
            )
            story.append(Paragraph("SQL commands and live checks for demonstrating BuildCore", subtitle))
        elif line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["h2"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["h3"]))
        elif line.startswith("- [ ] "):
            story.append(Paragraph("[ ] " + inline_markup(line[6:]), styles["bullet"]))
        elif line.startswith("- "):
            story.append(Paragraph("&#8226; " + inline_markup(line[2:]), styles["bullet"]))
        elif line.startswith("> "):
            story.append(Paragraph(inline_markup(line[2:]), styles["quote"]))
        elif line.startswith("---"):
            story.append(Spacer(1, 5))
        elif line.strip():
            story.append(Paragraph(inline_markup(line.strip()), styles["body"]))
        else:
            story.append(Spacer(1, 3))
        index += 1

    if in_code and code_lines:
        story.append(Preformatted(wrap_code("\n".join(code_lines)), styles["code"]))
    return story


def add_page_chrome(canvas, document):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#D8E2E0"))
    canvas.setLineWidth(0.6)
    canvas.line(document.leftMargin, height - 36, width - document.rightMargin, height - 36)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#586B70"))
    canvas.drawString(document.leftMargin, 23, "BuildCore | SQL & Project Verification")
    canvas.drawRightString(width - document.rightMargin, 23, f"Page {document.page}")
    canvas.restoreState()


def main():
    parser = argparse.ArgumentParser(description="Export a Markdown guide to a readable PDF.")
    parser.add_argument("source", nargs="?", default="PROJECT_PRESENTATION_DOCUMENT.md")
    parser.add_argument("output", nargs="?", default="PROJECT_PRESENTATION_DOCUMENT.pdf")
    arguments = parser.parse_args()
    source = Path(arguments.source)
    output = Path(arguments.output)

    markdown = source.read_text(encoding="utf-8")
    document = SimpleDocTemplate(
        str(output), pagesize=A4, rightMargin=44, leftMargin=44,
        topMargin=52, bottomMargin=40, title=source.stem.replace("_", " "),
        author="BuildCore Project Team",
    )
    document.build(make_story(markdown, document.width), onFirstPage=add_page_chrome, onLaterPages=add_page_chrome)
    print(f"Created {output.resolve()}")


if __name__ == "__main__":
    main()
