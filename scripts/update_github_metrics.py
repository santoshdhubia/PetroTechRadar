#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, os, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = [
    ROOT / "catalog" / "PETROTECHRADAR_V1.csv",
    ROOT / "catalog" / "ADDITIONAL_REPOSITORIES.csv",
]
TODAY = datetime.now(timezone.utc)
TOKEN = os.environ.get("GITHUB_TOKEN","").strip()

def request_json(url):
    req=urllib.request.Request(url)
    req.add_header("Accept","application/vnd.github+json")
    req.add_header("User-Agent","PetroTechRadar")
    req.add_header("X-GitHub-Api-Version","2022-11-28")
    if TOKEN: req.add_header("Authorization",f"Bearer {TOKEN}")
    with urllib.request.urlopen(req,timeout=30) as resp:
        return json.load(resp)

def months_since(s):
    if not s: return 0.0
    dt=datetime.fromisoformat(s.replace("Z","+00:00"))
    return max((TODAY-dt).total_seconds()/86400/30.4375,0.1)

def activity(meta):
    stars=meta.get("stargazers_count",0) or 0
    forks=meta.get("forks_count",0) or 0
    issues=meta.get("open_issues_count",0) or 0
    rec=0.0
    if meta.get("pushed_at"):
        dt=datetime.fromisoformat(meta["pushed_at"].replace("Z","+00:00"))
        days=max((TODAY-dt).total_seconds()/86400,0)
        rec=max(0,100-min(days,730)/7.3)
    traction=min(100,18*math.log10(stars+1)+12*math.log10(forks+1))
    issue=min(100,20*math.log10(issues+1))
    return round(.5*traction+.4*rec+.1*issue,1)

def prior(tier):
    return {"Core":90,"Research":82,"Emerging":78,"Reference":68,"Watch":55}.get(tier,65)

def radar(meta,tier):
    return round(.70*prior(tier)+.30*activity(meta),1)

all_errors=[]
total=0
success=0

for catalog in CATALOGS:
    if not catalog.exists():
        print(f"Skipping missing catalogue: {catalog}")
        continue
    with catalog.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    if not rows:
        continue

    print(f"\nRefreshing {catalog.name}: {len(rows)} repositories")
    for i,row in enumerate(rows,1):
        repo=row["repository"]
        total += 1
        try:
            meta=request_json(f"https://api.github.com/repos/{repo}")
            age=months_since(meta.get("created_at",""))
            stars=meta.get("stargazers_count",0) or 0
            lic=meta.get("license") or {}
            row.update({
                "stars":stars,
                "forks":meta.get("forks_count",0) or 0,
                "open_issues":meta.get("open_issues_count",0) or 0,
                "watchers":meta.get("subscribers_count",0) or 0,
                "language":meta.get("language") or "",
                "license":lic.get("spdx_id") or "",
                "created_at":meta.get("created_at") or "",
                "pushed_at":meta.get("pushed_at") or "",
                "archived":meta.get("archived",False),
                "size_kb":meta.get("size",0) or 0,
                "age_months":round(age,1),
                "stars_per_month":round(stars/age,2) if age else 0,
                "github_activity_score":activity(meta),
                "petrotech_radar_score":radar(meta,row["tier"]),
                "metrics_status":"OK",
                "last_verified":TODAY.date().isoformat(),
            })
            success += 1
            print(f"[{i}/{len(rows)}] {repo}: {stars} stars")
        except Exception as exc:
            row["metrics_status"]=f"ERROR: {type(exc).__name__}"
            all_errors.append({"repository":repo,"catalog":catalog.name,"error":str(exc)})
            print(f"ERROR {repo}: {exc}")
        time.sleep(.08)

    with catalog.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

(ROOT/"catalog"/"metrics_refresh_status.json").write_text(
    json.dumps({
        "refreshed_at":TODAY.isoformat(),
        "repository_count":total,
        "successful":success,
        "errors":all_errors
    },indent=2),
    encoding="utf-8"
)
