#!/usr/bin/env python3
from __future__ import annotations
import csv,json,math,os,urllib.request,urllib.parse
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/"catalog"/"PAPERS_WITH_CODE.csv"
NOW=datetime.now(timezone.utc)
TOKEN=os.environ.get("GITHUB_TOKEN","").strip()

def get_json(url,github=False):
    req=urllib.request.Request(url,headers={"User-Agent":"PetroTechRadar/1.0"})
    if github:
        req.add_header("Accept","application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version","2022-11-28")
        if TOKEN:req.add_header("Authorization",f"Bearer {TOKEN}")
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def openalex(doi, title=""):
    if doi:
        try:
            return get_json("https://api.openalex.org/works/https://doi.org/"+urllib.parse.quote(doi,safe="/:"))
        except Exception:
            pass
    if title:
        try:
            query=urllib.parse.quote(title)
            data=get_json("https://api.openalex.org/works?search="+query+"&per-page=5")
            results=data.get("results",[])
            if results:
                # prefer closest normalized title
                target=" ".join(title.lower().split())
                def dist(item):
                    cand=" ".join((item.get("title") or "").lower().split())
                    common=len(set(target.split()) & set(cand.split()))
                    return common
                return sorted(results,key=dist,reverse=True)[0]
        except Exception:
            pass
    return None

def cite_score(c):return round(min(100,33.3*math.log10(max(c,0)+1)),1)
def velocity_score(v):return round(min(100,50*math.log10(max(v,0)+1)),1)
def repro_score(v):return {"Very High":100,"High":88,"Medium":70,"Low":45}.get(v,60)
def gh_score(stars,forks,push):
    traction=min(100,22*math.log10(stars+1)+14*math.log10(forks+1))
    rec=0
    if push:
        dt=datetime.fromisoformat(push.replace("Z","+00:00"))
        days=max((NOW-dt).total_seconds()/86400,0)
        rec=max(0,100-min(days,730)/7.3)
    return round(.65*traction+.35*rec,1)

with CAT.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
for r in rows:
    status=[]
    oa=openalex(r.get("doi",""), r.get("paper_title",""))
    if oa:
        c=int(oa.get("cited_by_count",0) or 0); age=max(NOW.year-int(r["year"])+1,1); cpy=round(c/age,2)
        r["citations"]=c;r["citations_per_year"]=cpy;r["openalex_id"]=oa.get("id","")
        r["citation_score"]=cite_score(c);r["citation_velocity_score"]=velocity_score(cpy);status.append("citation-ok")
    else:status.append("citation-pending")
    try:
        m=get_json("https://api.github.com/repos/"+r["repository"],True)
        stars=int(m.get("stargazers_count",0) or 0);forks=int(m.get("forks_count",0) or 0);push=m.get("pushed_at") or ""
        r["repo_stars"]=stars;r["repo_forks"]=forks;r["repo_last_push"]=push;r["repo_license"]=((m.get("license") or {}).get("spdx_id") or "")
        r["github_score"]=gh_score(stars,forks,push);status.append("github-ok")
    except Exception:status.append("github-error")
    r["reproducibility_score"]=repro_score(r.get("reproducibility",""))
    tech=float(r.get("technical_relevance") or 0);repro=float(r.get("reproducibility_score") or 0);gh=float(r.get("github_score") or 0);venue=float(r.get("venue_score") or 0)
    cs=float(r.get("citation_score") or 0);cv=float(r.get("citation_velocity_score") or 0);code={"High":90,"Medium":72,"Low":45}.get(r.get("code_health",""),60)
    r["papers_with_code_score"]=round(.20*tech+.20*repro+.15*code+.10*venue+.15*cs+.10*cv+.10*gh,1)
    r["metrics_status"]=";".join(status);r["last_verified"]=NOW.date().isoformat()
with CAT.open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
