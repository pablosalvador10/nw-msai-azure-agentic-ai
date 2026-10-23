"""What the website serves from the course folder, and how.

- Browser pages (the course home, assets/, and each docs/ folder) are served as they are.
- Course documents (every README, lecture.md, notebook, handbook page and source file) are
  rendered as pages in the lecture style, so the whole course reads on the site.
- Anything else (uv.lock, files outside the course folder) opens on GitHub.

Nothing secret can match: hidden files (.env), Terraform variables and state, reports/, the
website itself (web/) and caches are never published. The image build also keeps only files
tracked by git.
"""

import os
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from web.render import Renderer

PUBLISHED_FILES = [("index.html",)]
PUBLISHED_DIRS = [("assets",), ("week*", "docs"), ("foundations", "docs")]
CONTENT_SUFFIXES = {".md", ".ipynb", ".py", ".tf", ".json", ".jsonl", ".toml", ".example"}
CONTENT_NAMES = {"Dockerfile"}
EXCLUDED_DIRS = {"web", "reports", "agent-file-memory", "build", "node_modules", "__pycache__"}

# The website adds the online harness to two places, at serve time. Kept out of the repository's
# pages because they also work offline, where /score/ does not exist.
# 1. The course home: a link next to this anchor.
INDEX_MARKER = '<a href="#weeks">Already set up? Choose your week</a>'
INDEX_LINK = '\n        <a href="score/">Score your deployed service</a>'
# 2. Each lecture: a script that adds "Score your service" to the materials bar lecture.js builds.
LECTURE_SCRIPT = '\n<script src="/_site/site.js"></script>\n'


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
        rel = url_path.strip("/") or "index.html"
        path = self._inside(rel) if is_published(rel) else None
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
        if rel == "index.html":
            return path.read_text(encoding="utf-8").replace(INDEX_MARKER, INDEX_MARKER + INDEX_LINK, 1)
        if path.name == "lecture.html" and PurePosixPath(rel).match("week*/docs/lecture.html"):
            return path.read_text(encoding="utf-8") + LECTURE_SCRIPT
        return None

    def document(self, path: Path) -> str:
        """A course document or source file as a page."""
        return self.renderer.document(path.relative_to(self.root).as_posix(), path.stat().st_mtime_ns)

    def listing(self, path: Path) -> str:
        """A folder as a page: its README, then what it contains."""
        rel = path.relative_to(self.root).as_posix()
        readme = path / "README.md"
        text = readme.read_text(encoding="utf-8") if readme.is_file() and is_content(f"{rel}/README.md") else None
        return self.renderer.directory(rel, self._entries(path), text)

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
