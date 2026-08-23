#!/usr/bin/env python3
"""Generate PetroTechRadar community contribution activity data and page.

Tracks currently open GitHub Issues created in the last 7 days (Current Pulse)
and last 180 days (Contribution Opportunities) for every repository in radar.json.
Pull requests are excluded. Outputs are static JSON + HTML for GitHub Pages.
"""
from __future__ import annotations

import html
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADAR = ROOT / "docs" / "data" / "radar.json"
DATA = ROOT / "docs" / "data"
OUT_JSON = DATA / "issues.json"
OUT_HTML = ROOT / "docs" / "issues.html"
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
NOW = datetime.now(timezone.utc)
DAYS_PULSE = 7
DAYS_OPPORTUNITY = 180


def api_json(url: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "PetroTechRadar-issue-activity")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.load(resp)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def github_issue_search_url(repo: str, since_date: str) -> str:
    q = f"is:issue is:open created:>={since_date}"
    return f"https://github.com/{repo}/issues?q={urllib.parse.quote(q)}"


def collect_recent_open_issues(repo: str, cutoff: datetime) -> list[dict]:
    """List open issues created since cutoff, newest first, excluding PRs."""
    found: list[dict] = []
    page = 1
    while page <= 20:
        url = (
            f"https://api.github.com/repos/{repo}/issues"
            f"?state=open&sort=created&direction=desc&per_page=100&page={page}"
        )
        items = api_json(url)
        if not items:
            break
        stop = False
        for item in items:
            created = parse_dt(item.get("created_at", "1970-01-01T00:00:00Z"))
            if created < cutoff:
                stop = True
                break
            if "pull_request" in item:
                continue
            found.append({
                "number": int(item.get("number") or 0),
                "title": item.get("title") or "Untitled issue",
                "url": item.get("html_url") or "",
                "created_at": item.get("created_at") or "",
                "updated_at": item.get("updated_at") or "",
                "comments": int(item.get("comments") or 0),
                "author": ((item.get("user") or {}).get("login") or "unknown"),
                "author_association": item.get("author_association") or "NONE",
                "assigned": bool(item.get("assignee") or item.get("assignees")),
                "labels": [x.get("name", "") for x in (item.get("labels") or []) if x.get("name")],
            })
        if stop or len(items) < 100:
            break
        page += 1
        time.sleep(0.04)
    return found


def build_page() -> str:
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Community Pulse — PetroTechRadar</title><meta name="description" content="Current open-source contribution opportunities across subsurface repositories tracked by PetroTechRadar.">
<style>
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f9ff;color:#17324a;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}.wrap{max-width:1420px;margin:auto;padding:28px}.nav{display:flex;justify-content:space-between;align-items:center;gap:14px;position:sticky;top:0;z-index:20;padding:10px 0;background:rgba(245,249,255,.95);backdrop-filter:blur(12px)}.brand{font-weight:850;color:#153b66;text-decoration:none}.links{display:flex;gap:8px;flex-wrap:wrap}.links a,.btn{border:1px solid #bdd6f7;background:#fff;color:#286fbf;padding:9px 11px;border-radius:10px;text-decoration:none;font-size:12px;font-weight:750}.links a.active,.btn.primary{background:#2f80ed;color:#fff;border-color:#2f80ed}.hero{border:1px solid #cbdcf3;border-radius:24px;padding:30px;background:linear-gradient(135deg,#edf5ff,#e2efff 58%,#fafcff)}.eyebrow{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:#2f6eae}h1{font-size:clamp(36px,5vw,58px);line-height:1;margin:12px 0;color:#153b66;letter-spacing:-.04em}.sub{max-width:900px;color:#607991;line-height:1.55}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.stat{background:#fff;border:1px solid #d7e3f3;border-radius:15px;padding:16px}.stat strong{display:block;color:#153b66;font-size:26px}.stat span{font-size:11px;color:#73879a;text-transform:uppercase}.section{margin-top:28px}.section h2{margin:0;color:#153b66;font-size:22px}.section p{margin:6px 0 12px;color:#70869b;font-size:13px}.toolbar{display:grid;grid-template-columns:2fr 1fr;gap:10px;margin:12px 0}.toolbar input,.toolbar select{width:100%;padding:11px;border:1px solid #cbdcf3;border-radius:10px;background:#fff;color:#23435c}.tablebox{overflow:auto;background:#fff;border:1px solid #d7e3f3;border-radius:16px}table{width:100%;border-collapse:collapse;min-width:920px}th,td{padding:11px 12px;border-bottom:1px solid #e5edf7;text-align:left;font-size:12px}th{background:#eef5ff;color:#365e7a;position:sticky;top:0}tbody tr:hover{background:#f8fbff}a{color:#2f80ed;text-decoration:none}.pulse{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.card{background:#fff;border:1px solid #d7e3f3;border-radius:16px;padding:15px}.card strong{display:block;color:#225b94;margin-bottom:5px}.card small{color:#7b8fa2}.badges{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.badge{font-size:10px;padding:4px 7px;border-radius:999px;background:#edf5ff;border:1px solid #d4e6fa;color:#326fae}.hot{background:#fff3df;border-color:#f2d19a;color:#99651a}.empty{padding:24px;text-align:center;color:#7c90a4}.note{font-size:11px;color:#8192a4;line-height:1.55;margin-top:18px}.repo-actions{display:flex;gap:7px;flex-wrap:wrap}.repo-actions a{font-size:11px;padding:5px 7px;border:1px solid #d4e3f6;border-radius:8px;background:#f8fbff}footer{text-align:center;color:#8798a7;font-size:11px;padding:30px 0 8px}@media(max-width:900px){.stats{grid-template-columns:1fr 1fr}.pulse{grid-template-columns:1fr 1fr}}@media(max-width:650px){.wrap{padding:16px}.nav{align-items:flex-start;flex-direction:column}.stats,.pulse,.toolbar{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<div class="nav"><a class="brand" href="index.html">◉ PetroTechRadar</a><div class="links"><a href="index.html">Overview</a><a href="index.html#ptr-repositories">Repositories</a><a class="active" href="issues.html">Community Pulse</a><a href="papers.html">Papers</a><a href="https://github.com/santoshdhubia/PetroTechRadar" target="_blank" rel="noopener">GitHub</a></div></div>
<section class="hero"><div class="eyebrow">Open-source contribution intelligence</div><h1>Community <span style="color:#2f80ed">Pulse</span></h1><div class="sub">Find subsurface repositories where open issues are active now. The 7-day pulse highlights newly opened unresolved work; the 6-month view shows broader contribution opportunities. Click directly into the repository or its filtered GitHub Issues page to contribute.</div></section>
<section class="stats"><div class="stat"><strong id="s-repos">—</strong><span>Repos with open issues · 6 months</span></div><div class="stat"><strong id="s-open180">—</strong><span>Open issues created · 6 months</span></div><div class="stat"><strong id="s-repos7">—</strong><span>Repos active · 7 days</span></div><div class="stat"><strong id="s-open7">—</strong><span>New open issues · 7 days</span></div></section>
<section class="section"><h2>Current Pulse — last 7 days</h2><p>Recently opened issues that are still unresolved. Higher counts indicate current discussion/workload, not lower software quality.</p><div class="pulse" id="pulse"><div class="empty">Loading current pulse…</div></div></section>
<section class="section"><h2>Contribution opportunities — last 6 months</h2><p>Tracked repositories with open issues created during the last six months. Use the direct filtered Issues link to see current work suitable for contribution.</p><div class="toolbar"><input id="q" placeholder="Search repository, organization or domain…"><select id="sort"><option value="open180">Most open · 6 months</option><option value="open7">Most recent · 7 days</option><option value="score">Radar score</option></select></div><div class="tablebox"><table><thead><tr><th>#</th><th>Repository</th><th>Domain</th><th>Open · 7d</th><th>Open · 6mo</th><th>No response · 7d</th><th>Unassigned · 7d</th><th>Radar</th><th>Contribute</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<div class="note">Method note: only GitHub Issues that are currently open and were created inside the stated windows are counted; pull requests are excluded. A high issue count can reflect an active user/developer community and should not be interpreted as a defect or quality score.</div>
<footer>PetroTechRadar · Community Pulse · Generated from public GitHub issue metadata</footer></div>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-HJGM182PM4"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','G-HJGM182PM4');</script>
<script>
(()=>{let repos=[];const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));const q=document.getElementById('q'),sort=document.getElementById('sort'),rows=document.getElementById('rows'),pulse=document.getElementById('pulse');function renderTable(){const term=q.value.trim().toLowerCase();let a=repos.filter(r=>r.open_180d>0&&(`${r.repository} ${r.organization} ${r.domain}`).toLowerCase().includes(term));a.sort((x,y)=>sort.value==='open7'?y.open_7d-x.open_7d:sort.value==='score'?y.radar_score-x.radar_score:y.open_180d-x.open_180d);rows.innerHTML=a.length?a.map((r,i)=>`<tr><td>${i+1}</td><td><a href="${r.repo_url}" target="_blank" rel="noopener"><strong>${esc(r.repository)}</strong></a><div style="color:#7b8ea1;margin-top:3px">${esc(r.organization)}</div></td><td>${esc(r.domain)}</td><td><strong>${r.open_7d}</strong></td><td><strong>${r.open_180d}</strong></td><td>${r.no_response_7d}</td><td>${r.unassigned_7d}</td><td>${Number(r.radar_score||0).toFixed(1)}</td><td><div class="repo-actions"><a href="${r.issues_7d_url}" target="_blank" rel="noopener">7-day issues ↗</a><a href="${r.issues_180d_url}" target="_blank" rel="noopener">6-month issues ↗</a></div></td></tr>`).join(''):'<tr><td colspan="9"><div class="empty">No matching repositories.</div></td></tr>'}function renderPulse(){const active=repos.filter(r=>r.open_7d>0).sort((a,b)=>b.open_7d-a.open_7d||b.open_180d-a.open_180d).slice(0,12);pulse.innerHTML=active.length?active.map(r=>`<div class="card"><small>${esc(r.organization)} · ${esc(r.domain)}</small><strong>${esc(r.repository)}</strong><div class="badges"><span class="badge hot">${r.open_7d} new open · 7d</span><span class="badge">${r.no_response_7d} no response</span><span class="badge">${r.unassigned_7d} unassigned</span></div><div class="repo-actions" style="margin-top:12px"><a href="${r.issues_7d_url}" target="_blank" rel="noopener">View recent issues ↗</a><a href="${r.repo_url}" target="_blank" rel="noopener">Repository ↗</a></div></div>`).join(''):'<div class="empty">No tracked repositories currently have open issues created in the last 7 days.</div>'}fetch('./data/issues.json?v='+Date.now(),{cache:'reload'}).then(r=>{if(!r.ok)throw Error('issues.json unavailable');return r.json()}).then(p=>{repos=p.repositories||[];document.getElementById('s-repos').textContent=p.summary?.repositories_with_open_180d??'—';document.getElementById('s-open180').textContent=p.summary?.open_issues_180d??'—';document.getElementById('s-repos7').textContent=p.summary?.repositories_with_open_7d??'—';document.getElementById('s-open7').textContent=p.summary?.open_issues_7d??'—';renderPulse();renderTable()}).catch(()=>{pulse.innerHTML='<div class="empty">Issue activity data is not available yet. Run the PetroTechRadar refresh workflow.</div>';rows.innerHTML='<tr><td colspan="9"><div class="empty">Issue activity data unavailable.</div></td></tr>'});q.addEventListener('input',renderTable);sort.addEventListener('change',renderTable)})();
</script></body></html>'''


def main():
    payload = json.loads(RADAR.read_text(encoding="utf-8"))
    records = payload.get("repositories", [])
    cutoff_7 = NOW - timedelta(days=DAYS_PULSE)
    cutoff_180 = NOW - timedelta(days=DAYS_OPPORTUNITY)
    date_7 = cutoff_7.date().isoformat()
    date_180 = cutoff_180.date().isoformat()
    output = []
    errors = []

    for i, record in enumerate(records, 1):
        repo = (record.get("repository") or "").strip()
        if not repo:
            continue
        print(f"[{i}/{len(records)}] {repo}")
        try:
            issues = collect_recent_open_issues(repo, cutoff_180)
            pulse = [x for x in issues if parse_dt(x["created_at"]) >= cutoff_7]
            output.append({
                "repository": repo,
                "organization": record.get("organization") or repo.split("/", 1)[0],
                "domain": record.get("domain") or "",
                "tier": record.get("tier") or "",
                "radar_score": float(record.get("petrotech_radar_score") or 0),
                "repo_url": record.get("url") or f"https://github.com/{repo}",
                "open_7d": len(pulse),
                "open_180d": len(issues),
                "no_response_7d": sum(1 for x in pulse if x["comments"] == 0),
                "unassigned_7d": sum(1 for x in pulse if not x["assigned"]),
                "issues_7d_url": github_issue_search_url(repo, date_7),
                "issues_180d_url": github_issue_search_url(repo, date_180),
                "recent_issues": pulse[:8],
            })
        except Exception as exc:
            print(f"  ERROR: {exc}")
            errors.append({"repository": repo, "error": str(exc)})
        time.sleep(0.05)

    output.sort(key=lambda r: (r["open_7d"], r["open_180d"], r["radar_score"]), reverse=True)
    summary = {
        "tracked_repositories": len(records),
        "repositories_with_open_7d": sum(1 for r in output if r["open_7d"] > 0),
        "repositories_with_open_180d": sum(1 for r in output if r["open_180d"] > 0),
        "open_issues_7d": sum(r["open_7d"] for r in output),
        "open_issues_180d": sum(r["open_180d"] for r in output),
    }
    DATA.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({
        "generated_at": NOW.isoformat(),
        "window_7d_start": cutoff_7.isoformat(),
        "window_180d_start": cutoff_180.isoformat(),
        "summary": summary,
        "errors": errors,
        "repositories": output,
    }, indent=2), encoding="utf-8")
    OUT_HTML.write_text(build_page(), encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)} and {OUT_HTML.relative_to(ROOT)}")
    print(json.dumps(summary, indent=2))
    if errors:
        print(f"Completed with {len(errors)} repository errors; successful repositories remain available.")


if __name__ == "__main__":
    main()
