// Reads a CV in the browser (nothing is uploaded), finds known skills in it, and scores jobs against them.
const CV = (() => {
  const STORAGE_KEY = "cvProfile.v1";
  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // One regex per skill; a skill matches if any of its spellings appears as a whole word.
  const MATCHERS = SKILLS.map(([name, field, ...aliases]) => {
    const spellings = [name, ...aliases].filter((s) => !NOT_A_SPELLING.has(s));
    const exact = spellings.filter((s) => EXACT_CASE.has(s)).map(escapeRe);
    const loose = spellings.filter((s) => !EXACT_CASE.has(s)).map(escapeRe);
    const wrap = (alts, flags) => (alts.length ? new RegExp(`(?<![A-Za-z0-9+#.])(?:${alts.join("|")})(?![A-Za-z0-9+#])`, flags) : null);
    return { name, field, exact: wrap(exact, ""), loose: wrap(loose, "i") };
  });
  const FIELD_OF = Object.fromEntries(SKILLS.map(([name, field]) => [name, field]));

  function findSkills(text) {
    const found = new Set();
    for (const m of MATCHERS) if ((m.exact && m.exact.test(text)) || (m.loose && m.loose.test(text))) found.add(m.name);
    return found;
  }

  const state = { skills: new Set(), fileName: "", topFields: [], active: false, years: null };
  let avgIdf = 1;

  // "5 years", "5+ yrs", "over 7 years of experience" -> the largest number of years mentioned (capped, to skip dates).
  function yearsOfExperience(text) {
    let best = null;
    for (const m of text.matchAll(/(\d{1,2})\s*\+?\s*(?:years?|yrs?)(?![a-z])/gi)) {
      const n = Number(m[1]);
      if (n > 0 && n <= 40) best = Math.max(best || 0, n);
    }
    return best;
  }
  const JUNIOR = /\b(intern|internship|trainee|graduate|apprentice|junior|entry[- ]level)\b/i;
  const SENIOR = /\b(senior|sr\.?|lead|principal|staff|head|director|manager|architect|expert)\b/i;
  const EXECUTIVE = /\b(director|head of|vice president|vp|chief)\b/i;

  function seniorityFactor(title) {
    const y = state.years;
    if (y === null) return 1;
    if (JUNIOR.test(title)) return y >= 3 ? 0.55 : 1;
    if (EXECUTIVE.test(title)) return y < 8 ? 0.75 : 1;
    if (SENIOR.test(title)) return y < 3 ? 0.7 : 1;
    return 1;
  }
  let jobSkills = new Map(); // job id -> { all: Set, title: Set }
  let idf = new Map();

  function computeTopFields() {
    const weight = {};
    for (const s of state.skills) weight[FIELD_OF[s]] = (weight[FIELD_OF[s]] || 0) + 1;
    const ranked = Object.entries(weight).sort((a, b) => b[1] - a[1]);
    const max = ranked.length ? ranked[0][1] : 0;
    state.topFields = ranked.filter(([, w]) => w >= Math.max(2, max * 0.5)).slice(0, 3).map(([f]) => f);
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ skills: [...state.skills], fileName: state.fileName, years: state.years }));
    } catch (e) { /* storage unavailable: matching still works for this visit */ }
  }

  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (saved && saved.skills && saved.skills.length) {
        state.skills = new Set(saved.skills.filter((s) => FIELD_OF[s]));
        state.fileName = saved.fileName || "";
        state.years = typeof saved.years === "number" ? saved.years : null;
        state.active = state.skills.size > 0;
        computeTopFields();
      }
    } catch (e) { /* ignore */ }
  }

  function clear() {
    state.skills = new Set();
    state.fileName = "";
    state.topFields = [];
    state.active = false;
    state.years = null;
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* ignore */ }
  }

  function setSkills(skills, fileName, years) {
    state.skills = new Set(skills);
    if (fileName !== undefined) state.fileName = fileName;
    if (years !== undefined) state.years = years;
    state.active = state.skills.size > 0;
    computeTopFields();
    save();
  }

  // Precompute each job's skills and how rare each skill is across all jobs.
  function compile(jobs) {
    jobSkills = new Map();
    const df = new Map();
    for (const j of jobs) {
      const all = findSkills([j.title, j.category, j.summary, j.description].join("\n"));
      const title = findSkills(j.title);
      jobSkills.set(j.id, { all, title });
      for (const s of all) df.set(s, (df.get(s) || 0) + 1);
    }
    idf = new Map([...df].map(([s, n]) => [s, Math.log(1 + jobs.length / n)]));
    avgIdf = idf.size ? [...idf.values()].reduce((a, b) => a + b, 0) / idf.size : 1;
  }

  // 0..100: how much of what the job asks for appears in the CV, plus a nudge when the job is in the CV's main field.
  function score(job) {
    if (!state.active) return null;
    const js = jobSkills.get(job.id) || { all: new Set(), title: new Set() };
    const matched = [], missing = [];
    let have = 0, total = 0;
    for (const s of js.all) {
      const w = (idf.get(s) || 1) * (js.title.has(s) ? 2 : 1);
      total += w;
      if (state.skills.has(s)) { have += w; matched.push(s); } else missing.push(s);
    }
    // Smoothing: a job that lists only one or two skills can't reach a high score from them alone.
    let value = total ? have / (total + 2 * avgIdf) : 0;
    const inField = state.topFields.includes(job.field);
    if (inField) value = Math.min(1, value + (total ? 0.15 : 0.3));
    if (!matched.length && !inField) value = 0;
    value *= seniorityFactor(job.title);
    const byWeight = (a, b) => (idf.get(b) || 0) - (idf.get(a) || 0);
    return { pct: Math.round(value * 100), matched: matched.sort(byWeight), missing: missing.sort(byWeight) };
  }

  let pdfReady = null;
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = () => reject(new Error(`Couldn't load ${src}`));
      document.head.append(s);
    });
  }

  async function extractText(file) {
    const name = file.name.toLowerCase();
    if (name.endsWith(".pdf") || file.type === "application/pdf") {
      pdfReady = pdfReady || loadScript("vendor/pdf.min.js").then(() => {
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = "vendor/pdf.worker.min.js";
      });
      await pdfReady;
      const pdf = await window.pdfjsLib.getDocument({ data: await file.arrayBuffer() }).promise;
      const pages = [];
      for (let i = 1; i <= pdf.numPages; i++) {
        const content = await (await pdf.getPage(i)).getTextContent();
        pages.push(content.items.map((it) => it.str + (it.hasEOL ? "\n" : " ")).join(""));
      }
      return pages.join("\n");
    }
    if (name.endsWith(".docx")) {
      if (!window.mammoth) await loadScript("vendor/mammoth.browser.min.js");
      return (await window.mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })).value;
    }
    if (name.endsWith(".txt") || name.endsWith(".md") || file.type.startsWith("text/")) return file.text();
    if (name.endsWith(".doc")) throw new Error("Old .doc files can't be read. Please save your CV as PDF or .docx and try again.");
    throw new Error("Please upload your CV as a PDF, Word (.docx) or text file.");
  }

  async function analyze(file) {
    const text = await extractText(file);
    if (!text || text.trim().length < 30) {
      throw new Error("We couldn't read any text in this file. If it's a scanned image, please upload a text-based PDF or .docx.");
    }
    const skills = findSkills(text);
    setSkills(skills, file.name, yearsOfExperience(text));
    return skills;
  }

  return { yearsOfExperience, state, restore, clear, setSkills, compile, score, analyze, findSkills, allSkillNames: SKILLS.map((s) => s[0]), fieldOf: (s) => FIELD_OF[s] };
})();
