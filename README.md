# IT Careers Hub

A job portal that checks company career sites twice a day, keeps only the IT openings in the UAE, the Gulf and Sri Lanka, tags each one with an IT field (DevOps & Cloud, Software Development, Cybersecurity, and so on), and lists them in one place with country, company and field filters. Clicking **Apply** opens the job on the company's own careers site.

## How it works

- `config/sources.json` lists the companies to check.
- `scraper/scrape.py` reads each site's job API, keeps IT jobs (rules in `config/it_filter.json`), and writes `site/data/jobs.json`. Jobs first seen in the last 2 days get a **NEW** badge; jobs that are closed on the company site drop off.
- `.github/workflows/update-jobs.yml` runs the scraper at 06:00 and 18:00 UAE time, commits the new jobs file, and publishes `site/` to the `gh-pages` branch, which GitHub Pages serves.

## One-time setup

After the first **Update jobs** run creates the `gh-pages` branch, check **Settings → Pages**: Source should be **Deploy from a branch**, branch **gh-pages**, folder **/ (root)**. GitHub usually sets this automatically. The site appears at `https://<your-user>.github.io/<repo>/`.

## Adding a company

Most big employers use a hosted careers platform. Supported today:

| type | Careers URL looks like | Example |
| --- | --- | --- |
| `oracle_hcm` | `https://<host>/hcmUI/CandidateExperience/en/sites/<site_number>/jobs` | e&, Fortinet |
| `smartrecruiters` | `https://careers.smartrecruiters.com/<company_identifier>` | IFS |
| `workday` | `https://<tenant>.wdN.myworkdayjobs.com/<site>` or `https://wdN.myworkdaysite.com/recruiting/<tenant>/<site>` | Accenture, Sysco LABS |
| `phenom` | `https://<host>/global/en/search-results` | G42 |

Add an entry to `config/sources.json` (copy a similar one). A company's own career page often links to one of these platforms behind its "Search jobs" button. Other platforms need a small new scraper in `scraper/`.

## Countries and IT fields

`defaults.countries` in `config/sources.json` sets which countries are kept (UAE, Saudi Arabia, Qatar, Kuwait, Bahrain, Oman and Sri Lanka today). A source can override it with its own `countries` list, or `"all"`. IT fields are defined in `config/it_filter.json` under `fields`: each job gets the first field whose keywords match its title.

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
