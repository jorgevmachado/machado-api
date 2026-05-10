from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET


SOURCE_REPORT = Path("coverage.xml")
SONAR_REPORT = Path("coverage-sonar.xml")
SONAR_SOURCE_PREFIX = "machado-api/app"


def main() -> None:
    tree = ET.parse(SOURCE_REPORT)
    root = tree.getroot()

    sources = root.find("sources")
    if sources is None:
        raise ValueError("Coverage report is missing the <sources> element")

    for child in list(sources):
        sources.remove(child)
    ET.SubElement(sources, "source").text = "."

    for class_node in root.findall(".//class"):
        filename = class_node.get("filename")
        if not filename:
            continue
        if filename.startswith(f"{SONAR_SOURCE_PREFIX}/"):
            continue
        class_node.set("filename", f"{SONAR_SOURCE_PREFIX}/{filename}")

    tree.write(SONAR_REPORT, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
