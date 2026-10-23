"""Weekly lectures and slides must keep working after shared assets or links move."""

import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

COHORT = Path(__file__).resolve().parents[1]
PAGES = sorted([COHORT / "index.html", *COHORT.glob("week*/docs/*.html"), *COHORT.glob("foundations/docs/*.html")])
MARKDOWN_PAGES = sorted(
    [
        COHORT.parent / "README.md",
        COHORT.parent / "CONTRIBUTING.md",
        COHORT / "README.md",
        COHORT / "setup/README.md",
        COHORT / "foundations/README.md",
        COHORT / "infra/README.md",
        *COHORT.glob("week*/README.md"),
        *COHORT.glob("week*/lecture.md"),
    ]
)


class DeckAssets(HTMLParser):
    """Collect assets, links and ids without fetching anything or executing JavaScript."""

    def __init__(self) -> None:
        super().__init__()
        self.styles: list[str] = []
        self.scripts: list[str] = []
        self.links: list[str] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        if tag == "a" and attributes.get("href") is not None:
            self.links.append(attributes["href"])
        if tag == "link" and "stylesheet" in (attributes.get("rel") or "").split():
            self.styles.append(attributes.get("href") or "")
        if tag == "script" and "src" in attributes:
            self.scripts.append(attributes["src"] or "")


@pytest.mark.parametrize("page", PAGES, ids=lambda page: f"{page.parent.name}/{page.name}")
def test_weekly_presentation_assets_exist(page):
    parser = DeckAssets()
    parser.feed(page.read_text(encoding="utf-8"))
    assert parser.styles, f"{page}: no stylesheet linked"
    assert parser.scripts, f"{page}: no navigation script linked"
    for reference in [*parser.styles, *parser.scripts]:
        url = urlsplit(reference)
        assert not url.scheme and not url.netloc, f"{page}: shared assets must work offline: {reference}"
        assert url.path, f"{page}: empty asset reference"
        asset = (page.parent / unquote(url.path)).resolve()
        assert asset.is_relative_to(COHORT), f"{page}: asset is outside the cohort: {reference}"
        assert asset.is_file(), f"{page}: missing asset {reference}"


def test_course_home_links_every_week_and_its_core_materials():
    parser = DeckAssets()
    parser.feed((COHORT / "index.html").read_text(encoding="utf-8"))
    for week in sorted(COHORT.glob("week*")):
        if not (week / "README.md").exists():
            continue
        for filename in ("README.md", "docs/lecture.html", "docs/slides.html", "lab.ipynb"):
            assert f"{week.name}/{filename}" in parser.links, f"Course home omits {week.name}/{filename}"


@pytest.mark.parametrize("page", PAGES, ids=lambda page: f"{page.parent.name}/{page.name}")
def test_weekly_presentation_ids_are_unique(page):
    parser = DeckAssets()
    parser.feed(page.read_text(encoding="utf-8"))
    duplicates = [name for name, count in Counter(parser.ids).items() if count > 1]
    assert not duplicates, f"{page}: duplicate ids break navigation: {duplicates}"


@pytest.mark.parametrize("page", PAGES, ids=lambda page: f"{page.parent.name}/{page.name}")
def test_weekly_presentation_local_links_resolve(page):
    parser = DeckAssets()
    parser.feed(page.read_text(encoding="utf-8"))
    for reference in parser.links:
        url = urlsplit(reference)
        if url.scheme or url.netloc:
            continue
        target = (page.parent / unquote(url.path)).resolve() if url.path else page
        assert target.exists(), f"{page}: broken link {reference}"
        if url.fragment and target.suffix == ".html":
            linked_page = DeckAssets()
            linked_page.feed(target.read_text(encoding="utf-8"))
            assert unquote(url.fragment) in linked_page.ids, f"{page}: missing fragment {reference}"


@pytest.mark.parametrize("page", MARKDOWN_PAGES, ids=lambda page: str(page.relative_to(COHORT.parent)))
def test_course_markdown_local_link_targets_exist(page):
    """Check inline Markdown links, excluding illustrative links inside fenced code."""
    text = re.sub(r"^```[^\n]*\n.*?^```[^\n]*$", "", page.read_text(encoding="utf-8"), flags=re.MULTILINE | re.DOTALL)
    references = re.findall(r"\[[^\]\n]*\]\(([^\s)]+)\)", text)
    for reference in references:
        url = urlsplit(reference)
        if url.scheme or url.netloc or not url.path:
            continue
        target = (page.parent / unquote(url.path)).resolve()
        assert target.exists(), f"{page}: broken local link {reference}"
