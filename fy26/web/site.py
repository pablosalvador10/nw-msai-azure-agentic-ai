"""Which course files the website serves, and where every other course link goes.

Only browser pages are published: the course home, shared assets, and each week's docs/ folder
(lecture and slides). Links inside those pages to notebooks, READMEs or code open the same
file on GitHub, where students with access to the course repository can read it.
"""

from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from urllib.parse import quote

PUBLISHED_FILES = [("index.html",)]
PUBLISHED_DIRS = [("assets",), ("week*", "docs"), ("foundations", "docs")]

# The website adds the online harness to two places, at serve time. Kept out of the repository's
# pages because they also work offline, where /score/ does not exist.
# 1. The course home: a link next to this anchor.
INDEX_MARKER = '<a href="#weeks">Already set up? Choose your week</a>'
INDEX_LINK = '\n        <a href="score/">Score your deployed service</a>'
# 2. Each lecture: a script that adds "Score your service" to the materials bar lecture.js builds.
LECTURE_SCRIPT = '\n<script src="/score/site.js"></script>\n'


def _parts(rel: str) -> tuple[str, ...] | None:
    """Path segments of a relative URL path, or None if it is unsafe (.., hidden files, backslashes)."""
    if "\\" in rel or "\x00" in rel:
        return None
    parts = PurePosixPath(rel).parts
    if not parts or any(p in (".", "..") or p.startswith(".") or p == "/" for p in parts):
        return None
    return parts


def is_published(rel: str) -> bool:
    parts = _parts(rel)
    if parts is None:
        return False
    if any(len(parts) == len(f) and all(map(fnmatchcase, parts, f)) for f in PUBLISHED_FILES):
        return True
    return any(len(parts) > len(d) and all(map(fnmatchcase, parts[: len(d)], d)) for d in PUBLISHED_DIRS)


def published_files(root: Path) -> list[str]:
    """Every file under root the site serves, as relative paths. The image build copies exactly these."""
    root = root.resolve()
    patterns = ["/".join(f) for f in PUBLISHED_FILES] + ["/".join(d) + "/**/*" for d in PUBLISHED_DIRS]
    found = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            rel = path.relative_to(root).as_posix()
            if path.is_file() and "__pycache__" not in rel and is_published(rel):
                found.add(rel)
    return sorted(found)


class Site:
    def __init__(self, root: Path, repo: str, ref: str, course_dir: str) -> None:
        self.root = root.resolve()
        self.source_base = f"https://github.com/{repo}"
        self.ref = ref
        self.course_dir = course_dir.strip("/")

    def file(self, url_path: str) -> Path | None:
        """The published file for a URL path, or None. Never leaves the site folder."""
        rel = url_path.strip("/") or "index.html"
        if not is_published(rel):
            return None
        path = (self.root / rel).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            return None
        return path

    def source_url(self, url_path: str) -> str | None:
        """GitHub URL for a course file the site does not publish (lab.ipynb, README.md, app/*.py)."""
        rel = url_path.strip("/")
        if not rel or _parts(rel) is None:
            return None
        kind, slash = ("tree", "/") if url_path.endswith("/") else ("blob", "")
        return f"{self.source_base}/{kind}/{quote(self.ref)}/{quote(self.course_dir)}/{quote(rel)}{slash}"

    def render(self, path: Path) -> str | None:
        """The page with the website's additions, or None when the file is served unchanged."""
        rel = path.relative_to(self.root).as_posix()
        if rel == "index.html":
            return path.read_text(encoding="utf-8").replace(INDEX_MARKER, INDEX_MARKER + INDEX_LINK, 1)
        if path.name == "lecture.html" and PurePosixPath(rel).match("week*/docs/lecture.html"):
            return path.read_text(encoding="utf-8") + LECTURE_SCRIPT
        return None
