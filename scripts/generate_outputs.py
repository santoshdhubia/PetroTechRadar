#!/usr/bin/env python3
from __future__ import annotations
import csv, json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; CATALOG=ROOT/'catalog'/'PETROTECHRADAR_V1.csv'; DATA=ROOT/'docs'/'data'; DATA.mkdir(parents=True,exist_ok=True)
with CATALOG.open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
def n(v):
    try:return float(v)
    except:return 0.0
def disp(v):
    try:return f'{int(float(v)):,}'
    except:return '—'
def dt(v): return v[:10] if v else '—'
rows=sorted(rows,key=lambda r:(n(r.get('petrotech_radar_score')),n(r.get('stars'))),reverse=True)
(DATA/'radar.json').write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'repository_count':len(rows),'repositories':rows},indent=2),encoding='utf-8')
with (DATA/'radar.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
def table(items,title,intro,limit=None):
    if limit: items=items[:limit]
    out=[f'# {title}','',intro,'','| Rank | Repository | Domain | Tier | Stars | Forks | Last push | Radar score |','|---:|---|---|---|---:|---:|---|---:|']
    for i,r in enumerate(items,1): out.append(f"| {i} | [{r['repository']}]({r['url']}) | {r['domain']} | {r['tier']} | {disp(r.get('stars'))} | {disp(r.get('forks'))} | {dt(r.get('pushed_at'))} | {r.get('petrotech_radar_score') or '—'} |")
    out+=['','_Generated automatically from the live master catalogue._','']; return '\n'.join(out)
(ROOT/'catalog'/'TOP_REPOSITORIES.md').write_text(table(rows,'Top PetroTechRadar Repositories','Highest-ranked repositories using technical curation plus current GitHub activity.',30),encoding='utf-8')
(ROOT/'catalog'/'EMERGING_RADAR.md').write_text(table([r for r in rows if r['tier']=='Emerging'],'Emerging & Vibe-Coded Radar','New AI, agentic, MCP, LLM and rapid-development petroleum/subsurface projects.'),encoding='utf-8')
(ROOT/'catalog'/'RESEARCH_RADAR.md').write_text(table([r for r in rows if r['tier']=='Research'],'Research Radar','Research code, datasets and reproducible technical methods.'),encoding='utf-8')
(ROOT/'catalog'/'SEISMIC_RADAR.md').write_text(table([r for r in rows if 'Seismic' in r['domain'] or 'Geophysics' in r['domain']],'Seismic & Geophysics Radar','Seismic imaging, FWI, inversion, data and geophysical tools.'),encoding='utf-8')
keys=('agent','mcp','rag','assistant','copilot')
(ROOT/'catalog'/'AI_AGENT_RADAR.md').write_text(table([r for r in rows if 'AI' in r['domain'] or any(k in (r.get('focus') or '').lower() for k in keys)],'AI Agents, MCP & Engineering Copilots','Domain-specific AI agents, MCP tools, RAG systems and engineering copilots.'),encoding='utf-8')
tiers=Counter(r['tier'] for r in rows); domains=Counter(r['domain'].split(' / ')[0] for r in rows); dates=[r.get('last_verified') for r in rows if r.get('last_verified')]
(DATA/'stats.json').write_text(json.dumps({'repository_count':len(rows),'tiers':dict(tiers),'domains':dict(domains),'last_verified':max(dates) if dates else ''},indent=2),encoding='utf-8')
