"""Checks every careers site in config/sources.json, keeps only IT jobs in the
selected countries, tags each with an IT field, and writes site/data/jobs.json.

    python scraper/scrape.py                    # update site/data/jobs.json
    python scraper/scrape.py --dry-run          # just print what would be found
    python scraper/scrape.py --dry-run --only g42,ifs
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import country_name  # noqa: E402
from it_filter import FieldTagger, ITFilter  # noqa: E402
from jsearch import JSearchSource  # noqa: E402
from oracle_hcm import OracleHCMSource  # noqa: E402
from phenom import PhenomSource  # noqa: E402
from smartrecruiters import SmartRecruitersSource  # noqa: E402
from workday import WorkdaySource  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "config" / "sources.json"
OUTPUT_PATH = ROOT / "site" / "data" / "jobs.json"
MAX_DETAIL_FETCHES_PER_SOURCE = 150  # full descriptions are fetched once per new job
# If a careers site can't be checked, its last known jobs stay up for this long, then come off
# (we can no longer tell whether they are still open).
KEEP_FAILED_SOURCE_HOURS = 48

SOURCE_TYPES = {
    "oracle_hcm": OracleHCMSource,
    "smartrecruiters": SmartRecruitersSource,
    "workday": WorkdaySource,
    "phenom": PhenomSource,
    "jsearch": JSearchSource,
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def norm(text):
    return " ".join((text or "").lower().replace("&", "and").split())


def load_previous():
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": []}


def hours_since(iso, now_iso_str):
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.fromisoformat(now_iso_str.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return (now - then).total_seconds() / 3600


def keep_after_failure(prev_status, prev_jobs, run_time):
    """Which old jobs to keep for a source that failed this run, and its last good check time."""
    last_ok = (prev_status or {}).get("last_ok_at")
    if not last_ok and (prev_status or {}).get("ok"):
        last_ok = prev_status.get("checked_at")
    age = hours_since(last_ok, run_time) if last_ok else None
    if age is None or age > KEEP_FAILED_SOURCE_HOURS:
        return [], last_ok
    return prev_jobs, last_ok


def wanted_countries(cfg, default):
    """A source's own 'countries' list wins; "all" (or []) keeps every country."""
    countries = cfg.get("countries", default)
    if countries in ("all", None) or countries == []:
        return None
    return {c.upper() for c in countries}


def scrape_source(cfg, defaults, it_filter, tagger, previous_jobs, run_time, log, known=()):
    """Returns (jobs, stats) for one source. `known` holds (company, title) pairs already
    collected from earlier sources, so a job-board copy of the same opening is skipped."""
    countries = wanted_countries(cfg, defaults.get("countries"))
    # Sources that filter by country on the server (Workday) need the resolved list.
    scraper = SOURCE_TYPES[cfg["type"]]({**cfg, "countries": sorted(countries or [])})
    previous = {j["id"]: j for j in previous_jobs}
    jobs, skipped = [], []
    stats = {"listed": 0, "in_location": 0, "it": 0, "new": 0}
    details_fetched = 0

    for post in scraper.fetch():
        stats["listed"] += 1
        if countries is not None and not (set(post["countries"]) & countries):
            continue
        stats["in_location"] += 1
        title = post["title"]
        if not it_filter.is_it_job(title, post.get("categories", [])):
            skipped.append(title)
            continue
        company = post.get("company") or cfg["company"]
        if any(t == norm(title) and (c in norm(company) or norm(company) in c) for c, t in known):
            continue
        stats["it"] += 1

        job_id = f'{cfg["id"]}:{post["key"]}'
        old = previous.get(job_id)
        codes = [c for c in post["countries"] if countries is None or c in countries] or post["countries"]
        job = {
            "id": job_id,
            "source": cfg["id"],
            "company": company,
            "via": post.get("via", ""),
            "title": title,
            "field": tagger.tag(title, post.get("categories", [])),
            "country_code": codes[0] if codes else "",
            "country": country_name(codes[0]) if codes else "",
            "countries": [country_name(c) for c in codes],
            "locations": post["locations"],
            "workplace_type": post.get("workplace_type", ""),
            "category": next((c for c in post.get("categories", []) if c), ""),
            "posted_date": (post.get("posted_date") or "")[:10],
            "summary": post.get("summary", ""),
            "url": post["url"],
            "first_seen": old["first_seen"] if old else run_time,
            "description": post.get("description") or (old or {}).get("description", ""),
        }
        if old:
            # Keep the exact date and locations read from the detail page last time.
            if old.get("posted_date"):
                job["posted_date"] = old["posted_date"]
            if not job["locations"]:
                job["locations"] = old.get("locations", [])
        else:
            stats["new"] += 1
        if not job["description"] and hasattr(scraper, "details") and details_fetched < MAX_DETAIL_FETCHES_PER_SOURCE:
            details_fetched += 1
            try:
                extra = scraper.details(post)
                job.update({k: v for k, v in extra.items() if v})
                job["posted_date"] = job["posted_date"][:10]
            except Exception as e:
                log(f"    could not fetch details for {job_id}: {e}")
        jobs.append(job)

    keep_days = getattr(scraper, "keep_unlisted_days", 0)
    if keep_days:
        current = {j["id"] for j in jobs}
        cutoff = datetime.now(timezone.utc).timestamp() - keep_days * 86400
        for old in previous_jobs:
            try:
                seen_at = datetime.fromisoformat(old["first_seen"].replace("Z", "+00:00")).timestamp()
            except (KeyError, ValueError):
                continue
            if old["id"] not in current and seen_at >= cutoff:
                jobs.append(old)

    for title in skipped[:25]:
        log(f"    skipped (not IT): {title}")
    return jobs, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="don't write jobs.json")
    parser.add_argument("--strict", action="store_true", help="exit 1 if any source fails or lists no jobs at all")
    parser.add_argument("--only", help="comma-separated source ids to check")
    args = parser.parse_args()

    log = lambda msg: print(msg, flush=True)  # noqa: E731
    with open(SOURCES_PATH, encoding="utf-8") as f:
        config = json.load(f)
    defaults = config.get("defaults", {})
    sources = config["sources"]
    if args.only:
        wanted = set(args.only.split(","))
        sources = [s for s in sources if s["id"] in wanted]

    it_filter, tagger = ITFilter.load(), FieldTagger.load()
    previous = load_previous()
    run_time = now_iso()
    all_jobs, source_status, failed = [], [], False

    for cfg in sources:
        needs = getattr(SOURCE_TYPES[cfg["type"]], "needs_key", None)
        if needs and not os.environ.get(needs, "").strip():
            log(f"Skipping {cfg['company']}: set the {needs} secret to turn it on")
            continue
        log(f"Checking {cfg['company']} ...")
        prev_for_source = [j for j in previous.get("jobs", []) if j.get("source") == cfg["id"]]
        prev_status = next((s for s in previous.get("sources", []) if s.get("id") == cfg["id"]), None)
        status = {"id": cfg["id"], "company": cfg["company"], "careers_page": cfg.get("careers_page", ""), "checked_at": run_time}
        try:
            known = {(norm(j["company"]), norm(j["title"])) for j in all_jobs}
            jobs, stats = scrape_source(cfg, defaults, it_filter, tagger, prev_for_source, run_time, log, known)
            log(f"  {stats['listed']} open jobs, {stats['in_location']} in selected countries, "
                f"{stats['it']} IT jobs ({stats['new']} new)")
            for j in jobs[:20]:
                log(f"    + [{j['field']}] {j['title']} | {j['country']}")
            if stats["listed"] == 0:
                failed = True
            all_jobs.extend(jobs)
            source_status.append({**status, "ok": True, "last_ok_at": run_time, "it_jobs": len(jobs), **stats})
        except Exception as e:
            failed = True
            log(f"  FAILED: {e}")
            # Keep showing what we had for a short while, rather than wiping the company off the portal
            # over one bad check; after that, drop them since they may have been taken down.
            kept, last_ok = keep_after_failure(prev_status, prev_for_source, run_time)
            if prev_for_source and not kept:
                log(f"  removed {len(prev_for_source)} old jobs: not confirmed open since {last_ok or 'unknown'}")
            all_jobs.extend(kept)
            source_status.append({**status, "ok": False, "last_ok_at": last_ok, "error": str(e)[:300], "it_jobs": len(kept)})

    all_jobs.sort(key=lambda j: (j["first_seen"], j.get("posted_date", "")), reverse=True)
    output = {"updated_at": run_time, "fields": tagger.names, "sources": source_status, "jobs": all_jobs}

    if not args.dry_run:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=1)
            f.write("\n")
        log(f"Wrote {len(all_jobs)} jobs to {OUTPUT_PATH.relative_to(ROOT)}")

    if args.strict and failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
