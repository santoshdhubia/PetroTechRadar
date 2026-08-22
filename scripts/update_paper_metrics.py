#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, os, re, urllib.parse, urllib.request
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "catalog" / "PAPERS_WITH_CODE.csv"
NOW = datetime.now(timezone.utc)
TOKEN = os.environ.get("GITHUB_TOKEN","").strip()
TITLE_THRESHOLD = 0.88

def get_json(url, github=False):
    req = urllib.request.Request(url, headers={"User-Agent":"PetroTechRadar/1.0"})
    if github:
        req.add_header("Accept","application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version","2022-11-28")
        if TOKEN:
            req.add_header("Authorization",f"Bearer {TOKEN}")
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)

def normalize_title(s):
    s=(s or "").lower()
    s=re.sub(r"[^a-z0-9]+"," ",s)
    return " ".join(s.split())

def title_similarity(a,b):
    return SequenceMatcher(None,normalize_title(a),normalize_title(b)).ratio()

def openalex_match(doi,title,expected_year):
    if doi:
        try:
            work=get_json("https://api.openalex.org/works/https://doi.org/"+urllib.parse.quote(doi,safe="/:"))
            return work,"doi"
        except Exception:
            pass
    if not title:
        return None,"unverified"
    try:
        q=urllib.parse.quote(title)
        data=get_json("https://api.openalex.org/works?search="+q+"&per-page=10")
    except Exception:
        return None,"unverified"
    best=None
    best_score=0.0
    for item in data.get("results",[]):
        sim=title_similarity(title,item.get("title",""))
        yr=item.get("publication_year")
        year_ok=(not expected_year or not yr or abs(int(expected_year)-int(yr))<=1)
        if year_ok and sim>best_score:
            best,best_score=item,sim
    if best is not None and best_score>=TITLE_THRESHOLD:
        return best,f"title:{best_score:.3f}"
    return None,"unverified"

def cite_score(c): return round(min(100,33.3*math.log10(max(c,0)+1)),1)
def velocity_score(v): return round(min(100,50*math.log10(max(v,0)+1)),1)
def repro_score(v): return {"Very High":100,"High":88,"Medium":70,"Low":45}.get(v,60)

def gh_score(stars,forks,push):
    traction=min(100,22*math.log10(stars+1)+14*math.log10(forks+1))
    rec=0
    if push:
        dt=datetime.fromisoformat(push.replace("Z","+00:00"))
        days=max((NOW-dt).total_seconds()/86400,0)
        rec=max(0,100-min(days,730)/7.3)
    return round(.65*traction+.35*rec,1)

with CAT.open(newline="",encoding="utf-8") as f:
    rows=list(csv.DictReader(f))

for r in rows:
    status=[]
    oa,match_type=openalex_match(r.get("doi",""),r.get("paper_title",""),r.get("year",""))
    if oa:
        c=int(oa.get("cited_by_count",0) or 0)
        age=max(NOW.year-int(r["year"])+1,1)
        cpy=round(c/age,2)
        r["citations"]=c
        r["citations_per_year"]=cpy
        r["openalex_id"]=oa.get("id","")
        r["citation_score"]=cite_score(c)
        r["citation_velocity_score"]=velocity_score(cpy)
        status.append("citation-ok:"+match_type)
    else:
        r["citations"]=""
        r["citations_per_year"]=""
        r["openalex_id"]=""
        r["citation_score"]=""
        r["citation_velocity_score"]=""
        status.append("citation-unverified")

    try:
        m=get_json("https://api.github.com/repos/"+r["repository"],True)
        stars=int(m.get("stargazers_count",0) or 0)
        forks=int(m.get("forks_count",0) or 0)
        push=m.get("pushed_at") or ""
        r["repo_stars"]=stars
        r["repo_forks"]=forks
        r["repo_last_push"]=push
        r["repo_license"]=((m.get("license") or {}).get("spdx_id") or "")
        r["github_score"]=gh_score(stars,forks,push)
        status.append("github-ok")
    except Exception:
        status.append("github-error")

    r["reproducibility_score"]=repro_score(r.get("reproducibility",""))
    tech=float(r.get("technical_relevance") or 0)
    repro=float(r.get("reproducibility_score") or 0)
    gh=float(r.get("github_score") or 0)
    venue=float(r.get("venue_score") or 0)
    cs=float(r.get("citation_score") or 0)
    cv=float(r.get("citation_velocity_score") or 0)
    code={"Very High":100,"High":90,"Medium":72,"Low":45}.get(r.get("code_health",""),60)
    r["papers_with_code_score"]=round(.20*tech+.20*repro+.15*code+.10*venue+.15*cs+.10*cv+.10*gh,1)
    r["metrics_status"]=";".join(status)
    r["last_verified"]=NOW.date().isoformat()

with CAT.open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
