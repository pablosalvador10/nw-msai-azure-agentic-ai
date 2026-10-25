"""The website's page shell: header, course sidebar, content, "on this page", previous / next.

Every page the site generates (home, course documents, folders, the score page) uses it, so the
course reads like one product. The lecture pages and slide decks keep their own design.
"""

import html
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import quote

from web.auth import User
from web.catalog import Catalog, Link, Week

ICONS = {
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "github": '<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 '
    "4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 "
    '4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>',
    "download": '<path d="M12 4v11m0 0-4-4m4 4 4-4M5 20h14"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "left": '<path d="m15 18-6-6 6-6"/>',
    "right": '<path d="m9 18 6-6-6-6"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "gauge": '<path d="M12 14l4-4"/><path d="M3.3 17a9 9 0 1 1 17.4 0"/>',
    "book": '<path d="M4 19.5V5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zm0 0A2 2 0 0 0 6 22h13"/>',
    "play": '<path d="m8 5 11 7-11 7z"/>',
}


def icon(name: str, size: int = 18) -> str:
    return (
        f'<svg class="icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


def esc(text: str) -> str:
    return html.escape(text, quote=True)


@dataclass
class Page:
    """What a page puts in the shell. Fields ending in _html are already escaped."""

    title: str
    path: str
    body_html: str
    kicker: str = ""
    title_html: str = ""
    lede: str = ""
    crumbs: list[tuple[str, str]] = field(default_factory=list)
    badges: list[str] = field(default_factory=list)
    actions: list[tuple[str, str, str]] = field(default_factory=list)  # (label, href, icon)
    toc: bool = True
    wide: bool = False
    mermaid: bool = False
    track: bool = True  # remembered as "continue where you left off"
    scripts: list[str] = field(default_factory=list)
    header: bool = True  # False: the body brings its own title (the home page)
    prose: bool = True  # False: the body is layout, not reading text


class Shell:
    def __init__(self, catalog: Catalog, mermaid_src: str) -> None:
        self.catalog = catalog
        self.mermaid_src = mermaid_src

    # ------------------------------------------------------------------ the page

    def render(self, page: Page, user: User | None) -> str:
        week = self.catalog.week_of(page.path)
        crumbs = "".join(
            f'<li><a href="{esc(href)}">{esc(label)}</a></li>' if href else f'<li aria-current="page">{esc(label)}</li>'
            for label, href in page.crumbs
        )
        badges = "".join(f'<span class="badge badge--{esc(b.lower().split()[0])}">{esc(b)}</span>' for b in page.badges)
        actions = "".join(
            f'<a class="btn btn--ghost btn--sm" href="{esc(href)}">{icon(ic, 16)}<span>{esc(label)}</span></a>'
            for label, href, ic in page.actions
        )
        spacer = '<span class="doc-meta__spacer"></span>' if badges else ""
        meta = f'<div class="doc-meta">{badges}{spacer}{actions}</div>' if badges or actions else ""
        parts = []
        if crumbs:
            parts.append(f'<nav class="breadcrumbs" aria-label="Breadcrumb"><ol>{crumbs}</ol></nav>')
        if page.kicker:
            parts.append(f'<p class="doc-kicker">{esc(page.kicker)}</p>')
        parts.append(f"<h1>{page.title_html or esc(page.title)}</h1>")
        if page.lede:
            parts.append(f'<p class="doc-lede">{esc(page.lede)}</p>')
        header = f'<header class="doc-header">{"".join(parts)}{meta}</header>' if page.header else ""
        prev, nxt = self.catalog.neighbours(page.path)
        pager = self._pager(prev, nxt)
        toc = '<aside class="doc-toc" aria-label="On this page"></aside>' if page.toc else ""
        classes = " ".join(
            c for c in ["doc", "doc--wide" if page.wide else "", "doc--notoc" if not page.toc else ""] if c
        )
        track = f' data-track="{esc(page.title)}"' if page.track else ""
        script = f' data-mermaid="{esc(self.mermaid_src)}"' if page.mermaid else ""
        title = (
            f"{page.title} · Agentic AI on Microsoft Foundry" if page.path != "/" else "Agentic AI on Microsoft Foundry"
        )
        week_label = f" · Week {week.number}" if week else ""
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(page.lede or page.title)}{esc(week_label)}">
<link rel="icon" href="/_site/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/_site/site.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
{self._header(user)}
<div class="site-body">
{self._sidebar(page.path)}
<div class="nav-backdrop" data-nav-close></div>
<main id="main" class="site-main" tabindex="-1">
<article class="{classes}"{track}>
{header}
<div class="{"prose" if page.prose else "page-body"}">
{page.body_html}
</div>
{pager}
</article>
{toc}
</main>
</div>
{self._search_dialog()}
<script src="/_site/site.js"{script} defer></script>
{"".join(f'<script src="{esc(src)}" defer></script>' for src in page.scripts)}
</body>
</html>
"""

    def _header(self, user: User | None) -> str:
        account = ""
        if user:
            avatar = f"https://avatars.githubusercontent.com/u/{int(user.id)}?s=64&v=4"
            account = (
                '<details class="account"><summary aria-label="Account">'
                f'<img class="avatar" src="{esc(avatar)}" alt="" width="30" height="30">'
                '</summary><div class="account__menu" role="menu">'
                f'<p class="account__who">Signed in as<br><b>@{esc(user.login)}</b></p>'
                '<a role="menuitem" href="/auth/logout">Sign out</a></div></details>'
            )
        return f"""<header class="site-header">
  <button class="icon-btn nav-toggle" type="button" aria-controls="site-nav" aria-expanded="false" aria-label="Open course navigation">{icon("menu", 20)}</button>
  <a class="brand" href="/"><span class="brand__mark" aria-hidden="true"></span><span class="brand__name">Agentic AI <span>on Microsoft Foundry</span></span></a>
  <button class="search-trigger" type="button" data-search-open aria-haspopup="dialog">{icon("search", 16)}<span class="search-trigger__label">Search the course</span><kbd>⌘K</kbd></button>
  <div class="site-header__actions">
    <a class="btn btn--primary btn--sm score-cta" href="/score/">{icon("gauge", 16)}<span>Score your service</span></a>
    {account}
  </div>
</header>"""

    def active_href(self, path: str) -> str | None:
        """The sidebar link that stands for a page: exact match, a week's notes, or the closest folder."""
        links = [link.href for week in self.catalog.weeks for link in week.links]
        links += [link.href for _, group in self.catalog.sections() for link in group]
        if path in links:
            return path
        if path == "/":
            return None
        if path.endswith("/") and f"{path}README.md" in links:
            return f"{path}README.md"
        if path.endswith("/lecture.md") and path.replace("/lecture.md", "/docs/lecture.html") in links:
            return path.replace("/lecture.md", "/docs/lecture.html")
        folders = [href for href in links if href.endswith("/") and href != "/" and path.startswith(href)]
        if folders:
            return max(folders, key=len)
        folder = path.rsplit("/", 1)[0]
        return f"{folder}/README.md" if folder and f"{folder}/README.md" in links else None

    def _sidebar(self, path: str) -> str:
        active = self.active_href(path)

        def item(link: Link) -> str:
            aria = ' aria-current="page"' if link.href == active else ""
            tag = f'<span class="nav-tag">{esc(link.tag)}</span>' if link.tag else ""
            return f'<li><a href="{esc(link.href)}"{aria}>{esc(link.label)}{tag}</a></li>'

        week_now = self.catalog.week_of(path)
        weeks = []
        for week in self.catalog.weeks:
            open_ = " open" if week is week_now else ""
            links = "".join(item(link) for link in week.links)
            weeks.append(
                f'<li><details class="nav-week"{open_}><summary><span class="nav-week__num">{week.number:02d}</span>'
                f'<span class="nav-week__title">{esc(week.title)}</span></summary><ul>{links}</ul></details></li>'
            )
        groups = [
            f'<ul class="nav-list"><li><a href="/"{" aria-current=page" if path == "/" else ""}>Course home</a></li></ul>'
        ]
        sections = self.catalog.sections()
        groups.append(self._group(*sections[0], item))
        groups.append(f'<p class="nav-heading">Weeks</p><ul class="nav-list nav-list--weeks">{"".join(weeks)}</ul>')
        for title, links in sections[1:]:
            groups.append(self._group(title, links, item))
        return f'<nav class="site-nav" id="site-nav" aria-label="Course">{"".join(groups)}</nav>'

    @staticmethod
    def _group(title: str, links: list[Link], item) -> str:
        return (
            f'<p class="nav-heading">{esc(title)}</p><ul class="nav-list">{"".join(item(link) for link in links)}</ul>'
        )

    @staticmethod
    def _pager(prev: Link | None, nxt: Link | None) -> str:
        if not prev and not nxt:
            return ""
        cells = []
        if prev:
            cells.append(
                f'<a class="pager__link pager__link--prev" href="{esc(prev.href)}"><span class="pager__dir">'
                f'{icon("left", 16)} Previous</span><span class="pager__label">{esc(prev.label)}</span></a>'
            )
        else:
            cells.append("<span></span>")
        if nxt:
            cells.append(
                f'<a class="pager__link pager__link--next" href="{esc(nxt.href)}"><span class="pager__dir">Next '
                f'{icon("right", 16)}</span><span class="pager__label">{esc(nxt.label)}</span></a>'
            )
        return f'<nav class="pager" aria-label="Previous and next">{"".join(cells)}</nav>'

    @staticmethod
    def _search_dialog() -> str:
        return f"""<dialog class="search" aria-label="Search the course">
  <form method="dialog" class="search__box" role="search">
    {icon("search", 18)}
    <input type="search" class="search__input" placeholder="Search lectures, labs, handbook, code…" autocomplete="off" spellcheck="false" aria-controls="search-results" aria-label="Search">
    <kbd>Esc</kbd>
  </form>
  <ol class="search__results" id="search-results" role="listbox" aria-label="Results"></ol>
  <p class="search__hint">Type to search every page of the course. ↑ ↓ to move, Enter to open.</p>
</dialog>"""

    # ------------------------------------------------------------------ the home page

    def home(self, today: date) -> Page:
        focus = self.catalog.focus(today)
        rows = "".join(self._week_row(w, self.catalog.status(w, today)) for w in self.catalog.weeks)
        start = [
            (
                "Setup",
                "/setup/README.md",
                "Tools, Azure, Terraform and your first deployment. Do it once, before Week 5.",
            ),
            (
                "Foundations",
                "/foundations/docs/primers.html",
                "Short primers on Terraform, FastAPI, containers, identity and the harness.",
            ),
            (
                "Your course agents",
                "/foundations/docs/agents.html",
                "Five Copilot agents that know this course. Start with FY26 Guide when you are stuck.",
            ),
        ]
        start_cards = "".join(
            f'<a class="card card--link" href="{esc(href)}"><h3>{esc(title)}</h3><p>{esc(text)}</p></a>'
            for title, href, text in start
        )
        reference = "".join(
            f'<li><a href="{esc(link.href)}">{icon("folder" if link.href.endswith("/") else "book", 16)}<span>{esc(link.label)}</span></a></li>'
            for link in self.catalog.sections()[2][1]
        )
        steps = [
            ("Learn", "Read the lecture, then follow the main lab."),
            ("Build", "Change one thing in the service in app/."),
            ("Test", "Score it on your laptop with the harness."),
            ("Deploy & submit", "Deploy, check the URL here, submit it."),
        ]
        step_items = "".join(
            f'<li><span class="step__num">{i}</span><div><b>{esc(t)}</b><p>{esc(d)}</p></div></li>'
            for i, (t, d) in enumerate(steps, 1)
        )
        body = f"""
<section class="home-hero">
  <div class="home-hero__copy">
    <p class="doc-kicker">Five sessions · one service</p>
    <h1>Build, deploy and harden an AI support service</h1>
    <p class="home-hero__lede">You improve one API for <b>Lakeshore Ride</b>, a fictional bike-share company. Each week adds a capability, you deploy it to Azure, and a harness scores it.</p>
    <div class="home-hero__actions">
      <a class="btn btn--primary" href="/setup/README.md">Start with setup {icon("right", 16)}</a>
      <a class="btn btn--ghost" href="/score/">{icon("gauge", 16)} Score your service</a>
    </div>
    <p class="continue" hidden><span>Continue where you left off:</span> <a href="#"></a></p>
  </div>
  {self._focus_card(focus, today) if focus else ""}
</section>

<section class="home-section" aria-labelledby="h-weeks">
  <div class="home-section__head"><h2 id="h-weeks">Sessions</h2><p>The service is cumulative: each week keeps the earlier routes working.</p></div>
  <ol class="week-rows">{rows}</ol>
</section>

<section class="home-section" aria-labelledby="h-loop">
  <div class="home-section__head"><h2 id="h-loop">How every week works</h2></div>
  <ol class="steps">{step_items}</ol>
</section>

<section class="home-section home-section--split">
  <div><div class="home-section__head"><h2 id="h-start">Get started</h2></div><div class="cards">{start_cards}</div></div>
  <div><div class="home-section__head"><h2 id="h-ref">Reference</h2></div><ul class="ref-list">{reference}</ul></div>
</section>
"""
        return Page(
            title="Course home", path="/", body_html=body, toc=False, wide=True, track=False, header=False, prose=False
        )

    def _focus_card(self, week: Week, today: date) -> str:
        status = self.catalog.status(week, today)
        label = {"now": "This week", "next": "Next session", "past": "Last session"}.get(status, "Session")
        when = f"{week.day:%a %b} {week.day.day}" if week.day else ""
        links = "".join(
            f'<li><a href="{esc(link.href)}">{esc(link.label)}</a></li>'
            for link in week.links
            if link.label in ("Lecture", "Slides", "Main lab")
        )
        return f"""<aside class="focus-card" aria-label="{esc(label)}">
    <p class="focus-card__label"><span class="dot"></span>{esc(label)}{f" · <time>{esc(when)}</time>" if when else ""}</p>
    <p class="focus-card__week">Week {week.number}</p>
    <h2>{esc(week.title)}</h2>
    <p>{esc(week.tagline)}</p>
    {f'<p class="focus-card__builds"><span>You build</span> <code>{esc(week.endpoint)}</code></p>' if week.endpoint else ""}
    <div class="focus-card__actions">
      <a class="btn btn--primary btn--sm" href="/{quote(week.folder)}/README.md">Open Week {week.number} {icon("right", 15)}</a>
      <ul class="text-links">{links}</ul>
    </div>
  </aside>"""

    def _week_row(self, week: Week, status: str) -> str:
        chip = {"now": "This week", "next": "Next", "past": "Done"}.get(status, "")
        when = f"{week.day:%b} {week.day.day}" if week.day else ""
        links = "".join(
            f'<li><a href="{esc(link.href)}">{esc(link.label)}{" (optional)" if link.tag else ""}</a></li>'
            for link in week.links
            if link.label != "Overview"
        )
        return f"""<li class="week-row week-row--{esc(status or "upcoming")}">
  <div class="week-row__num"><span>Week</span><b>{week.number:02d}</b></div>
  <div class="week-row__body">
    <h3><a href="/{quote(week.folder)}/README.md">{esc(week.title)}</a></h3>
    <p>{esc(week.tagline)}</p>
    <ul class="text-links">{links}</ul>
  </div>
  <div class="week-row__side">{f"<time>{esc(when)}</time>" if when else ""}{f'<span class="chip chip--{esc(status)}">{esc(chip)}</span>' if chip else ""}{f"<code>{esc(week.endpoint)}</code>" if week.endpoint else ""}</div>
</li>"""
