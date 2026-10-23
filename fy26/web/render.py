"""Course Markdown, notebooks and source files as web pages, in the same style as the lectures.

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

MERMAID = "/_site/mermaid-12.2.0.min.js"
H1 = re.compile(r'<h1 id="[^"]*">(.*?)</h1>\s*', re.S)
H2 = re.compile(r'<h2 id="([^"]*)">')
TAGS = re.compile(r"<[^>]+>")


def slugify(text: str) -> str:
    """GitHub-style heading anchor: lowercase, punctuation dropped, spaces become hyphens."""
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def describe(rel: str) -> tuple[str, str]:
    """(topbar subtitle, eyebrow) for a course file."""
    parts = PurePosixPath(rel).parts
    name = parts[-1]
    week = next((w for w, folder in WEEK_DIRS.items() if parts[0] == folder), None)
    if week:
        crumb = f"Week {week} · {WEEK_TITLES[week]}"
    elif parts[0] == "setup":
        crumb = "Setup"
    elif parts[0] == "foundations":
        crumb = "Foundations"
    elif rel.startswith("app/data/handbook/"):
        crumb = "Lakeshore Ride handbook"
    elif len(parts) == 1 and name.endswith(".md"):
        crumb = "Course guide"
    else:
        crumb = "Course files"
    eyebrows = {
        "README.md": "Overview",
        "lecture.md": "Lecture notes · Markdown source",
        "lab.ipynb": "Main lab · notebook",
        "deep-dive.ipynb": "Optional deep dive · notebook",
        "setup.ipynb": "Setup notebook",
    }
    if name in eyebrows:
        return crumb, eyebrows[name]
    if parts[0] == "foundations" and name.endswith(".ipynb"):
        return crumb, "Foundations primer · notebook"
    if rel.startswith("app/data/handbook/"):
        return crumb, "Handbook page"
    if name.endswith(".md"):
        return crumb, "Notes"
    return crumb, "Source file"


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
    def document(self, rel: str, mtime_ns: int) -> str:
        """The page for a Markdown file, a notebook or a source file."""
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        env: dict[str, Any] = {"rel": rel}
        crumb, eyebrow = describe(rel)
        notes: list[str] = []
        actions = [f'<a class="button button--quiet" href="{html.escape(self.github_url(rel))}">View on GitHub</a>']

        if rel.endswith(".md"):
            body = self.markdown(text, env)
        elif rel.endswith(".ipynb"):
            body = self._notebook(text, env)
            actions.insert(0, f'<a class="button" href="/{quote(rel)}?download=1">Download notebook</a>')
            notes.append(
                "<p><strong>Read-only copy.</strong> To run this notebook, open "
                f"<code>fy26/{html.escape(rel)}</code> in VS Code from your clone of the course repository and "
                'select the Python environment in <code>fy26/.venv</code> (see <a href="/setup/README.md">Setup</a>).</p>'
            )
        else:
            body = f'<pre class="code"><code>{html.escape(text, quote=False)}</code></pre>\n'
            notes.append(
                f"<p>Source file <code>fy26/{html.escape(rel)}</code>, as committed to the course repository.</p>"
            )

        if PurePosixPath(rel).name == "lecture.md":
            folder = PurePosixPath(rel).parent.as_posix()
            notes.append(
                f'<p>The same lecture, formatted for reading: <a href="/{quote(folder)}/docs/lecture.html">lecture page</a>'
                f' · <a href="/{quote(folder)}/docs/slides.html">slides</a>.</p>'
            )

        title_html, body = self._split_title(body)
        title_html = title_html or html.escape(PurePosixPath(rel).name)
        return self._page(
            title_html=title_html,
            crumb=crumb,
            eyebrow=eyebrow,
            notes=notes,
            actions=actions,
            body=self._sections(body),
            mermaid=bool(env.get("mermaid")),
        )

    def directory(self, rel: str, entries: list[tuple[str, bool]], readme: str | None) -> str:
        """A folder: its README (when it has one) followed by the list of what it contains."""
        crumb, _ = describe(f"{rel}/README.md")
        items = "".join(
            f'<li><a href="/{quote(posixpath.join(rel, name))}{"/" if is_dir else ""}">'
            f"{html.escape(name)}{'/' if is_dir else ''}</a></li>"
            for name, is_dir in entries
        )
        listing = f'<section id="files"><h2>In this folder</h2><ul class="file-list">{items}</ul></section>'
        env: dict[str, Any] = {"rel": f"{rel}/README.md"}
        title_html, body = self._split_title(self.markdown(readme, env) if readme else "")
        return self._page(
            title_html=title_html or html.escape(f"{rel}/"),
            crumb=crumb,
            eyebrow="Folder",
            notes=[],
            actions=[
                f'<a class="button button--quiet" href="{html.escape(self.github_url(rel, folder=True))}">View on GitHub</a>'
            ],
            body=self._sections(body) + listing,
            mermaid=bool(env.get("mermaid")),
        )

    def _notebook(self, raw: str, env: dict) -> str:
        cells = json.loads(raw).get("cells", [])
        out = []
        for cell in cells:
            source = cell.get("source", "")
            source = "".join(source) if isinstance(source, list) else str(source)
            if cell.get("cell_type") == "markdown":
                out.append(self.markdown(source, env))
            elif cell.get("cell_type") == "code" and source.strip():
                out.append(f'<pre class="code nb-cell"><code>{html.escape(source, quote=False)}</code></pre>\n')
        return "".join(out)

    @staticmethod
    def _split_title(body: str) -> tuple[str | None, str]:
        match = H1.search(body)
        if not match:
            return None, body
        return match.group(1), body[: match.start()] + body[match.end() :]

    @staticmethod
    def _sections(body: str) -> str:
        """Wrap each h2 and what follows in <section id>, which the lecture script turns into contents links."""
        chunks = re.split(r'(?=<h2 id=")', body)
        out = [f'<div class="doc-intro">{chunks[0]}</div>' if chunks[0].strip() else ""]
        for chunk in chunks[1:]:
            match = H2.match(chunk)
            section_id = match.group(1) if match else ""
            out.append(f'<section id="{section_id}">{H2.sub("<h2>", chunk, count=1)}</section>')
        return "".join(out)

    def _page(
        self,
        *,
        title_html: str,
        crumb: str,
        eyebrow: str,
        notes: list[str],
        actions: list[str],
        body: str,
        mermaid: bool,
    ) -> str:
        title_text = html.escape(html.unescape(TAGS.sub("", title_html)).strip())
        note_html = f'<div class="callout">{"".join(notes)}</div>' if notes else ""
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_text} · {html.escape(crumb)} · Agentic AI on Microsoft Foundry</title>
<link rel="stylesheet" href="/assets/lecture.css">
<link rel="stylesheet" href="/_site/site.css">
</head>
<body class="doc-page">
<a class="skip" href="#content">Skip to the document</a>
<div id="progress" aria-hidden="true"></div>
<header class="topbar"><div class="topbar__inner">
  <span class="brand-copy"><b>Agentic AI on Microsoft Foundry</b><span>{html.escape(crumb)}</span></span>
  <div class="topbar__right">
    {"".join(actions)}
    <button class="button" id="print" type="button">Print / PDF</button>
  </div>
</div></header>
<div class="layout">
<nav class="toc" aria-label="Contents"></nav>
<main id="content" tabindex="-1">
<header class="hero">
  <p class="eyebrow">{html.escape(eyebrow)}</p>
  <h1>{title_html}</h1>
  {note_html}
</header>
<div class="doc-body">
{body}
</div>
</main>
</div>
<button id="back-to-top" type="button" aria-label="Back to top">↑</button>
<script src="/assets/lecture.js"></script>
<script src="/_site/site.js"{' data-mermaid="' + MERMAID + '"' if mermaid else ""}></script>
</body>
</html>
"""
