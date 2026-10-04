"""Checks every careers site in config/sources.json, keeps only IT jobs,
and writes site/data/jobs.json for the portal.

    python scraper/scrape.py              # update site/data/jobs.json
    python scraper/scrape.py --dry-run    # just print what would be found
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from it_filter import ITFilter  # noqa: E402
from oracle_hcm import OracleHCMSource  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "config" / "sources.json"
OUTPUT_PATH = ROOT / "site" / "data" / "jobs.json"
MAX_DETAIL_FETCHES_PER_SOURCE = 200  # full descriptions are fetched once per new job

SOURCE_TYPES = {"oracle_hcm": OracleHCMSource}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_previous():
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"jobs": []}


def scrape_source(cfg, it_filter, previous_jobs, run_time, log):
    scraper = SOURCE_TYPES[cfg["type"]](cfg)
    previous = {j["id"]: j for j in previous_jobs}
    jobs, stats = [], {"listed": 0, "in_location": 0, "it": 0, "new": 0}
    skipped = []
    details_fetched = 0

    for req in scraper.list_jobs():
        stats["listed"] += 1
        if not scraper.in_selected_countries(req):
            continue
        stats["in_location"] += 1
        title = (req.get("Title") or "").strip()
        if not it_filter.is_it_job(title, scraper.categories(req)):
            skipped.append(title)
            continue
        stats["it"] += 1

        job_id = f'{cfg["id"]}:{req["Id"]}'
        old = previous.get(job_id)
        job = {
            "id": job_id,
            "source": cfg["id"],
            "company": cfg["company"],
            "title": title,
            "locations": scraper.locations(req),
            "workplace_type": req.get("WorkplaceType") or "",
            "category": req.get("JobFamily") or req.get("JobFunction") or "",
            "posted_date": req.get("PostedDate") or "",
            "summary": (req.get("ShortDescriptionStr") or "").strip(),
            "url": scraper.job_url(req["Id"]),
            "first_seen": old["first_seen"] if old else run_time,
            "description": old.get("description", "") if old else "",
        }
        if not old:
            stats["new"] += 1
        if not job["description"] and details_fetched < MAX_DETAIL_FETCHES_PER_SOURCE:
            details_fetched += 1
            try:
                job["description"] = scraper.description_from_details(scraper.details(req["Id"]))
            except Exception as e:
                log(f"    could not fetch details for {job_id}: {e}")
        jobs.append(job)
    for title in skipped[:30]:
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
        sources = json.load(f)["sources"]
    if args.only:
        wanted = set(args.only.split(","))
        sources = [s for s in sources if s["id"] in wanted]

    it_filter = ITFilter.load()
    previous = load_previous()
    run_time = now_iso()
    all_jobs, source_status, failed = [], [], False

    for cfg in sources:
        log(f"Checking {cfg['company']} ...")
        prev_for_source = [j for j in previous.get("jobs", []) if j.get("source") == cfg["id"]]
        try:
            jobs, stats = scrape_source(cfg, it_filter, prev_for_source, run_time, log)
            log(f"  {stats['listed']} open jobs, {stats['in_location']} in selected locations, "
                f"{stats['it']} IT jobs ({stats['new']} new)")
            for j in jobs[:15]:
                log(f"    - {j['title']} | {', '.join(j['locations'][:2])}")
            if stats["listed"] == 0:
                failed = True
            all_jobs.extend(jobs)
            source_status.append({"id": cfg["id"], "company": cfg["company"], "careers_page": cfg.get("careers_page", ""),
                                  "ok": True, "checked_at": run_time, "it_jobs": len(jobs), **stats})
        except Exception as e:
            failed = True
            log(f"  FAILED: {e}")
            # Keep showing what we had, rather than wiping the company off the portal.
            all_jobs.extend(prev_for_source)
            source_status.append({"id": cfg["id"], "company": cfg["company"], "careers_page": cfg.get("careers_page", ""),
                                  "ok": False, "checked_at": run_time, "error": str(e)[:300],
                                  "it_jobs": len(prev_for_source)})

    all_jobs.sort(key=lambda j: (j["first_seen"], j["posted_date"]), reverse=True)
    output = {"updated_at": run_time, "sources": source_status, "jobs": all_jobs}

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
