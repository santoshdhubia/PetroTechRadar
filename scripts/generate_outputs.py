#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"catalog"/"PETROTECHRADAR_V1.csv"
DATA=ROOT/"docs"/"data"; DATA.mkdir(parents=True,exist_ok=True)

ORG_MAP={"equinor":"Equinor","opendtect":"OpendTect","seequentevo":"Seequent","bp":"bp","sede-open":"Shell","schlumberger":"SLB","azure":"Microsoft","microsoft":"Microsoft","nvidia":"NVIDIA","opm":"OPM","agilescientific":"Agile Scientific","geos-dev":"GEOS Consortium","natlabrockies":"National Lab Rockies"}

with CATALOG.open(newline="",encoding="utf-8") as f:
    source_rows=list(csv.DictReader(f))

def n(v):
    try:return float(v)
    except:return 0.0

def disp(v):
    try:return f"{int(float(v)):,}"
    except:return "—"

def dt(v): return v[:10] if v else "—"

def organization_for(r):
    if (r.get("organization") or "").strip():
        return r["organization"].strip()
    owner=(r.get("repository") or "").split("/",1)[0].lower()
    return ORG_MAP.get(owner,(r.get("repository") or "").split("/",1)[0] or "Community")

rows=[]
for src in source_rows:
    r=dict(src); r["organization"]=organization_for(r); rows.append(r)

rows=sorted(rows,key=lambda r:(n(r.get("petrotech_radar_score")),n(r.get("stars"))),reverse=True)

(DATA/"radar.json").write_text(json.dumps({"generated_at":datetime.now(timezone.utc).isoformat(),"repository_count":len(rows),"repositories":rows},indent=2),encoding="utf-8")

fieldnames=list(rows[0].keys()) if rows else []
with (DATA/"radar.csv").open("w",newline="",encoding="utf-8") as f:
    if fieldnames:
        w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); w.writerows(rows)

def table(items,title,intro,limit=None):
    if limit: items=items[:limit]
    out=[f"# {title}","",intro,"","| Rank | Repository | Organization | Domain | Tier | Stars | Forks | Last push | Radar score |","|---:|---|---|---|---|---:|---:|---|---:|"]
    for i,r in enumerate(items,1):
        out.append(f"| {i} | [{r['repository']}]({r['url']}) | {r.get('organization','—')} | {r.get('domain','—')} | {r.get('tier','—')} | {disp(r.get('stars'))} | {disp(r.get('forks'))} | {dt(r.get('pushed_at'))} | {r.get('petrotech_radar_score') or '—'} |")
    out+=["","_Generated automatically from the live master catalogue._",""]
    return "\n".join(out)

(ROOT/"catalog"/"TOP_REPOSITORIES.md").write_text(table(rows,"Top PetroTechRadar Repositories","Highest-ranked repositories using technical curation plus current GitHub activity.",30),encoding="utf-8")
(ROOT/"catalog"/"EMERGING_RADAR.md").write_text(table([r for r in rows if r.get("tier")=="Emerging"],"Emerging & Vibe-Coded Radar","New AI, agentic, MCP, LLM and rapid-development petroleum/subsurface projects."),encoding="utf-8")
(ROOT/"catalog"/"RESEARCH_RADAR.md").write_text(table([r for r in rows if r.get("tier")=="Research"],"Research Radar","Research code, datasets and reproducible technical methods."),encoding="utf-8")
(ROOT/"catalog"/"SEISMIC_RADAR.md").write_text(table([r for r in rows if "Seismic" in (r.get("domain") or "") or "Geophysics" in (r.get("domain") or "")],"Seismic & Geophysics Radar","Seismic imaging, FWI, inversion, data and geophysical tools."),encoding="utf-8")
keys=("agent","mcp","rag","assistant","copilot","llm")
(ROOT/"catalog"/"AI_AGENT_RADAR.md").write_text(table([r for r in rows if "AI" in (r.get("domain") or "") or any(k in (r.get("focus") or "").lower() for k in keys)],"AI Agents, MCP & Engineering Copilots","Domain-specific AI agents, MCP tools, RAG systems and engineering copilots."),encoding="utf-8")

tiers=Counter(r.get("tier","") for r in rows if r.get("tier"))
domains=Counter((r.get("domain") or "").split(" / ")[0] for r in rows if r.get("domain"))
organizations=Counter(r.get("organization","") for r in rows if r.get("organization"))
dates=[r.get("last_verified") for r in rows if r.get("last_verified")]
(DATA/"stats.json").write_text(json.dumps({"repository_count":len(rows),"tiers":dict(tiers),"domains":dict(domains),"organizations":dict(organizations),"last_verified":max(dates) if dates else ""},indent=2),encoding="utf-8")
