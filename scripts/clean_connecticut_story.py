#!/usr/bin/env python3
"""Minimally remove misplaced orange callouts from the Connecticut Tableau story.

Run against the portfolio's existing, already-hosted Tableau workbook.
Do not change author-written story text, data or layout settings.
"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as ET
import hashlib

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "projects/dashboards/connecticut-drug-mortality-tableau.twbx"
target = ROOT / "projects/dashboards/connecticut-drug-related-mortality-tableau-revised.twbx"

with ZipFile(source) as z:
    names = z.namelist()
    source_xml = next(n for n in names if n.lower().endswith(".twb"))
    root = ET.fromstring(z.read(source_xml), parser=ET.XMLParser(remove_blank_text=False))
    story = root.xpath("./dashboards/dashboard[@type='storyboard']")
    assert len(story) == 1, "Expected one Connecticut story"
    story = story[0]

    rules = story.xpath("./style/style-rule[@element='story-description']")
    assert len(rules) == 1, "Expected story-description formatting"
    orange = [node for node in rules[0] if node.tag == "format" and
              node.get("id") in ("story-description_19", "story-description_21") and
              node.get("attr") in ("border-width", "border-style", "border-color")]
    assert len(orange) == 6, "Expected exactly six orange-box styling rules"
    for node in orange:
        rules[0].remove(node)

    charts = root.xpath("./worksheets/worksheet[@name='Accidental Drug-Related Deaths Due To Drug']")
    assert len(charts) == 1, "Cannot locate original drug chart"
    table = charts[0].find("table")
    annotation = table.find("annotations")
    assert annotation is not None and "Highest Deaths Due To Drug" in "".join(annotation.itertext())
    table.remove(annotation)
    ann_styles = table.xpath("./style/style-rule[@element='annotation']")
    assert len(ann_styles) == 1
    ann_styles[0].getparent().remove(ann_styles[0])
    overrides = story.xpath(".//capturedDeltas/worksheet[@name='Accidental Drug-Related Deaths Due To Drug']")
    assert len(overrides) == 1
    overrides[0].getparent().remove(overrides[0])

    captions = {"Beginning": "Overview", "Middle": "Drug Comparisons", "End": "Opioid Patterns"}
    for point in story.xpath(".//story-points/story-point"):
        if point.get("caption") in captions:
            point.set("caption", captions[point.get("caption")])

    assert len(root.xpath("./worksheets/worksheet")) == 8
    assert len(story.xpath(".//story-points/story-point")) == 3
    assert all(d.find("size").get("sizing-mode") == "automatic"
               for d in root.xpath("./dashboards/dashboard"))
    assert not charts[0].xpath(".//encodings/color")
    modified = ET.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False)

    with ZipFile(target, "w") as out:
        for item in z.infolist():
            out.writestr(item, modified if item.filename == source_xml else z.read(item.filename))

with ZipFile(source) as old, ZipFile(target) as new:
    assert new.testzip() is None
    for name in old.namelist():
        if name != source_xml:
            assert hashlib.sha256(old.read(name)).digest() == hashlib.sha256(new.read(name)).digest()
    check = ET.fromstring(new.read(source_xml))
    assert not check.xpath("./dashboards/dashboard[@type='storyboard']//style-rule[@element='story-description']/format[@id='story-description_19' or @id='story-description_21']")
    assert not check.xpath("./worksheets/worksheet[@name='Accidental Drug-Related Deaths Due To Drug']//annotation")
print("Verified clean Tableau download:", target)
