"""Course Markdown, notebooks and source files as pages of the website.

The site serves the repository's own files: a README, lecture.md, a lab notebook or app/domain.py
render here exactly as they are in the course folder, with links that stay on the site. Notebooks
are shown read-only (they are committed without outputs); students run them in VS Code.
"""

import html
import json
import posixpath
import re
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlsplit

from markdown_it import MarkdownIt

from web.hints import WEEK_DIRS, WEEK_TITLES
from web.shell import Page

MERMAID = "/_site/mermaid-12.2.0.min.js"
H1 = re.compile(r'<h1 id="[^"]*">(.*?)</h1>\s*', re.S)
TAGS = re.compile(r"<[^>]+>")
LANGUAGES = {".py": "Python", ".tf": "Terraform", ".json": "JSON", ".jsonl": "JSON Lines", ".toml": "TOML"}
FOLDER_TITLES = {
    "app": "Service code",
    "app/data": "Service data",
    "app/data/handbook": "Lakeshore Ride handbook",
    "app/services": "Service routes",
    "harness": "Harness",
    "infra": "Infrastructure",
    "tests": "Tests",
    "setup": "Setup",
    "foundations": "Foundations",
}


def slugify(text: str) -> str:
    """GitHub-style heading anchor: lowercase, punctuation dropped, spaces become hyphens."""
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def describe(rel: str) -> tuple[list[tuple[str, str]], str]:
    """(breadcrumbs above the title, kicker) for a course file. The page itself is the last crumb."""
    parts = PurePosixPath(rel).parts
    name = parts[-1]
    week = next((w for w, folder in WEEK_DIRS.items() if parts[0] == folder), None)
    home = [("Course home", "/")]
    kinds = {
        "README.md": "Overview",
        "lecture.md": "Lecture notes (Markdown)",
        "lab.ipynb": "Main lab",
        "deep-dive.ipynb": "Optional deep dive",
        "setup.ipynb": "Setup notebook",
    }
    kind = kinds.get(name, "Notebook" if name.endswith(".ipynb") else "Notes" if name.endswith(".md") else "Source")
    if week:
        return [*home, (f"Week {week} · {WEEK_TITLES[week]}", f"/{parts[0]}/README.md")], f"Week {week} · {kind}"
    if parts[0] in ("setup", "foundations") and len(parts) == 2:
        section = parts[0].capitalize()
        return [*home, (section, f"/{parts[0]}/README.md")], f"{section} · {kind}"
    if rel.startswith("app/data/handbook/"):
        return [*home, ("Lakeshore Ride handbook", "/app/data/handbook/")], "Lakeshore Ride handbook"
    if len(parts) == 1:
        return home, "Course guide" if name.endswith(".md") else "Source"
    folders = ["/".join(parts[: i + 1]) for i in range(len(parts) - 1)]
    crumbs = [*home] + [(FOLDER_TITLES.get(f, PurePosixPath(f).name), f"/{f}/") for f in folders]
    return crumbs, FOLDER_TITLES.get(parts[0], kind)


class Renderer:
    def __init__(self, root: Path, repo: str, ref: str, course_dir: str) -> None:
        self.root = root
        self.repo = repo
        self.ref = ref
        self.course_dir = course_dir
        self.md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
        # markdown-it binds each rule to its renderer, so the rules are plain functions that call back here.
        rules = {
            "heading_open": self._heading_open,
            "link_open": self._link_open,
            "fence": self._fence,
            "code_block": self._fence,
        }
        for name, method in rules.items():
            self.md.add_render_rule(name, lambda renderer, *args, _m=method: _m(renderer, *args))
        self.md.add_render_rule("table_open", lambda renderer, *args: '<div class="table-wrap"><table>\n')
        self.md.add_render_rule("table_close", lambda renderer, *args: "</table></div>\n")

    # ------------------------------------------------------------------ links and pieces

    def github_url(self, rel: str, *, folder: bool = False) -> str:
        """The file (or folder) on GitHub. rel is relative to the course folder."""
        repo_path = posixpath.normpath(posixpath.join(self.course_dir, rel)) if rel else self.course_dir
        kind = "tree" if folder else "blob"
        return f"https://github.com/{self.repo}/{kind}/{quote(self.ref)}/{quote(repo_path)}{'/' if folder else ''}"

    def resolve(self, href: str, rel: str) -> str:
        """A link written relative to a course file, as a site path (or GitHub, if it leaves the course folder)."""
        parts = urlsplit(href)
        if parts.scheme or parts.netloc or not parts.path or parts.path.startswith("/"):
            return href
        folder = parts.path.endswith("/")
        target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), parts.path))
        fragment = f"#{parts.fragment}" if parts.fragment else ""
        if target == "..":
            return href
        if target.startswith("../") or any(p.startswith(".") for p in PurePosixPath(target).parts if p != "."):
            # Outside the course folder (.github/) or hidden (.env.example): the site never serves these.
            repo_path = posixpath.normpath(posixpath.join(self.course_dir, target))
            if repo_path.startswith(".."):
                return href
            kind = "tree" if folder else "blob"
            return f"https://github.com/{self.repo}/{kind}/{quote(self.ref)}/{quote(repo_path)}{fragment}"
        path = "/" if target == "." else f"/{quote(target)}{'/' if folder else ''}"
        query = f"?{parts.query}" if parts.query else ""
        return f"{path}{query}{fragment}"

    def _heading_open(self, renderer: Any, tokens: list, idx: int, options: Any, env: dict) -> str:
        inline = tokens[idx + 1]
        text = "".join(c.content for c in (inline.children or []) if c.type in ("text", "code_inline"))
        slug = slugify(text) or "section"
        seen = env.setdefault("slugs", {})
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        tokens[idx].attrSet("id", slug if count == 0 else f"{slug}-{count}")
        return renderer.renderToken(tokens, idx, options, env)

    def _link_open(self, renderer: Any, tokens: list, idx: int, options: Any, env: dict) -> str:
        href = tokens[idx].attrGet("href")
        if isinstance(href, str):
            tokens[idx].attrSet("href", self.resolve(href, env.get("rel", "")))
        return renderer.renderToken(tokens, idx, options, env)

    def _fence(self, renderer: Any, tokens: list, idx: int, options: Any, env: dict) -> str:
        token = tokens[idx]
        lang = (token.info or "").strip().split(" ")[0].lower()
        code = html.escape(token.content.rstrip("\n"), quote=False)
        if lang == "mermaid":
            env["mermaid"] = True
            return f'<div class="diagram"><pre class="mermaid">{code}</pre></div>\n'
        plain = " data-plain" if lang in ("text", "txt", "output") else ""
        return f'<pre class="code"{plain}><code>{code}</code></pre>\n'

    def markdown(self, text: str, env: dict) -> str:
        return self.md.render(text, env)

    # ------------------------------------------------------------------ whole pages

    @lru_cache(maxsize=512)  # noqa: B019 - one Renderer per app; keyed by mtime so edits show up
    def document(self, rel: str, mtime_ns: int) -> Page:
        """The page for a Markdown file, a notebook or a source file."""
        path = self.root / rel
        name = PurePosixPath(rel).name
        text = path.read_text(encoding="utf-8")
        env: dict[str, Any] = {"rel": rel}
        crumbs, kicker = describe(rel)
        badges: list[str] = []
        actions = [("View on GitHub", self.github_url(rel), "github")]
        lede = ""

        if rel.endswith(".md"):
            body = self.markdown(text, env)
        elif rel.endswith(".ipynb"):
            body = self._notebook(text, env)
            badges.append({"lab.ipynb": "Required", "deep-dive.ipynb": "Optional"}.get(name, "Notebook"))
            actions.insert(0, ("Download notebook", f"/{quote(rel)}?download=1", "download"))
            body = (
                '<div class="callout callout--info"><p><b>Read-only copy.</b> Run it in VS Code: open '
                f"<code>fy26/{html.escape(rel)}</code> in your clone of the course repository and pick the "
                '<code>fy26/.venv</code> kernel (<a href="/setup/README.md">Setup</a> shows how).</p></div>\n' + body
            )
        else:
            language = LANGUAGES.get(PurePosixPath(rel).suffix, "Source")
            badges.append(language if name != "Dockerfile" else "Dockerfile")
            lede = f"fy26/{rel}, as committed to the course repository."
            body = f'<pre class="code code--file" data-lang="{html.escape(language)}"><code>{html.escape(text, quote=False)}</code></pre>\n'

        if name == "lecture.md":
            folder = quote(PurePosixPath(rel).parent.as_posix())
            badges.append("Markdown source")
            actions.insert(0, ("Lecture page", f"/{folder}/docs/lecture.html", "book"))

        title_html, body = self._split_title(body)
        title_html = title_html or html.escape(name)
        return Page(
            title=html.unescape(TAGS.sub("", title_html)).strip(),
            title_html=title_html,
            path=f"/{rel}",
            body_html=body,
            kicker=kicker,
            lede=lede,
            crumbs=crumbs,
            badges=badges,
            actions=actions,
            toc=rel.endswith((".md", ".ipynb")),
            wide=not rel.endswith((".md", ".ipynb")),
            mermaid=bool(env.get("mermaid")),
        )

    def directory(self, rel: str, entries: list[tuple[str, bool]], readme: str | None) -> Page:
        """A folder: its README (when it has one) followed by the list of what it contains."""
        parts = PurePosixPath(rel).parts
        week = next((w for w, folder in WEEK_DIRS.items() if parts[0] == folder), None)
        crumbs = [("Course home", "/")] + [
            (FOLDER_TITLES.get("/".join(parts[: i + 1]), p), "/" + "/".join(parts[: i + 1]) + "/")
            for i, p in enumerate(parts[:-1])
        ]
        rows = []
        for entry, is_dir in entries:
            title = "" if is_dir else self._title_of(self.root / rel / entry)
            label = (
                f'<span class="file-list__name">{html.escape(title)}</span>'
                f'<span class="file-list__file">{html.escape(entry)}</span>'
                if title
                else f'<span class="file-list__name file-list__name--mono">{html.escape(entry)}{"/" if is_dir else ""}</span>'
            )
            rows.append(
                f'<li><a href="/{quote(posixpath.join(rel, entry))}{"/" if is_dir else ""}">'
                f'<span class="file-list__icon file-list__icon--{"dir" if is_dir else "file"}" aria-hidden="true"></span>'
                f"{label}</a></li>"
            )
        listing = f'<h2 id="in-this-folder">In this folder</h2>\n<ul class="file-list">{"".join(rows)}</ul>\n'
        env: dict[str, Any] = {"rel": f"{rel}/README.md"}
        title_html, body = self._split_title(self.markdown(readme, env) if readme else "")
        name = FOLDER_TITLES.get(rel, f"{parts[-1]}/")
        return Page(
            title=html.unescape(TAGS.sub("", title_html)).strip() if title_html else name,
            title_html=title_html or html.escape(name),
            path=f"/{rel}/",
            body_html=body + listing,
            kicker=f"Week {week} · Folder" if week else f"fy26/{rel}/",
            crumbs=crumbs,
            actions=[("View on GitHub", self.github_url(rel, folder=True), "github")],
            mermaid=bool(env.get("mermaid")),
        )

    def _title_of(self, path: Path) -> str:
        """The first '# ' heading of a Markdown file, for friendlier folder listings."""
        if path.suffix != ".md":
            return ""
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("# "):
                        return line[2:].strip()
        except OSError:
            pass
        return ""

    def headings(self, text: str, notebook: bool = False) -> list[tuple[int, str, str]]:
        """(level, text, anchor) of every heading, with the same anchors the rendered page uses."""
        sources = [text]
        if notebook:
            cells = json.loads(text).get("cells", [])
            sources = [
                "".join(c["source"]) if isinstance(c.get("source"), list) else str(c.get("source", ""))
                for c in cells
                if c.get("cell_type") == "markdown"
            ]
        seen: dict[str, int] = {}
        found = []
        for source in sources:
            tokens = self.md.parse(source)
            for i, token in enumerate(tokens):
                if token.type != "heading_open":
                    continue
                inline = tokens[i + 1]
                label = "".join(c.content for c in (inline.children or []) if c.type in ("text", "code_inline"))
                slug = slugify(label) or "section"
                count = seen.get(slug, 0)
                seen[slug] = count + 1
                found.append((int(token.tag[1]), label, slug if count == 0 else f"{slug}-{count}"))
        return found

    def _notebook(self, raw: str, env: dict) -> str:
        cells = json.loads(raw).get("cells", [])
        out = []
        for cell in cells:
            source = cell.get("source", "")
            source = "".join(source) if isinstance(source, list) else str(source)
            if cell.get("cell_type") == "markdown":
                out.append(self.markdown(source, env))
            elif cell.get("cell_type") == "code" and source.strip():
                out.append(
                    f'<pre class="code nb-cell" data-lang="Python"><code>{html.escape(source, quote=False)}</code></pre>\n'
                )
        return "".join(out)

    @staticmethod
    def _split_title(body: str) -> tuple[str | None, str]:
        match = H1.search(body)
        if not match:
            return None, body
        return match.group(1), body[: match.start()] + body[match.end() :]
