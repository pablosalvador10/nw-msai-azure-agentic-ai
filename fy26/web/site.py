"""What the website serves from the course folder, and how.

- The lecture pages, slide decks and Foundations pages (assets/ and every docs/ folder) are
  served as they are: they have their own design.
- Course documents (every README, lecture.md, notebook, handbook page and source file) are
  rendered into the website's shell, so the whole course reads and navigates as one site.
- Anything else (uv.lock, files outside the course folder) opens on GitHub.

Nothing secret can match: hidden files (.env), Terraform variables and state, reports/, the
website itself (web/) and caches are never published. The image build also keeps only files
tracked by git.
"""

import html
import os
import re
from fnmatch import fnmatchcase
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from web.render import LANGUAGES, Renderer, describe
from web.shell import Page

PUBLISHED_FILES: list[tuple[str, ...]] = []
PUBLISHED_DIRS = [("assets",), ("week*", "docs"), ("foundations", "docs")]
CONTENT_SUFFIXES = {".md", ".ipynb", ".py", ".tf", ".json", ".jsonl", ".toml", ".example"}
CONTENT_NAMES = {"Dockerfile"}
EXCLUDED_DIRS = {"web", "reports", "agent-file-memory", "build", "node_modules", "__pycache__"}

# Lecture pages keep their own design; one script adds "Score your service" to their materials bar.
LECTURE_SCRIPT = '\n<script src="/_site/lecture-addon.js"></script>\n'
TITLE = re.compile(r"<title>(.*?)</title>", re.DOTALL)
SECTION_H2 = re.compile(r'<section\b[^>]*\bid="([^"]+)"[^>]*>\s*(?:<[^h][^>]*>\s*)*<h2[^>]*>(.*?)</h2>', re.DOTALL)
HTML_KINDS = {
    "lecture.html": "Lecture",
    "slides.html": "Slides",
    "primers.html": "Primers",
    "agents.html": "Course agents",
}


def _parts(rel: str) -> tuple[str, ...] | None:
    """Path segments of a relative URL path, or None if it is unsafe (.., hidden files, backslashes)."""
    if "\\" in rel or "\x00" in rel:
        return None
    parts = PurePosixPath(rel).parts
    if not parts or any(p in (".", "..") or p.startswith(".") or p == "/" for p in parts):
        return None
    return parts


def is_published(rel: str) -> bool:
    """A browser page or asset, served unchanged."""
    parts = _parts(rel)
    if parts is None:
        return False
    if any(len(parts) == len(f) and all(map(fnmatchcase, parts, f)) for f in PUBLISHED_FILES):
        return True
    return any(len(parts) > len(d) and all(map(fnmatchcase, parts[: len(d)], d)) for d in PUBLISHED_DIRS)


def is_content(rel: str) -> bool:
    """A course document or source file, rendered as a page."""
    parts = _parts(rel)
    if parts is None or parts[0] in EXCLUDED_DIRS or "__pycache__" in parts or is_published(rel):
        return False
    return PurePosixPath(parts[-1]).suffix in CONTENT_SUFFIXES or parts[-1] in CONTENT_NAMES


def _walk(root: Path):
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in EXCLUDED_DIRS)
        yield Path(folder), files


def _plain(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def published_files(root: Path) -> list[str]:
    """Every file under root the site serves, as relative paths. The image build copies these (if tracked)."""
    root = root.resolve()
    found = []
    for folder, files in _walk(root):
        for name in files:
            rel = (folder / name).relative_to(root).as_posix()
            if is_published(rel) or is_content(rel):
                found.append(rel)
    return sorted(found)


class Site:
    def __init__(self, root: Path, repo: str, ref: str, course_dir: str) -> None:
        self.root = root.resolve()
        self.renderer = Renderer(self.root, repo, ref, course_dir.strip("/"))

    def _inside(self, rel: str) -> Path | None:
        path = (self.root / rel).resolve()
        return path if path.is_relative_to(self.root) and path.exists() else None

    def file(self, url_path: str) -> Path | None:
        """The published page or asset for a URL path, or None. Never leaves the site folder."""
        rel = url_path.strip("/")
        path = self._inside(rel) if rel and is_published(rel) else None
        return path if path and path.is_file() else None

    def content(self, url_path: str) -> Path | None:
        """The course document or source file for a URL path, or None."""
        rel = url_path.strip("/")
        path = self._inside(rel) if rel and is_content(rel) else None
        return path if path and path.is_file() else None

    def folder(self, url_path: str) -> Path | None:
        """A course folder with something to show, or None."""
        rel = url_path.strip("/")
        parts = _parts(rel) if rel else None
        if not parts or parts[0] in EXCLUDED_DIRS:
            return None
        path = self._inside(rel)
        return path if path and path.is_dir() and self._entries(path) else None

    def render(self, path: Path) -> str | None:
        """A published page with the website's additions, or None when the file is served unchanged."""
        rel = path.relative_to(self.root).as_posix()
        if path.name == "lecture.html" and PurePosixPath(rel).match("week*/docs/lecture.html"):
            return path.read_text(encoding="utf-8") + LECTURE_SCRIPT
        return None

    def document(self, path: Path) -> Page:
        """A course document or source file as a page."""
        return self.renderer.document(path.relative_to(self.root).as_posix(), path.stat().st_mtime_ns)

    def listing(self, path: Path) -> Page:
        """A folder as a page: its README, then what it contains."""
        rel = path.relative_to(self.root).as_posix()
        readme = path / "README.md"
        text = readme.read_text(encoding="utf-8") if readme.is_file() and is_content(f"{rel}/README.md") else None
        return self.renderer.directory(rel, self._entries(path), text)

    @cached_property
    def search_index(self) -> list[dict[str, Any]]:
        """Every page and its headings, for the search box: [{t: title, k: kind, u: url, h: [[heading, anchor]]}]."""
        items = []
        for rel in published_files(self.root):
            path, url = self.root / rel, "/" + quote(rel)
            name = PurePosixPath(rel).name
            if rel.endswith((".md", ".ipynb")):
                heads = self.renderer.headings(path.read_text(encoding="utf-8"), notebook=rel.endswith(".ipynb"))
                title = next((text for level, text, _ in heads if level == 1), name)
                _, kind = describe(rel)
                # lecture.md has the same sections as docs/lecture.html; search lists them once, on the lecture page.
                sections = [] if name == "lecture.md" else [[t, a] for lvl, t, a in heads if lvl in (2, 3)]
                items.append({"t": title, "k": kind, "u": url, "h": sections})
            elif rel.endswith(".html"):
                page = path.read_text(encoding="utf-8")
                match = TITLE.search(page)
                title = _plain(match.group(1)) if match else name
                kind = HTML_KINDS.get(name, "Page")
                if rel.startswith("week"):
                    kind = f"Week {int(rel[4:6])} · {kind}"
                elif rel.startswith("foundations/"):
                    kind = f"Foundations · {kind}"
                heads = [[_plain(text), anchor] for anchor, text in SECTION_H2.findall(page)]
                items.append({"t": title, "k": kind, "u": url, "h": heads[:60]})
            elif not rel.startswith(("assets/",)):
                kind = LANGUAGES.get(PurePosixPath(rel).suffix, "Source")
                items.append({"t": rel, "k": f"{kind} file", "u": url, "h": []})
        return items

    def _entries(self, path: Path) -> list[tuple[str, bool]]:
        """(name, is folder) for what a folder shows: pages, documents and folders that contain some."""
        entries = []
        for child in sorted(path.iterdir()):
            rel = child.relative_to(self.root).as_posix()
            if child.is_dir():
                if _parts(rel) and child.name not in EXCLUDED_DIRS and self._has_files(child):
                    entries.append((child.name, True))
            elif is_published(rel) or is_content(rel):
                entries.append((child.name, False))
        return entries

    def _has_files(self, path: Path) -> bool:
        for folder, files in _walk(path):
            base = folder.relative_to(self.root).as_posix()
            if any(is_published(f"{base}/{f}") or is_content(f"{base}/{f}") for f in files):
                return True
        return False

    def source_url(self, url_path: str) -> str | None:
        """GitHub URL for a course file the site does not show (uv.lock, .env.example)."""
        rel = url_path.strip("/")
        if not rel or _parts(rel) is None:
            return None
        return self.renderer.github_url(rel, folder=url_path.endswith("/"))
