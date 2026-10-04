const NEW_DAYS = 2; // a job counts as "new" for this many days after the portal first sees it
const $ = (id) => document.getElementById(id);
let allJobs = [];

const isNew = (job) => Date.now() - Date.parse(job.first_seen) < NEW_DAYS * 864e5;
const safeUrl = (u) => (/^https:\/\//i.test(u || "") ? u : "#");
const fmtDate = (s) => {
  const d = new Date(s);
  return isNaN(d) ? "" : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
};
const cities = (job) => job.locations || [];

function el(tag, props = {}, children = []) {
  const node = Object.assign(document.createElement(tag), props);
  for (const c of [].concat(children)) if (c) node.append(c);
  return node;
}

function fillSelect(select, values) {
  for (const v of [...new Set(values)].filter(Boolean).sort()) select.append(el("option", { value: v, textContent: v }));
}

function metaLine(job) {
  return [cities(job).slice(0, 2).join(" · "), job.workplace_type, job.posted_date && "Posted " + fmtDate(job.posted_date)]
    .filter(Boolean).join("  |  ");
}

function render() {
  const q = $("search").value.trim().toLowerCase();
  const company = $("company").value;
  const location = $("location").value;
  const newOnly = $("newOnly").checked;

  const shown = allJobs.filter((j) =>
    (!company || j.company === company) &&
    (!location || cities(j).includes(location)) &&
    (!newOnly || isNew(j)) &&
    (!q || [j.title, j.company, j.category, j.summary, cities(j).join(" ")].join(" ").toLowerCase().includes(q))
  );

  const list = $("jobs");
  list.replaceChildren(...shown.map((job) => {
    const apply = el("a", { className: "apply", href: safeUrl(job.url), target: "_blank", rel: "noopener noreferrer", textContent: "Apply ↗" });
    apply.addEventListener("click", (e) => e.stopPropagation());
    const li = el("li", { className: "job", tabIndex: 0 }, [
      el("div", {}, [
        el("h3", { textContent: job.title }),
        el("div", { className: "meta", textContent: job.company }),
        el("div", { className: "meta", textContent: metaLine(job) }),
      ]),
      el("div", { className: "side" }, [isNew(job) && el("span", { className: "badge", textContent: "NEW" }), apply]),
    ]);
    li.addEventListener("click", () => openDetail(job));
    li.addEventListener("keydown", (e) => { if (e.key === "Enter") openDetail(job); });
    return li;
  }));

  const newCount = shown.filter(isNew).length;
  $("count").textContent = `${shown.length} IT job${shown.length === 1 ? "" : "s"}` + (newCount ? ` · ${newCount} new` : "");
  $("empty").hidden = shown.length > 0;
}

function openDetail(job) {
  $("d-company").textContent = job.company;
  $("d-title").textContent = job.title;
  $("d-meta").textContent = [cities(job).join(" · "), job.workplace_type, job.category,
    job.posted_date && "Posted " + fmtDate(job.posted_date)].filter(Boolean).join("  |  ");
  $("d-apply").href = safeUrl(job.url);
  $("d-desc").textContent = job.description || job.summary || "Open the company site for the full description.";
  $("detail").showModal();
}

function renderSources(sources) {
  $("sources").replaceChildren(...sources.map((s) => {
    const link = el("a", { href: safeUrl(s.careers_page), target: "_blank", rel: "noopener noreferrer", textContent: s.company });
    const note = s.ok
      ? el("span", { textContent: ` · ${s.it_jobs} IT jobs` })
      : el("span", { className: "err", textContent: ` · last check failed, showing earlier results` });
    return el("li", {}, [link, note]);
  }));
}

async function init() {
  try {
    const res = await fetch("data/jobs.json", { cache: "no-store" });
    const data = await res.json();
    allJobs = data.jobs || [];
    if (data.updated_at) $("updated").textContent = "Last checked " + new Date(data.updated_at).toLocaleString() + ".";
    fillSelect($("company"), allJobs.map((j) => j.company));
    fillSelect($("location"), allJobs.flatMap(cities));
    renderSources(data.sources || []);
  } catch (e) {
    $("count").textContent = "Couldn't load jobs right now.";
  }
  for (const id of ["search", "company", "location", "newOnly"]) $(id).addEventListener("input", render);
  $("detail").addEventListener("click", (e) => { if (e.target === $("detail")) $("detail").close(); });
  render();
}

init();
