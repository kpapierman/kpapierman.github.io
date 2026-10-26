#!/usr/bin/env python3
"""Check published portfolio navigation, attachments, and basic accessibility.

Uses only the Python standard library so it can run locally or in GitHub Actions.
Does not attempt to validate external services or interpret Tableau calculations.
"""
from __future__ import annotations
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "work.html", "projects.html", "experience.html",
         "pawsitive-preview.html", "weather-traffic-overview.html"]
ERRORS: list[str] = []


class Parse(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.refs = []
        self.h1 = 0
        self.main = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "main":
            self.main += 1
        if tag == "img" and "alt" not in a:
            ERRORS.append("Image missing alt text")
        if tag == "a" and a.get("target") == "_blank":
            if "noopener" not in (a.get("rel") or "").split():
                ERRORS.append("New-tab link missing noopener: " + str(a.get("href")))
        for attr in (("href",) if tag == "a" else ("src",) if tag in ("img", "script") else ()):
            if a.get(attr):
                self.refs.append(a[attr])


parsed = {}
for name in PAGES:
    path = ROOT / name
    assert path.is_file(), f"Missing page: {name}"
    parser = Parse()
    parser.feed(path.read_text(encoding="utf-8"))
    parsed[name] = parser
    if parser.h1 != 1 or parser.main != 1:
        ERRORS.append(f"{name}: expected one H1 and one main, got {parser.h1} and {parser.main}")
    if len(parser.ids) != len(set(parser.ids)):
        ERRORS.append(f"{name}: duplicate IDs")

internal = 0
for name, page in parsed.items():
    for ref in page.refs:
        parsed_url = urlsplit(ref)
        if parsed_url.scheme or parsed_url.netloc:
            continue
        dest = unquote(parsed_url.path)
        path = (ROOT / dest) if dest else (ROOT / name)
        if dest and not path.is_file():
            ERRORS.append(f"{name}: missing asset: {ref}")
            continue
        internal += 1
        fragment = unquote(parsed_url.fragment)
        if fragment and (dest.endswith(".html") or not dest):
            target = dest if dest else name
            if target not in parsed or fragment not in parsed[target].ids:
                ERRORS.append(f"{name}: broken anchor: {ref}")

homepage = (ROOT / "index.html").read_text()
projects = (ROOT / "projects.html").read_text()
preview = (ROOT / "pawsitive-preview.html").read_text()
assert 'href="pawsitive-preview.html"' in homepage, "Home Pawsitive Care card must open safe preview"
assert 'href="weather-traffic-overview.html"' in projects, "Weather project needs a real destination"
assert "healthcare-analytics-tableau-expanded.twbx" in projects, "Expanded healthcare download missing"
assert "us-border-crossings-interactive-dashboard.twbx" in projects, "Interactive dashboard download missing"
assert "connecticut-drug-mortality-dashboard.png" in projects, "Connecticut screenshot missing"
if any(term in preview.lower() for term in ("<form", "localstorage.", "fetch(", "xmlhttprequest", "/api/sync")):
    ERRORS.append("Read-only preview may contain state-changing or network behavior")

workbooks = sorted((ROOT / "projects/dashboards").glob("*.twbx"))
for p in workbooks:
    with zipfile.ZipFile(p) as z:
        corrupt = z.testzip()
        if corrupt:
            ERRORS.append(f"{p.name}: corrupt archive member {corrupt}")
        if not any(item.endswith(".twb") for item in z.namelist()):
            ERRORS.append(f"{p.name}: no Tableau XML workbook")
for p in (ROOT / "projects/notebooks").glob("*.ipynb"):
    with p.open(encoding="utf-8") as f:
        json.load(f)
for p in (ROOT / "projects/reports").glob("*.pdf"):
    if not p.read_bytes().startswith(b"%PDF"):
        ERRORS.append(f"Invalid PDF header: {p.name}")
if not (ROOT / "assets/connecticut/connecticut-drug-mortality-dashboard.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
    ERRORS.append("Connecticut screenshot is not a PNG")
if list((ROOT / ".github/portfolio-transfers").glob("**/*.b64")) if (ROOT / ".github/portfolio-transfers").exists() else []:
    ERRORS.append("Temporary workbook transfer chunks were not cleaned up")

print(f"Checked {len(PAGES)} pages, {internal} internal references, "
      f"{len(workbooks)} Tableau workbooks, notebook JSON, PDF headers, and the safe preview.")
for problem in ERRORS:
    print("FAIL:", problem)
if ERRORS:
    raise SystemExit(1)
print("PASS: all local portfolio checks")
