"""Build a self-contained HTML dashboard (report.html) from the analysis results."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from skills import CATEGORY, SOFT_SKILLS

TOP_MATCHES = 25  # "close to" jobs used for the "in your top matches" signal


def build_data(result: dict, have: set[str], unknown: list[str], role: str | None,
               goal_label: str | None = None, boost: dict[str, float] | None = None) -> dict:
    boost = boost or {}
    total, demand = result["total"], result["demand"]
    top_missing = {}
    for r in result["jobs"][:TOP_MATCHES]:
        for s in r["missing"]:
            top_missing[s] = top_missing.get(s, 0) + 1

    def row(skill: str) -> dict:
        n = demand[skill]
        return {"skill": skill, "category": CATEGORY[skill], "count": n,
                "pct": round(100 * n / total) if total else 0,
                "inTop": top_missing.get(skill, 0), "boost": boost.get(CATEGORY[skill], 1.0)}

    return {
        "generated": datetime.now().strftime("%b %d, %Y at %I:%M %p"),
        "total": total,
        "companies": len({r["job"]["company"] for r in result["jobs"]}),
        "role": goal_label if role and goal_label else (role or "all roles"),
        "roleRaw": role or "",
        "have": [row(s) for s in sorted(have - SOFT_SKILLS, key=lambda s: -demand[s])],
        "gaps": [row(s) for s, n in demand.most_common() if s not in have and s not in SOFT_SKILLS and n],
        "focus": sorted((row(s) for s, n in demand.items() if s not in have and s not in SOFT_SKILLS and n),
                        key=lambda r: -r["pct"] * r["boost"])[:12],
        "soft": [row(s) for s in sorted(SOFT_SKILLS, key=lambda s: -demand[s]) if demand[s]],
        "unknown": unknown,
        "jobs": [
            {"company": r["job"]["company"], "title": r["job"]["title"].strip(),
             "url": r["job"]["url"] or "", "location": r["job"]["location"] or "",
             "score": round(100 * r["score"]),
             "matched": sorted(r["matched"], key=lambda s: -demand[s]),
             "missing": sorted(r["missing"], key=lambda s: -demand[s])}
            for r in result["jobs"]
        ],
    }


def write_html(data: dict, path: Path) -> Path:
    payload = json.dumps(data).replace("</", "<\\/")  # safe inside <script>
    path.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    return path


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Internship Skills Review</title>
<style>
:root {
  --bg: #f6f7f9; --panel: #ffffff; --text: #1b1f24; --muted: #5f6b7a; --border: #e3e7ec;
  --accent: #3b5bdb; --accent-soft: #e7ecfd; --good: #2b8a3e; --good-soft: #e3f4e6;
  --gap: #c2410c; --gap-soft: #fdeee4; --track: #eef1f5;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111418; --panel: #191d23; --text: #e6e9ee; --muted: #9aa5b4; --border: #2a3039;
    --accent: #8ea6ff; --accent-soft: #232c4a; --good: #6cc785; --good-soft: #1d3324;
    --gap: #f59e6b; --gap-soft: #3a2518; --track: #252b34;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.wrap { max-width: 1040px; margin: 0 auto; padding: 28px 16px 60px; }
header h1 { margin: 0 0 4px; font-size: 26px; letter-spacing: -0.01em; }
header p { margin: 0; color: var(--muted); font-size: 13px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 22px 0; }
.stat { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
.stat b { display: block; font-size: 26px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 13px; }
nav { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 20px; overflow-x: auto; }
nav button { background: none; border: 0; border-bottom: 2px solid transparent; color: var(--muted);
  font: inherit; font-weight: 600; padding: 10px 14px; cursor: pointer; white-space: nowrap; }
nav button[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); }
.panel { display: none; } .panel.active { display: block; }
.card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; margin-bottom: 16px; }
.card h2 { margin: 0 0 4px; font-size: 17px; } .card .sub { margin: 0 0 14px; color: var(--muted); font-size: 13px; }
.bar-row { display: grid; grid-template-columns: 28px minmax(120px, 210px) 1fr 52px; align-items: center; gap: 10px; padding: 6px 0; }
.rank { color: var(--muted); font-variant-numeric: tabular-nums; text-align: right; font-size: 13px; }
.name { font-weight: 600; } .name small { display: block; font-weight: 400; color: var(--muted); font-size: 12px; }
.track { background: var(--track); border-radius: 6px; height: 12px; overflow: hidden; }
.fill { height: 100%; border-radius: 6px; }
.gapfill { background: var(--gap); } .goodfill { background: var(--good); } .accentfill { background: var(--accent); }
.val { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }
.hint.goal { color: var(--good); background: var(--good-soft); margin-left: 0; }
.hint { display: inline-block; margin-left: 6px; font-size: 11px; font-weight: 600; color: var(--accent);
  background: var(--accent-soft); border-radius: 999px; padding: 1px 7px; }
.cats { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 12px; border-radius: 999px; padding: 2px 9px; border: 1px solid var(--border); white-space: nowrap; }
.chip.have { background: var(--good-soft); color: var(--good); border-color: transparent; }
.chip.miss { background: var(--gap-soft); color: var(--gap); border-color: transparent; }
.toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.toolbar input, .toolbar select { font: inherit; color: var(--text); background: var(--panel);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; }
.toolbar input { flex: 1; min-width: 180px; }
.job { display: grid; grid-template-columns: 64px 1fr; gap: 14px; padding: 14px 0; border-top: 1px solid var(--border); }
.job:first-child { border-top: 0; }
.score { width: 56px; height: 56px; border-radius: 50%; display: grid; place-items: center; font-weight: 700;
  font-size: 15px; font-variant-numeric: tabular-nums; }
.job a { color: var(--text); font-weight: 600; text-decoration: none; } .job a:hover { color: var(--accent); text-decoration: underline; }
.job .meta { color: var(--muted); font-size: 13px; margin: 2px 0 8px; }
.empty { color: var(--muted); text-align: center; padding: 30px 0; }
.legend { color: var(--muted); font-size: 12px; margin-top: 10px; }
@media (max-width: 560px) {
  .bar-row { grid-template-columns: 22px 1fr 44px; } .bar-row .track { grid-column: 2 / 4; grid-row: 2; }
}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Internship Skills Review</h1>
    <p id="meta"></p>
  </header>
  <div class="stats" id="stats"></div>
  <nav role="tablist">
    <button role="tab" data-tab="focus">🎯 Work On Next</button>
    <button role="tab" data-tab="matches">💼 Best Matches</button>
    <button role="tab" data-tab="skills">✅ Your Skills</button>
    <button role="tab" data-tab="all">📊 All Skills</button>
  </nav>

  <section class="panel" id="focus">
    <div class="card">
      <h2>Top skills to learn next</h2>
      <p class="sub">Ranked by how many postings ask for each skill, weighted toward your goal (<span class="hint goal">★ goal</span> skills are boosted; weights live in companies.json). A blue tag means the skill is missing from your closest-matching internships, so learning it lifts you there first.</p>
      <div id="focusBars"></div>
    </div>
    <div class="card">
      <h2>Soft skills employers mention</h2>
      <p class="sub">Not counted in match scores, but put concrete examples of these on your resume.</p>
      <div id="softBars"></div>
    </div>
  </section>

  <section class="panel" id="matches">
    <div class="card">
      <div class="toolbar">
        <input id="q" type="search" placeholder="Search role, company or skill…">
        <select id="company"><option value="">All companies</option></select>
      </div>
      <div id="jobList"></div>
      <p class="legend">Match = share of the posting's technical skills you already have (postings listing fewer than 3 skills count as 3).</p>
    </div>
  </section>

  <section class="panel" id="skills">
    <div class="card">
      <h2>Skills you have</h2>
      <p class="sub">From your resume and my_skills.txt, ranked by how many postings want them.</p>
      <div id="haveBars"></div>
      <p class="legend" id="unknown"></p>
    </div>
  </section>

  <section class="panel" id="all">
    <div class="cats" id="cats"></div>
  </section>
</div>

<script>
const D = __DATA__;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

$("meta").textContent = `Generated ${D.generated} · showing: ${D.role}`;
$("meta").title = D.roleRaw ? "Title filter: " + D.roleRaw : "";
const avg = D.jobs.length ? Math.round(D.jobs.reduce((a, j) => a + j.score, 0) / D.jobs.length) : 0;
const good = D.jobs.filter((j) => j.score >= 50).length;
$("stats").innerHTML = [
  [D.total, "internship postings"], [D.companies, "companies hiring"],
  [D.have.length, "of your skills in demand"], [good, "postings you match ≥ 50%"], [avg + "%", "average match"],
].map(([b, s]) => `<div class="stat"><b>${b}</b><span>${s}</span></div>`).join("");

function bars(rows, cls, opts = {}) {
  if (!rows.length) return `<p class="empty">${opts.empty || "Nothing here yet."}</p>`;
  return rows.map((r, i) => `
    <div class="bar-row">
      <span class="rank">${opts.rank === false ? "" : i + 1}</span>
      <span class="name">${esc(r.skill)}${opts.hint && r.boost > 1 ? `<span class="hint goal">★ goal</span>` : ""}${opts.hint && r.inTop ? `<span class="hint">in ${r.inTop} top matches</span>` : ""}
        <small>${esc(r.category)} · ${r.count} postings</small></span>
      <div class="track"><div class="fill ${cls}" style="width:${r.pct}%"></div></div>
      <span class="val">${r.pct}%</span>
    </div>`).join("");
}

$("focusBars").innerHTML = bars(D.focus, "gapfill", { hint: true, empty: "No gaps found. Nice!" });
$("softBars").innerHTML = bars(D.soft, "accentfill", { rank: false });
$("haveBars").innerHTML = bars(D.have, "goodfill", { empty: "No skills found. Add your resume or fill in my_skills.txt." });
if (D.unknown.length) $("unknown").textContent = "Listed but not tracked (add to skills.py): " + D.unknown.join(", ");

// All skills by category
const byCat = {};
[...D.have.map((r) => ({ ...r, have: true })), ...D.gaps].forEach((r) => (byCat[r.category] ||= []).push(r));
$("cats").innerHTML = Object.entries(byCat)
  .sort((a, b) => Math.max(...b[1].map((r) => r.pct)) - Math.max(...a[1].map((r) => r.pct)))
  .map(([cat, rows]) => `<div class="card"><h2>${esc(cat)}</h2><p class="sub">${rows.filter((r) => r.have).length} of ${rows.length} skills</p>
    <div class="chips">${rows.sort((a, b) => b.pct - a.pct).map((r) =>
      `<span class="chip ${r.have ? "have" : "miss"}">${r.have ? "✓ " : ""}${esc(r.skill)} · ${r.pct}%</span>`).join("")}</div></div>`)
  .join("") + `<p class="legend">Green = you have it · orange = gap · % = share of postings</p>`;

// Best matches with search + company filter
[...new Set(D.jobs.map((j) => j.company))].sort().forEach((c) =>
  $("company").insertAdjacentHTML("beforeend", `<option>${esc(c)}</option>`));
function scoreStyle(s) {
  const v = s >= 50 ? "good" : s >= 30 ? "accent" : "gap";
  return `background:var(--${v}-soft);color:var(--${v})`;
}
function renderJobs() {
  const q = $("q").value.trim().toLowerCase(), co = $("company").value;
  const list = D.jobs.filter((j) => (!co || j.company === co) &&
    (!q || [j.title, j.company, j.location, ...j.matched, ...j.missing].join(" ").toLowerCase().includes(q))).slice(0, 60);
  $("jobList").innerHTML = list.length ? list.map((j) => `
    <div class="job">
      <div class="score" style="${scoreStyle(j.score)}">${j.score}%</div>
      <div>
        ${j.url ? `<a href="${esc(j.url)}" target="_blank" rel="noopener">${esc(j.title)}</a>` : `<b>${esc(j.title)}</b>`}
        <div class="meta">${esc(j.company)}${j.location ? " · " + esc(j.location) : ""}</div>
        <div class="chips">${j.matched.map((s) => `<span class="chip have">✓ ${esc(s)}</span>`).join("")}${
          j.missing.map((s) => `<span class="chip miss">${esc(s)}</span>`).join("")}</div>
      </div>
    </div>`).join("") : `<p class="empty">No postings match that search.</p>`;
}
$("q").addEventListener("input", renderJobs);
$("company").addEventListener("change", renderJobs);
renderJobs();

// Tabs (remembers the last tab you viewed)
function show(tab) {
  document.querySelectorAll("nav button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === tab));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === tab));
  try { localStorage.setItem("isr-tab", tab); } catch (e) {}
}
document.querySelectorAll("nav button").forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));
let start = "focus";
try { start = localStorage.getItem("isr-tab") || "focus"; } catch (e) {}
if (location.hash) start = location.hash.slice(1);
show($(start) ? start : "focus");
window.addEventListener("load", () => window.scrollTo(0, 0));  // don't jump to the #tab anchor
</script>
</body>
</html>
"""
