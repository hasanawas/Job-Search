"""Temporary: inspect career sites from GitHub's network (the dev sandbox can't reach them)."""
import json, re, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
      "Accept": "text/html,application/json,*/*", "Accept-Language": "en"}
ATS = r"(lever\.co|greenhouse\.io|workable\.com|smartrecruiters\.com|myworkdayjobs\.com|successfactors|phenom|icims|taleo|oraclecloud|bamboohr|zohorecruit|teamtailor|recruitee|ashbyhq|jobvite|eightfold|hrmos|darwinbox|keka|freshteam|breezy|personio|jazzhr|applytojob|ripplehire|hire\.trakstar)[^\"'\s<>]*"

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

def show(label, url, data=None, headers=None, n=1500, grep=True):
    st, final, body = get(url, data, headers)
    print(f"\n===== {label}: {st} {final} len={len(body)}")
    if grep:
        hits = sorted(set(m.group(0)[:160] for m in re.finditer(ATS, body)))
        print("ATS hits:", hits[:40])
        for key in ["eagerLoadRefineSearch", "totalHits", "phApp", "refNum", "widgetApiEndpoint", "siteNumber", "jobsearch"]:
            i = body.find(key)
            if i >= 0:
                print(f"  [{key}] ...{body[max(0,i-150):i+350]!r}")
    print("HEAD:", body[:n].replace("\n", " ")[:n])

show("smartrecruiters IFS", "https://api.smartrecruiters.com/v1/companies/ifs1/postings?limit=3", grep=False)
show("syscolabs careers", "https://syscolabs.lk/careers", n=600)
show("g42 home", "https://careers.g42.ai/global/en/home", n=300)
show("g42 search", "https://careers.g42.ai/global/en/search-results", n=300)
body = json.dumps({"lang": "en_global", "deviceType": "desktop", "country": "global", "pageName": "search-results",
                   "ddoKey": "refineSearch", "sortBy": "", "subsearch": "", "from": 0, "jobs": True, "counts": True,
                   "all_fields": ["category", "country", "city"], "size": 3, "clearAll": False, "jdsource": "facets",
                   "isSliderEnable": False, "pageId": "page20", "siteType": "external", "keywords": "",
                   "global": True, "selected_fields": {}, "locationData": {}}).encode()
show("g42 widgets", "https://careers.g42.ai/widgets", data=body, headers={"Content-Type": "application/json"}, n=2500, grep=False)
show("accenture ae careers", "https://www.accenture.com/ae-en/careers/jobsearch", n=300)
acc = json.dumps({"f": 1, "s": 3, "k": "", "lang": "en", "cs": "ae-en", "df": "[]", "c": "United Arab Emirates",
                  "sf": 1, "syn": False, "isPk": False, "wordDistance": 0, "userId": ""}).encode()
show("accenture api", "https://www.accenture.com/api/accenture/jobsearch/result", data=acc,
     headers={"Content-Type": "application/json"}, n=2500, grep=False)
