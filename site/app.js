const NEW_DAYS = 2; // a job counts as "new" for this many days after the portal first sees it
const DAY = 864e5;
const FIELD_COLORS = {
  "Software Development": "#3b6fd4", "DevOps & Cloud": "#0e9384", "Cybersecurity": "#c4320a", "Data & AI": "#7a5af8",
  "QA & Testing": "#4e8a2e", "Product & Project": "#b8860b", "UI/UX Design": "#dd2590", "ERP & Business Apps": "#1570ef",
  "IT Support": "#5f6b7a", "Networking & Telecom": "#0086c9", "Systems & Infrastructure": "#6941c6",
  "Architecture": "#a15c07", "IT Consulting": "#344054", "Other IT": "#8a8f9c",
};
const AVATAR_COLORS = ["#0f2342", "#1d4e89", "#0e6655", "#7a3e9d", "#a0522d", "#2f4f4f", "#8b1e3f", "#3d5a80"];

const $ = (id) => document.getElementById(id);
const state = { field: "" };
let allJobs = [];

const ageDays = (iso) => (Date.now() - Date.parse(iso)) / DAY;
const isNew = (job) => ageDays(job.first_seen) < NEW_DAYS;
const safeUrl = (u) => (/^https:\/\//i.test(u || "") ? u : "#");
const cities = (job) => job.locations || [];
const countryList = (job) => (job.countries && job.countries.length ? job.countries : job.country ? [job.country] : []);
const flag = (code) => (/^[A-Z]{2}$/.test(code || "") ? String.fromCodePoint(...[...code].map((c) => 0x1f1a5 + c.charCodeAt(0))) : "");

function when(job) {
  const ref = job.posted_date || job.first_seen;
  const d = Math.floor(ageDays(ref));
  if (isNaN(d)) return "";
  if (d <= 0) return "Posted today";
  if (d === 1) return "Posted yesterday";
  if (d < 30) return `Posted ${d} days ago`;
  return "Posted " + new Date(ref).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function el(tag, props = {}, children = []) {
  const node = Object.assign(document.createElement(tag), props);
  for (const c of [].concat(children)) if (c) node.append(c);
  return node;
}

function initials(name) {
  const words = (name || "?").replace(/[^A-Za-z0-9& ]/g, " ").split(/\s+/).filter(Boolean);
  if (words.length === 1 && words[0].length <= 3) return words[0].toUpperCase();
  return (words.length > 1 ? words[0][0] + words[1][0] : (words[0] || "?").slice(0, 2)).toUpperCase();
}

function avatar(company, node) {
  const base = (company || "").split(" · ")[0];
  let h = 0;
  for (const ch of base) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  node.textContent = initials(base);
  node.style.background = AVATAR_COLORS[h % AVATAR_COLORS.length];
  return node;
}

function fieldTag(field) {
  const color = FIELD_COLORS[field] || FIELD_COLORS["Other IT"];
  const t = el("span", { className: "tag fieldtag", textContent: field });
  t.style.color = color;
  t.style.background = `color-mix(in srgb, ${color} 11%, transparent)`;
  return t;
}

function tagsFor(job, full = false) {
  const loc = full ? cities(job).join(" · ") : cities(job)[0] || job.country;
  return [
    fieldTag(job.field || "Other IT"),
    loc && el("span", { className: "tag", textContent: `${flag(job.country_code)} ${loc}`.trim() }),
    job.workplace_type && el("span", { className: "tag", textContent: job.workplace_type }),
    full && job.category && el("span", { className: "tag", textContent: job.category }),
  ];
}

function companyLine(job) {
  return job.company + (job.via ? ` · via ${job.via}` : "");
}

function matches(job, skip) {
  const q = $("search").value.trim().toLowerCase();
  const country = $("country").value;
  const company = $("company").value;
  const posted = Number($("posted").value);
  return (
    (skip === "field" || !state.field || job.field === state.field) &&
    (!country || countryList(job).includes(country)) &&
    (!company || job.company === company) &&
    (!posted || ageDays(job.first_seen) < posted) &&
    (!q || [job.title, job.company, job.field, job.category, job.summary, cities(job).join(" ")].join(" ").toLowerCase().includes(q))
  );
}

function sorted(jobs) {
  const by = $("sort").value;
  const list = [...jobs];
  if (by === "posted") list.sort((a, b) => (b.posted_date || "").localeCompare(a.posted_date || ""));
  else if (by === "company") list.sort((a, b) => a.company.localeCompare(b.company) || a.title.localeCompare(b.title));
  else list.sort((a, b) => b.first_seen.localeCompare(a.first_seen) || (b.posted_date || "").localeCompare(a.posted_date || ""));
  return list;
}

function renderFields(fieldNames) {
  const pool = allJobs.filter((j) => matches(j, "field"));
  const counts = {};
  for (const j of pool) counts[j.field] = (counts[j.field] || 0) + 1;
  const names = fieldNames.filter((f) => counts[f] || f === state.field);
  const chip = (value, label, n) => {
    const b = el("button", { className: "chip", type: "button", role: "radio" }, [
      el("span", {}, [value && Object.assign(el("span", { className: "dot" }), { style: `background:${FIELD_COLORS[value] || "#8a8f9c"}` }), label]),
      el("span", { className: "n", textContent: n }),
    ]);
    b.setAttribute("aria-checked", String(state.field === value));
    b.addEventListener("click", () => { state.field = value; render(); });
    return b;
  };
  $("fields").replaceChildren(chip("", "All IT fields", pool.length), ...names.map((f) => chip(f, f, counts[f] || 0)));
}

function renderStats() {
  const stat = (n, label) => el("div", { className: "stat" }, [el("b", { textContent: n }), el("span", { textContent: label })]);
  $("stats").replaceChildren(
    stat(allJobs.length, "Open IT roles"),
    stat(allJobs.filter(isNew).length, "New in 48 hours"),
    stat(new Set(allJobs.map((j) => j.company.split(" · ")[0])).size, "Companies"),
    stat(new Set(allJobs.flatMap(countryList)).size, "Countries"),
  );
}

let fieldNames = [];
function render() {
  renderFields(fieldNames);
  const shown = sorted(allJobs.filter((j) => matches(j)));
  $("jobs").replaceChildren(...shown.map((job) => {
    const apply = el("a", { className: "btn btn-primary", href: safeUrl(job.url), target: "_blank", rel: "noopener noreferrer", textContent: "Apply ↗" });
    apply.addEventListener("click", (e) => e.stopPropagation());
    const li = el("li", { className: "job", tabIndex: 0 }, [
      avatar(job.company, el("span", { className: "avatar", ariaHidden: "true" })),
      el("div", {}, [
        el("h3", { textContent: job.title }),
        el("p", { className: "co", textContent: companyLine(job) }),
        el("div", { className: "tags" }, tagsFor(job)),
      ]),
      el("div", { className: "side" }, [
        el("div", { className: "when" }, [isNew(job) && el("span", { className: "badge-new", textContent: "NEW" }), " ", when(job)]),
        apply,
      ]),
    ]);
    li.addEventListener("click", () => openDetail(job));
    li.addEventListener("keydown", (e) => { if (e.key === "Enter") openDetail(job); });
    return li;
  }));
  const newCount = shown.filter(isNew).length;
  $("count").replaceChildren(el("b", { textContent: shown.length }), ` IT job${shown.length === 1 ? "" : "s"}` + (newCount ? ` · ${newCount} new` : ""));
  $("empty").hidden = shown.length > 0;
}

function openDetail(job) {
  avatar(job.company, $("d-avatar"));
  $("d-company").textContent = companyLine(job);
  $("d-title").textContent = job.title;
  $("d-tags").replaceChildren(...tagsFor(job, true), el("span", { className: "tag", textContent: when(job) }));
  $("d-apply").href = safeUrl(job.url);
  $("d-desc").textContent = job.description || job.summary || "Open the company site for the full description.";
  $("detail").showModal();
  $("detail").scrollTop = 0;
}

function fillSelect(select, values) {
  for (const v of [...new Set(values)].filter(Boolean).sort((a, b) => a.localeCompare(b))) select.append(el("option", { value: v, textContent: v }));
}

function renderSources(sources) {
  $("sources").replaceChildren(...sources.map((s) => el("li", {}, [
    el("a", { href: safeUrl(s.careers_page), target: "_blank", rel: "noopener noreferrer", textContent: s.company }),
    s.ok ? ` · ${s.it_jobs}` : el("span", { className: "err", textContent: " · last check failed" }),
  ])));
}

async function init() {
  try {
    const res = await fetch("data/jobs.json", { cache: "no-store" });
    const data = await res.json();
    allJobs = (data.jobs || []).map((j) => ({ ...j, field: j.field || "Other IT" }));
    fieldNames = data.fields || Object.keys(FIELD_COLORS);
    if (data.updated_at) $("updated").textContent = "Updated " + new Date(data.updated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    fillSelect($("country"), allJobs.flatMap(countryList));
    fillSelect($("company"), allJobs.map((j) => j.company));
    renderSources(data.sources || []);
    renderStats();
  } catch (e) {
    $("count").textContent = "Couldn't load jobs right now. Please try again shortly.";
  }
  for (const id of ["search", "country", "company", "posted", "sort"]) $(id).addEventListener("input", render);
  $("clear").addEventListener("click", () => {
    for (const id of ["search", "country", "company", "posted"]) $(id).value = "";
    state.field = "";
    render();
  });
  $("detail").addEventListener("click", (e) => { if (e.target === $("detail")) $("detail").close(); });
  render();
}

init();
