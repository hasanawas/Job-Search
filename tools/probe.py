"""Temporary: inspect career sites from GitHub's network (the dev sandbox can't reach them)."""
import json, re, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
      "Accept": "application/json,text/html,*/*", "Accept-Language": "en-US"}

def get(url, data=None, headers=None):
    h = dict(UA); h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, url, str(e)

# --- Sysco LABS SPA: find bundle and the URLs it calls
st, _, html = get("https://syscolabs.lk/careers")
print("SYSCO HTML:", html)
for src in re.findall(r'src="([^"]+\.js)"', html):
    url = src if src.startswith("http") else "https://syscolabs.lk" + src
    st, _, js = get(url)
    print("\nSYSCO BUNDLE", url, st, len(js))
    urls = sorted(set(re.findall(r'https?://[A-Za-z0-9._\-/]+', js)))
    print("URLS:", [u for u in urls if not any(x in u for x in ["w3.org", "reactjs", "fb.me", "github.com/", "mui.com"])][:80])
    for kw in ["career", "vacanc", "/api", "jobs"]:
        for m in list(re.finditer(kw, js))[:4]:
            print(f"  [{kw}]", repr(js[max(0, m.start()-120):m.start()+160]))

# --- Accenture Workday host
st, _, page = get("https://www.accenture.com/ae-en/careers/jobsearch")
print("\nACCENTURE workday:", sorted(set(re.findall(r'https://[a-z0-9.]*myworkdayjobs\.com/[A-Za-z0-9_/\-]*', page)))[:10])
for host in ["accenture.wd103.myworkdayjobs.com", "accenture.wd3.myworkdayjobs.com", "accenture.wd1.myworkdayjobs.com", "accenture.wd5.myworkdayjobs.com"]:
    body = json.dumps({"appliedFacets": {}, "limit": 2, "offset": 0, "searchText": ""}).encode()
    st, _, r = get(f"https://{host}/wday/cxs/accenture/AccentureCareers/jobs", data=body, headers={"Content-Type": "application/json"})
    print(f"\nWORKDAY {host}: {st} len={len(r)}")
    if st == 200:
        d = json.loads(r)
        print("total", d.get("total"), "postings", json.dumps(d.get("jobPostings"))[:800])
        for f in d.get("facets", []):
            vals = f.get("values", [])
            print("FACET", f.get("facetParameter"), f.get("descriptor"), len(vals))
            for v in vals:
                if "values" in v:
                    print("   SUB", v.get("facetParameter"), v.get("descriptor"), [(x.get("descriptor"), x.get("id"), x.get("count")) for x in v["values"]][:60])
                else:
                    if any(k in (v.get("descriptor") or "") for k in ["Arab", "Sri Lanka", "Saudi", "India"]):
                        print("   ", v.get("descriptor"), v.get("id"), v.get("count"))
        break

# --- Phenom job detail for G42
body = json.dumps({"lang": "en_global", "deviceType": "desktop", "country": "global", "pageName": "job", "ddoKey": "jobDetail",
                   "jobId": "3390", "siteType": "external"}).encode()
st, _, r = get("https://careers.g42.ai/widgets", data=body, headers={"Content-Type": "application/json"})
print("\nG42 DETAIL", st, r[:1500])
st, final, r = get("https://careers.g42.ai/global/en/job/3390")
print("\nG42 JOB PAGE", st, final, len(r), r.find("Senior Engineer"))

# --- SmartRecruiters detail
st, _, r = get("https://api.smartrecruiters.com/v1/companies/ifs1/postings/744000153246949")
print("\nSR DETAIL", st, r[:1200])
