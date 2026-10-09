"""Small careers sites and recruiters that only publish HTML listing pages: SALT, Charterhouse, Guildhall and
NYU Abu Dhabi. Each reads its listing pages for titles and links, and each new job's page for its full advert."""

import html
import http.cookiejar
import json
import re
import time
import urllib.request

from common import country_code, country_name, fetch_text, html_to_text, relative_posted_date

MAX_PAGES = 15
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def _place(location, default_country):
    """('Dubai', 'AE') -> ('Dubai, United Arab Emirates', 'AE')."""
    parts = [p.strip() for p in location.split(",") if p.strip()]
    code = next((c for c in (country_code(p) for p in reversed(parts)) if c), "") or default_country
    name = country_name(code) if code else ""
    if name and not any(p.lower() == name.lower() for p in parts):
        parts.append(name)
    return ", ".join(parts), code


def _posting(key, title, url, location, default_country, summary="", posted_date="", workplace_type="", categories=()):
    place, code = _place(location, default_country)
    return {
        "key": key,
        "title": title,
        "locations": [place] if place else [],
        "countries": [code] if code else [],
        "workplace_type": workplace_type,
        "categories": list(categories),
        "posted_date": posted_date,
        "summary": summary[:300],
        "url": url,
    }


def jsonld_job(page):
    """The JobPosting JSON-LD block on a job page, if it has one."""
    for raw in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            data = json.loads(raw.strip(), strict=False)
        except ValueError:
            continue
        for item in data.get("@graph", [data]) if isinstance(data, dict) else data:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return {}


def _jsonld_details(url):
    data = jsonld_job(fetch_text(url))
    if not data:
        return {}
    out = {"description": html_to_text(data.get("description"))}
    if data.get("datePosted"):
        out["posted_date"] = data["datePosted"][:10]
    return out


class _Paged:
    """Walks numbered listing pages until one adds no new jobs."""

    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")
        self.list_path = cfg.get("list_path", "")
        self.default_country = (cfg.get("country") or "").upper()

    def page_url(self, n):
        raise NotImplementedError

    def parse(self, page):
        raise NotImplementedError

    def get_page(self, n):
        return fetch_text(self.page_url(n))

    def fetch(self):
        seen = set()
        for n in range(1, MAX_PAGES + 1):
            fresh = 0
            for p in self.parse(self.get_page(n)):
                if p["key"] not in seen:
                    seen.add(p["key"])
                    fresh += 1
                    yield p
            if not fresh or not self.has_next(n):
                break
            time.sleep(0.5)

    def has_next(self, n):
        return True

    def details(self, posting):
        return _jsonld_details(posting["url"])


class SaltSource(_Paged):
    """SALT recruitment (welovesalt.com). Config: base_url, list_path (a job category such as
    "/job-category/united-arab-emirates/technology-united-arab-emirates"), country."""

    def page_url(self, n):
        return f"{self.base}{self.list_path}" + (f"/page/{n}" if n > 1 else "")

    def get_page(self, n):
        page = fetch_text(self.page_url(n))
        self._next = f"{self.list_path}/page/{n + 1}" in page
        return page

    def has_next(self, n):
        return self._next

    def parse(self, page):
        for item in page.split('<li class="job-item">')[1:]:
            link = re.search(r'class="job-item__title">\s*<a href="([^"]+/jobs/[^"]+?-(\d+))/?"[^>]*>(.*?)</a>', item, re.S)
            if not link:
                continue
            highlights = re.findall(r'<li class="highlights__item">(.*?)</li>', item, re.S)
            location = _text(highlights[0]) if highlights else ""
            categories = [_text(c) for c in re.findall(r"<a[^>]*>(.*?)</a>", highlights[1], re.S)] if len(highlights) > 1 else []
            details = [_text(d) for d in re.findall(r'<li class="job-item__detail">(.*?)</li>', item, re.S)]
            workplace = next((d for d in details if d.lower() in ("remote", "hybrid", "on-site", "onsite")), "")
            yield _posting(link.group(2), _text(link.group(3)), link.group(1), location, self.default_country,
                           workplace_type=workplace, categories=categories)

    def details(self, posting):
        page = fetch_text(posting["url"])
        data = jsonld_job(page)
        if data:
            return {"description": html_to_text(data.get("description")), "posted_date": (data.get("datePosted") or "")[:10]}
        m = re.search(r'<div class="[^"]*job-(?:description|details?|content)[^"]*">(.*?)</div>\s*</div>', page, re.S)
        return {"description": html_to_text(m.group(1))} if m else {}


class CharterhouseSource(_Paged):
    """Charterhouse Middle East (charterhouseme.ae). Config: base_url, list_path (e.g. "/jobs/information-technology"),
    country."""

    def page_url(self, n):
        return f"{self.base}{self.list_path}" + (f"?page={n}" if n > 1 else "")

    def get_page(self, n):
        page = fetch_text(self.page_url(n))
        self._next = bool(re.search(r"class='results-nav'.*?rel=\"next\"", page, re.S))
        return page

    def has_next(self, n):
        return self._next

    def parse(self, page):
        for item in re.findall(r"<li class='job-result-item'[^>]*>(.*?)<div class='extra-job-links'>", page, re.S):
            link = re.search(r'<div class=\'job-title\'>\s*<a href="(/job/[^"]+?-(\d+))"[^>]*>(.*?)</a>', item, re.S)
            if not link:
                continue
            field = lambda cls: _text((re.search(rf"<li class='{cls}'>(.*?)</li>", item, re.S) or [None, ""])[1])  # noqa: E731
            summary = _text((re.search(r"<p class='job-description'>(.*?)</p>", item, re.S) or [None, ""])[1]).lstrip("​")
            yield _posting(link.group(2), _text(link.group(3)), f"{self.base}{link.group(1)}", field("results-job-location"),
                           self.default_country, summary=summary, posted_date=relative_posted_date(field("results-posted-at")))

    def details(self, posting):
        page = fetch_text(posting["url"])
        data = jsonld_job(page)
        if data:
            return {"description": html_to_text(data.get("description"))}
        m = re.search(r"<div class='job-description'>(.*?)</div>", page, re.S) or re.search(r'class="job-description">(.*?)</div>', page, re.S)
        return {"description": html_to_text(m.group(1))} if m else {}


class GuildhallSource(_Paged):
    """Guildhall executive search (guildhall.agency). Config: base_url, list_path ("/jobs"), country."""

    def page_url(self, n):
        return f"{self.base}{self.list_path}/" + (f"page/{n}/" if n > 1 else "")

    def __init__(self, cfg):
        super().__init__(cfg)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def _get(self, url):
        return fetch_text(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/html,*/*"}, opener=self.opener)

    def get_page(self, n):
        # The first visit gets a bot-check page (HTTP 202) that sets a cookie; the next request goes through.
        for attempt in range(3):
            page = self._get(self.page_url(n))
            if 'class="ghj-card"' in page or (n > 1 and "ghj-" in page) or attempt == 2:
                return page
            time.sleep(3)

    def parse(self, page):
        for card in re.findall(r'<article class="ghj-card">(.*?)</article>', page, re.S):
            link = re.search(r'<h3>\s*<a href="([^"]+/jobs/([^"/]+)/?)"[^>]*>(.*?)</a>', card, re.S)
            if not link:
                continue
            location = _text((re.search(r'<span class="ghj-meta-location">(.*?)</span>', card, re.S) or [None, ""])[1])
            tag = _text((re.search(r'<span class="ghj-card-tag">(.*?)</span>', card, re.S) or [None, ""])[1])
            summary = _text((re.search(r"</div>\s*<p>(.*?)</p>", card, re.S) or [None, ""])[1])
            yield _posting(link.group(2), _text(link.group(3)), link.group(1), location, self.default_country,
                           summary=summary, categories=[tag] if tag else [])

    def details(self, posting):
        data = jsonld_job(self._get(posting["url"]))
        return {"description": html_to_text(data.get("description"))} if data else {}


class NyuadSource:
    """NYU Abu Dhabi staff vacancies. Config: base_url ("https://nyuad.nyu.edu"), list_paths (listing pages)."""

    def __init__(self, cfg):
        self.base = cfg["base_url"].rstrip("/")
        self.list_paths = cfg.get("list_paths") or ["/en/about/careers/administration-staff.html"]

    def fetch(self):
        seen = set()
        for path in self.list_paths:
            page = fetch_text(f"{self.base}{path}")
            for href, title in re.findall(r'<a href="(/en/about/careers/[\w-]+/\d{4}/\d{2}/[^"]+\.html)"[^>]*>(.*?)</a>', page, re.S):
                if href in seen:
                    continue
                seen.add(href)
                yield _posting(href.rsplit("/", 1)[-1][:-5], _text(title), f"{self.base}{href}", "Abu Dhabi", "AE")
            time.sleep(0.5)

    def details(self, posting):
        page = fetch_text(posting["url"])
        body = page[page.find("<h1"):]
        sections = re.findall(r"<section>\s*<h4>(.*?)</h4>(.*?)</section>", body, re.S)
        text = "\n\n".join(f"{_text(h)}\n{html_to_text(s)}" for h, s in sections)
        return {"description": text}
