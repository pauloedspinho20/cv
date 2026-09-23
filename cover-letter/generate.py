#!/usr/bin/env python3
"""
Generate a tailored cover letter from cover-letter/template.html.

Zero dependencies. Writes HTML, plain text and (on macOS with Chrome) a PDF.

Examples
--------
  # interactive (prompts for the placeholders)
  python3 cover-letter/generate.py

  # one-liner
  python3 cover-letter/generate.py -r "Senior Full-Stack Developer" \\
      -c "Acme Corp" -m "Jane Doe" --flavor ai

  # add a paragraph that mirrors a specific job requirement
  python3 cover-letter/generate.py -r "Full-Stack Engineer" -c "Acme" \\
      -x "Your mention of event-driven architecture maps to the real-time WebSocket streaming I do at Miew."

Run `python3 cover-letter/generate.py --help` for all options.
"""

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "template.html")

OPENERS = {
    "general": (
        "I am applying for the {role} position at {company}. I am a full-stack developer with "
        "10+ years building and shipping web platforms in fintech, AI, blockchain, e-commerce and "
        "entertainment, and I work end to end: React, Next.js and TypeScript on the front end; "
        "Node.js, Python (FastAPI), PHP/Laravel and ASP.NET Core on the back end; SQL and data "
        "modelling underneath."
    ),
    "ai": (
        "I am applying for the {role} position at {company}. I ship production LLM features, not "
        "demos, and I would like to bring that applied-AI engineering to your team. I build with "
        "FastAPI, LangChain, RAG and retrieval pipelines on top of a 10-year full-stack foundation in "
        "React, Node.js and .NET."
    ),
    "fintech": (
        "I am applying for the {role} position at {company}. I have spent the last two years building "
        "production fintech and AI platforms, including daskapital.eu and koltena.com, and I would "
        "like to bring that end-to-end delivery to your team."
    ),
    "startup": (
        "I am applying for the {role} position at {company}. I have worked in both small and large "
        "teams and across every stage of a web product, from concept and design to testing, delivery "
        "and client communication, and I am comfortable owning a feature end to end."
    ),
    "enterprise": (
        "I am applying for the {role} position at {company}. My career started in backend and data "
        "with ASP.NET, .NET Core and SQL Server, and I now pair that foundation with modern React and "
        "Next.js front ends at enterprise scale."
    ),
    "wordpress": (
        "I am applying for the {role} position at {company}. I build WordPress the modern way: custom "
        "themes and plugins in PHP, plus headless WordPress front ends driven by the REST API and React "
        "or Next.js, all tuned for speed and Core Web Vitals. That work sits on a 10-year full-stack "
        "foundation in PHP, JavaScript and SQL."
    ),
}


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", value) or "company"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def build_html(role, company, salutation, opening, custom):
    with open(TEMPLATE, encoding="utf-8") as fh:
        tpl = fh.read()
    custom_section = ""
    if custom.strip():
        custom_section = "    <p>" + esc(custom.strip()) + "</p>\n"
    values = {
        "DATE": esc(date.today().strftime("%-d %B %Y") if os.name != "nt"
                    else f"{date.today().day} {date.today().strftime('%B %Y')}"),
        "SALUTATION": esc(salutation),
        "ROLE_TITLE": esc(role),
        "COMPANY": esc(company),
        "OPENING": esc(opening),
        "CUSTOM_SECTION": custom_section,
    }
    for key, val in values.items():
        tpl = tpl.replace("{{" + key + "}}", val)
    return re.sub(r"\n{3,}", "\n\n", tpl)


def html_to_text(doc: str) -> str:
    doc = re.sub(r"(?is)<(script|style).*?</\1>", "", doc)
    doc = re.sub(r"(?i)<br\s*/?>", "\n", doc)
    doc = re.sub(r"(?i)</(p|div|h1|h2|article|header|li)>", "\n", doc)
    doc = re.sub(r"<[^>]+>", "", doc)
    doc = html.unescape(doc)
    doc = re.sub(r"[ \t]+\n", "\n", doc)
    return re.sub(r"\n{3,}", "\n\n", doc).strip() + "\n"


def find_chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def html_to_pdf(html_path, pdf_path, chrome):
    url = "file://" + os.path.abspath(html_path)
    cmd = [
        chrome, "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer", f"--print-to-pdf={os.path.abspath(pdf_path)}", url,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        proc.wait(timeout=90)
    except subprocess.TimeoutExpired:
        proc.kill()
    return os.path.exists(pdf_path)


def prompt(label, default=""):
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def main():
    parser = argparse.ArgumentParser(description="Generate a tailored cover letter.")
    parser.add_argument("-r", "--role", help="job title, e.g. 'Senior Full-Stack Developer'")
    parser.add_argument("-c", "--company", help="company name")
    parser.add_argument("-m", "--manager", help="hiring manager name (default: Hiring Team)")
    parser.add_argument("-s", "--salutation", help="full salutation line, overrides --manager")
    parser.add_argument("-f", "--flavor", choices=sorted(OPENERS), default="general",
                        help="opening paragraph style (default: general)")
    parser.add_argument("-x", "--custom", help="extra tailored paragraph to insert")
    parser.add_argument("--custom-file", help="read the extra paragraph from a file")
    parser.add_argument("--formats", default="pdf,txt,html",
                        help="comma list of pdf,txt,html (default: pdf,txt,html)")
    parser.add_argument("-o", "--outdir", default=os.path.join(HERE, "output"),
                        help="output directory (default: cover-letter/output)")
    parser.add_argument("--list-flavors", action="store_true", help="show opening styles and exit")
    args = parser.parse_args()

    if args.list_flavors:
        for name in sorted(OPENERS):
            print(f"  {name:11} {OPENERS[name][:70]}...")
        return

    role, company = args.role, args.company
    interactive = sys.stdin.isatty() and (not role or not company)
    if interactive:
        print("Fill in the cover-letter placeholders (Enter accepts defaults).\n")
        role = prompt("Role title", role or "Senior Full-Stack Developer")
        company = prompt("Company", company or "")
        if not company:
            print("Company is required.", file=sys.stderr)
            sys.exit(1)
        manager = args.manager or prompt("Hiring manager name", "Hiring Team")
    else:
        if not role or not company:
            parser.error("--role and --company are required (or run interactively in a terminal)")
        manager = args.manager or "Hiring Team"

    custom = args.custom or ""
    if args.custom_file:
        with open(args.custom_file, encoding="utf-8") as fh:
            custom = fh.read()

    salutation = args.salutation or (
        f"Dear {manager}," if manager and manager.lower() not in ("hiring team", "") else "Dear Hiring Team,"
    )
    opening = OPENERS[args.flavor].format(role=role, company=company)

    doc = build_html(role, company, salutation, opening, custom)

    os.makedirs(args.outdir, exist_ok=True)
    base = f"Paulo-Pinho-Cover-Letter-{slugify(company)}"
    formats = {f.strip().lower() for f in args.formats.split(",") if f.strip()}

    html_path = os.path.join(args.outdir, base + ".html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(doc)

    if "txt" in formats:
        with open(os.path.join(args.outdir, base + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(html_to_text(doc))

    pdf_note = ""
    if "pdf" in formats:
        chrome = find_chrome()
        pdf_path = os.path.join(args.outdir, base + ".pdf")
        if chrome and html_to_pdf(html_path, pdf_path, chrome):
            pdf_note = f"\n  PDF : {pdf_path}"
        else:
            pdf_note = "\n  PDF : skipped (Chrome not found; set $CHROME or use --formats txt,html)"

    print(f"Cover letter for “{role}” at “{company}” ({args.flavor}) written to:")
    print(f"  HTML: {html_path}{pdf_note}")


if __name__ == "__main__":
    main()
