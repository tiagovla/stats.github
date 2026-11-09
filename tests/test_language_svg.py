import xml.etree.ElementTree as ET

import pytest

from github_stats.language_svg import LANGUAGE_COLORS, render_language_svg


NS = {"s": "http://www.w3.org/2000/svg"}


def test_language_chart_uses_actual_percentages_accessible_labels_and_github_colors():
    svg = render_language_svg([("Python", 72.5), ("JavaScript", 0.3), ("Unlisted", 27.2)])
    root = ET.fromstring(svg)
    fills = [node.attrib.get("fill") for node in root.findall(".//s:rect", NS)]

    assert root.attrib["role"] == "img"
    assert root.find("s:title", NS).text == "GitHub language composition"
    assert "LANGUAGE CODE COMPOSITION" in "".join(root.itertext())
    assert "GITHUB STATS" not in "".join(root.itertext())
    assert "Python: 72.5%" in root.find("s:desc", NS).text
    assert "shared 0 to 100 percent scale" in root.find("s:desc", NS).text
    assert LANGUAGE_COLORS["Python"] in fills
    assert LANGUAGE_COLORS["JavaScript"] in fills
    assert "#8b9aa8" in fills
    percentage_labels = [t.text for t in root.findall(".//s:text", NS) if t.text and t.text.endswith("%") and t.text not in ("0%", "25%", "50%", "75%", "100%")]
    assert percentage_labels == ["72.5%", "27.2%", "0.3%"]
    assert "font-family:ui-monospace" in root.find("s:style", NS).text
    assert "<title>" in svg and "https://" not in svg


def test_empty_and_long_language_names_are_presented_without_overflowing_label_column():
    empty = ET.fromstring(render_language_svg([]))
    assert empty.find("s:desc", NS).text == "No language data is available."
    assert "No language data available" in "".join(empty.itertext())

    root = ET.fromstring(render_language_svg([("A Very Long Language Name That Needs Room", 0.01)]))
    label = root.find(".//s:text[s:title]", NS)
    assert label.text.endswith("…")
    assert label.find("s:title", NS).text == "A Very Long Language Name That Needs Room"
    assert any(t.text == "<0.1%" for t in root.findall(".//s:text", NS))


def test_renderer_sorts_all_bars_descending():
    root = ET.fromstring(render_language_svg([("Other", 20), ("Rust", 15), ("Python", 65)]))
    labels = [node.text for node in root.findall(".//s:text", NS) if node.text in ("Python", "Rust", "Other")]
    assert labels == ["Python", "Other", "Rust"]


def test_light_theme_has_static_valid_svg_and_unknown_theme_rejected():
    root = ET.fromstring(render_language_svg([("Rust", 100)], "light"))
    assert root.find("s:rect", NS).attrib["fill"] == "#f8fcfd"
    assert "<animate" not in ET.tostring(root, encoding="unicode")
    with pytest.raises(ValueError, match="unknown theme"):
        render_language_svg([], "blue")


@pytest.mark.parametrize("value", [-0.1, 100.1, float("nan"), float("inf"), True, "4"])
def test_invalid_percentages_are_rejected(value):
    with pytest.raises(ValueError, match="invalid percentage"):
        render_language_svg([("Python", value)])


def test_invalid_language_records_are_rejected():
    with pytest.raises(ValueError, match="pairs"):
        render_language_svg([("Python", 20, "extra")])
    with pytest.raises(ValueError, match="non-empty"):
        render_language_svg([(" ", 20)])
