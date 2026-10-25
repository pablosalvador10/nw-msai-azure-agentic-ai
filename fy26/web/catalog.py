"""The course map the website is built around: weeks, navigation, reading order.

Week titles, dates and taglines are read from the course files themselves (each week's README
and lecture page), so the site never drifts from the content.
"""

import html
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from web.hints import WEEK_DIRS, WEEK_TITLES

MONTHS = {
    m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)
}
TAGS = re.compile(r"<[^>]+>")
WEEK = timedelta(days=7)


@dataclass(frozen=True)
class Link:
    label: str
    href: str
    tag: str = ""  # a short note shown next to the label: "optional", "new tab"


@dataclass(frozen=True)
class Week:
    number: int
    folder: str
    title: str
    day: date | None
    tagline: str
    builds: str  # what the student builds, e.g. "POST /v1/ask"

    @property
    def endpoint(self) -> str:
        """The route this week builds, when it is one (Week 10 hardens every route instead)."""
        return self.builds if re.match(r"(GET|POST|PUT|PATCH|DELETE) /", self.builds) else ""

    @property
    def links(self) -> list[Link]:
        f = self.folder
        return [
            Link("Overview", f"/{f}/README.md"),
            Link("Lecture", f"/{f}/docs/lecture.html"),
            Link("Slides", f"/{f}/docs/slides.html"),
            Link("Main lab", f"/{f}/lab.ipynb"),
            Link("Deep dive", f"/{f}/deep-dive.ipynb", "optional"),
        ]


@dataclass
class Catalog:
    weeks: list[Week] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path, year: int | None = None) -> "Catalog":
        year = year or date.today().year
        weeks = []
        for number, folder in WEEK_DIRS.items():
            readme = _read(root / folder / "README.md")
            lecture = _read(root / folder / "docs" / "lecture.html")
            when = re.search(r"\*\*Date:\*\*\s*([A-Z][a-z]{2})\w*\s+(\d{1,2})", readme)
            day = date(year, MONTHS[when.group(1)], int(when.group(2))) if when and when.group(1) in MONTHS else None
            tagline = re.search(r'<span class="hero-subtitle">(.*?)</span>\s*</h1>', lecture, re.S)
            builds = re.search(r"<td>You build</td>\s*<td>(.*?)</td>", lecture, re.S)
            weeks.append(
                Week(
                    number=number,
                    folder=folder,
                    title=WEEK_TITLES[number],
                    day=day,
                    tagline=_text(tagline.group(1)) if tagline else "",
                    builds=_text(builds.group(1)).split(":")[0].strip() if builds else "",
                )
            )
        return cls(weeks)

    def week_of(self, path: str) -> Week | None:
        return next((w for w in self.weeks if path.startswith(f"/{w.folder}/")), None)

    def status(self, week: Week, today: date) -> str:
        """'now' in the seven days from the session, 'past' after them, 'next' for the first one ahead."""
        if week.day is None:
            return ""
        if week.day <= today < week.day + WEEK:
            return "now"
        if today >= week.day + WEEK:
            return "past"
        if any(w.day and w.day <= today < w.day + WEEK for w in self.weeks):
            return "upcoming"
        first = next((w for w in self.weeks if w.day and w.day > today), None)
        return "next" if first is week else "upcoming"

    def focus(self, today: date) -> Week | None:
        """The week to put first: this week's session, else the next one, else the last."""
        for wanted in ("now", "next"):
            found = next((w for w in self.weeks if self.status(w, today) == wanted), None)
            if found:
                return found
        return self.weeks[-1] if self.weeks else None

    def sections(self) -> list[tuple[str, list[Link]]]:
        """The sidebar, minus the weeks (rendered as groups)."""
        return [
            (
                "Get started",
                [
                    Link("Setup", "/setup/README.md"),
                    Link("Foundations", "/foundations/docs/primers.html"),
                    Link("Foundations notebooks", "/foundations/README.md"),
                    Link("Your course agents", "/foundations/docs/agents.html"),
                ],
            ),
            ("Tools", [Link("Score your service", "/score/")]),
            (
                "Reference",
                [
                    Link("Course guide", "/README.md"),
                    Link("Lakeshore Ride handbook", "/app/data/handbook/"),
                    Link("Service code", "/app/"),
                    Link("Harness", "/harness/"),
                    Link("Infrastructure", "/infra/"),
                ],
            ),
        ]

    def sequence(self) -> list[Link]:
        """Reading order for previous / next at the bottom of each page. Slides are for class, not reading."""
        order = [
            Link("Setup", "/setup/README.md"),
            Link("Setup notebook", "/setup/setup.ipynb"),
            Link("Foundations", "/foundations/docs/primers.html"),
            Link("Foundations notebooks", "/foundations/README.md"),
        ]
        for week in self.weeks:
            for link in week.links:
                if link.label != "Slides":
                    order.append(Link(f"Week {week.number} · {link.label}", link.href))
        return order

    def neighbours(self, path: str) -> tuple[Link | None, Link | None]:
        order = self.sequence()
        hrefs = [link.href for link in order]
        if path.endswith("/") and f"{path}README.md" in hrefs:
            path = f"{path}README.md"
        if path not in hrefs:
            return None, None
        i = hrefs.index(path)
        return (order[i - 1] if i > 0 else None), (order[i + 1] if i + 1 < len(order) else None)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _text(fragment: str) -> str:
    return " ".join(html.unescape(TAGS.sub("", fragment)).split())
