# UAE IT Jobs

A small job portal that checks company career sites twice a day, keeps only the IT openings, and lists them in one place. Clicking **Apply** opens the job on the company's own careers site.

## How it works

- `config/sources.json` lists the companies to check.
- `scraper/scrape.py` reads each site's job API, keeps IT jobs (rules in `config/it_filter.json`), and writes `site/data/jobs.json`. Jobs first seen in the last 2 days get a **NEW** badge; jobs that are closed on the company site drop off.
- `.github/workflows/update-jobs.yml` runs the scraper at 06:00 and 18:00 UAE time, commits the new jobs file, and publishes `site/` to the `gh-pages` branch, which GitHub Pages serves.

## One-time setup

After the first **Update jobs** run creates the `gh-pages` branch, check **Settings → Pages**: Source should be **Deploy from a branch**, branch **gh-pages**, folder **/ (root)**. GitHub usually sets this automatically. The site appears at `https://<your-user>.github.io/<repo>/`.

## Adding a company

Most big employers use a hosted careers platform. Supported today:

| type | Careers URL looks like |
| --- | --- |
| `oracle_hcm` | `https://<host>/hcmUI/CandidateExperience/en/sites/<SITE>/jobs` |

Add an entry to `config/sources.json` with the host as `base_url` and `<SITE>` as `site_number`. Add `"countries": ["AE"]` to keep only UAE jobs from a global company. Other platforms (Workday, SuccessFactors, Greenhouse, …) need a small new scraper in `scraper/`.

## LinkedIn and other job boards

LinkedIn has no public jobs API and its terms forbid scraping, so LinkedIn (plus Indeed, Bayt, Glassdoor and others) comes in through the [JSearch API](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch), which reads Google for Jobs. To turn it on:

1. Sign up at RapidAPI, subscribe to JSearch's free Basic plan (200 requests a month), and copy your `X-RapidAPI-Key`.
2. In this repo: **Settings → Secrets and variables → Actions → New repository secret**, name `JSEARCH_API_KEY`, paste the key.

Without the secret, that source is simply skipped. The `jobboards` entry in `config/sources.json` sets the search queries; each query costs one request per run. Jobs found on a company's own careers site aren't listed a second time.

## Tuning what counts as IT

Edit `config/it_filter.json`: `include` words mark a title as IT, `exclude` words (sales, finance, HR…) override them.

## Running locally

```
python scraper/scrape.py --dry-run     # check every site, print what it finds
python scraper/scrape.py               # update site/data/jobs.json
python -m http.server -d site 8000     # open http://localhost:8000
python -m unittest discover -s scraper # tests
```

No dependencies beyond Python 3.10+.
