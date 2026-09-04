#!/usr/bin/env python3
from __future__ import annotations
import csv, json, math, os, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "catalog"
MAIN = CATALOG_DIR / "PETROTECHRADAR_V1.csv"
ADDITIONAL = CATALOG_DIR / "ADDITIONAL_REPOSITORIES.csv"
CANDIDATES = CATALOG_DIR / "DISCOVERY_CANDIDATES.csv"
SUMMARY = CATALOG_DIR / "discovery_summary.json"
TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
NOW = datetime.now(timezone.utc)

# Broad discovery topics. Search is intentionally redundant; dedupe happens by full_name.
QUERIES = [
    "seismic processing geophysics in:name,description,topics",
    "seismic interpretation geoscience in:name,description,topics",
    "full waveform inversion FWI seismic in:name,description,topics",
    "reverse time migration RTM seismic in:name,description,topics",
    "segy SEG-Y geophysics in:name,description,topics",
    "petrophysics well logs in:name,description,topics",
    "DLIS LAS well log in:name,description,topics",
    "reservoir simulation petroleum in:name,description,topics",
    "reservoir modeling geoscience in:name,description,topics",
    "history matching reservoir in:name,description,topics",
    "drilling petroleum engineering in:name,description,topics",
    "production optimization oil gas in:name,description,topics",
    "geothermal subsurface in:name,description,topics",
    "CCS carbon storage geoscience in:name,description,topics",
    "OSDU energy data in:name,description,topics",
    "RESQML ETP subsurface in:name,description,topics",
    "geological modeling structural geology in:name,description,topics",
    "geoscience machine learning subsurface in:name,description,topics",
    "geophysics machine learning in:name,description,topics",
    "MCP geoscience subsurface in:name,description,topics",
    "agent geoscience subsurface AI in:name,description,topics",
]

DOMAIN_RULES = [
    ("Seismic / Processing", ["seismic processing", "migration", "rtm", "fwi", "full waveform", "segy", "seg-y", "geophysics"]),
    ("Petrophysics / Data", ["petrophysics", "well log", "well logs", "dlis", "las file", "formation evaluation"]),
    ("Reservoir / Simulation", ["reservoir simulation", "black oil", "compositional", "history matching", "eclipse", "opm flow"]),
    ("Reservoir / Modeling", ["reservoir model", "static model", "reservoir modeling", "reservoir modelling"]),
    ("Drilling / Production", ["drilling", "well planning", "production optimization", "production engineering"]),
    ("Geothermal", ["geothermal"]),
    ("CCS / Carbon Storage", ["carbon storage", "ccs", "co2 storage", "carbon sequestration"]),
    ("Data / OSDU", ["osdu", "resqml", "energistics", "etp"]),
    ("Geology / Modeling", ["geological modeling", "geological modelling", "structural geology", "implicit modeling", "implicit modelling"]),
    ("AI / Geoscience", ["geoscience ai", "geophysics machine learning", "subsurface ai", "geoscience machine learning", "mcp", "agent"]),
]

STRONG_TERMS = {
    "seismic", "geophysics", "petrophysics", "reservoir", "subsurface", "geoscience",
    "geothermal", "osdu", "resqml", "well log", "well logs", "drilling", "petroleum",
    "carbon storage", "ccs", "fwi", "rtm", "seg-y", "segy"
}
NEGATIVE_TERMS = {"game", "minecraft", "crypto", "trading bot", "music", "medical imaging", "computer vision benchmark"}

FIELDS = [
    "repository","url","domain","focus","tier","stars","forks","open_issues","watchers","language","license",
    "created_at","pushed_at","archived","size_kb","age_months","stars_per_month","github_activity_score",
    "petrotech_radar_score","metrics_status","last_verified"
]
CAND_FIELDS = [
    "repository","url","domain","focus","suggested_tier","discovery_score","relevance_score","activity_score",
    "stars","forks","open_issues","language","license","created_at","pushed_at","archived","topics",
    "matched_queries","reason","decision","discovered_at"
]

def request_json(url: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "PetroTechRadar-Discovery")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def existing_repos() -> set[str]:
    out=set()
    for p in (MAIN, ADDITIONAL):
        if not p.exists(): continue
        with p.open(newline="",encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("repository"): out.add(r["repository"].strip().lower())
    return out

def months_since(s: str) -> float:
    if not s: return 999
    try: dt=datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception: return 999
    return max((NOW-dt).total_seconds()/86400/30.4375,0.1)

def classify_domain(text: str) -> str:
    t=text.lower()
    best=("AI / Geoscience",0)
    for domain, terms in DOMAIN_RULES:
        n=sum(1 for x in terms if x in t)
        if n>best[1]: best=(domain,n)
    return best[0] if best[1] else "Geoscience / Other"

def relevance(meta: dict) -> tuple[float,list[str]]:
    blob=" ".join([
        meta.get("name") or "", meta.get("full_name") or "", meta.get("description") or "",
        " ".join(meta.get("topics") or [])
    ]).lower()
    if any(x in blob for x in NEGATIVE_TERMS): return 0.0,["negative-domain match"]
    hits=[x for x in STRONG_TERMS if x in blob]
    score=min(100, len(hits)*18)
    if "subsurface" in blob or "geoscience" in blob: score+=15
    if any(x in blob for x in ("seismic","petrophysics","reservoir","geothermal","osdu","resqml")): score+=15
    return min(score,100),sorted(hits)

def activity(meta: dict) -> float:
    stars=meta.get("stargazers_count",0) or 0
    forks=meta.get("forks_count",0) or 0
    issues=meta.get("open_issues_count",0) or 0
    pushed=meta.get("pushed_at") or ""
    months=months_since(pushed)
    rec=max(0,100-min(months*30.4,730)/7.3)
    traction=min(100,18*math.log10(stars+1)+12*math.log10(forks+1))
    issue=min(100,20*math.log10(issues+1))
    return round(.5*traction+.4*rec+.1*issue,1)

def tier(meta: dict, rel: float, act: float) -> str:
    stars=meta.get("stargazers_count",0) or 0
    age=months_since(meta.get("created_at") or "")
    if rel>=85 and act>=55 and stars>=40: return "Core"
    if rel>=80 and age<=24 and act>=40: return "Emerging"
    if rel>=75 and ("jupyter notebook"==(meta.get("language") or "").lower() or stars>=20): return "Research"
    return "Reference"

def discovery_score(rel: float, act: float, meta: dict) -> float:
    stars=meta.get("stargazers_count",0) or 0
    star_bonus=min(10, math.log10(stars+1)*4)
    return round(.62*rel+.28*act+star_bonus,1)

def search_candidates():
    found={}
    for qi,q in enumerate(QUERIES,1):
        url="https://api.github.com/search/repositories?"+urllib.parse.urlencode({"q":q,"sort":"updated","order":"desc","per_page":20})
        try: payload=request_json(url)
        except Exception as e:
            print(f"Query failed {q}: {e}"); continue
        for item in payload.get("items",[]):
            full=(item.get("full_name") or "").strip()
            if not full or item.get("fork") or item.get("archived"): continue
            rec=found.setdefault(full,{"meta":item,"queries":[]})
            rec["queries"].append(q)
        print(f"Discovery query {qi}/{len(QUERIES)}: {q}")
        time.sleep(.15)
    return found

def write_additional(promoted: list[dict]):
    if not promoted: return
    with ADDITIONAL.open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f)); fieldnames=list(rows[0].keys()) if rows else FIELDS
    have={r["repository"].lower() for r in rows}
    for c in promoted:
        if c["repository"].lower() in have: continue
        row={k:"" for k in fieldnames}
        row.update({
            "repository":c["repository"],"url":c["url"],"domain":c["domain"],"focus":c["focus"],"tier":c["suggested_tier"],
            "stars":c["stars"],"forks":c["forks"],"open_issues":c["open_issues"],"language":c["language"],"license":c["license"],
            "created_at":c["created_at"],"pushed_at":c["pushed_at"],"archived":c["archived"],"metrics_status":"DISCOVERED",
            "last_verified":NOW.date().isoformat(),
        })
        rows.append(row); have.add(c["repository"].lower())
    with ADDITIONAL.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); w.writerows(rows)

def main():
    known=existing_repos(); raw=search_candidates(); candidates=[]; promoted=[]
    for full,rec in raw.items():
        if full.lower() in known: continue
        meta=rec["meta"]; rel,hits=relevance(meta); act=activity(meta); score=discovery_score(rel,act,meta)
        if rel<45: continue
        domain=classify_domain(" ".join([meta.get("description") or ""," ".join(meta.get("topics") or [])]))
        sug=tier(meta,rel,act); lic=(meta.get("license") or {}).get("spdx_id") or ""
        reason=f"relevance={rel:.0f}; activity={act:.1f}; matched={', '.join(hits[:6])}"
        decision="review"
        # Strict auto-promotion threshold: high relevance + current activity + non-trivial project.
        stars=meta.get("stargazers_count",0) or 0
        recent_months=months_since(meta.get("pushed_at") or "")
        if score>=78 and rel>=80 and recent_months<=12 and stars>=10:
            decision="auto-add"
        c={
            "repository":full,"url":meta.get("html_url") or f"https://github.com/{full}","domain":domain,
            "focus":(meta.get("description") or "").strip()[:240],"suggested_tier":sug,"discovery_score":score,
            "relevance_score":round(rel,1),"activity_score":act,"stars":stars,"forks":meta.get("forks_count",0) or 0,
            "open_issues":meta.get("open_issues_count",0) or 0,"language":meta.get("language") or "","license":lic,
            "created_at":meta.get("created_at") or "","pushed_at":meta.get("pushed_at") or "","archived":meta.get("archived",False),
            "topics":";".join(meta.get("topics") or []),"matched_queries":";".join(rec["queries"][:5]),"reason":reason,
            "decision":decision,"discovered_at":NOW.isoformat(),
        }
        candidates.append(c)
        if decision=="auto-add": promoted.append(c)
    candidates.sort(key=lambda x:(x["decision"]!="auto-add",-float(x["discovery_score"]),-int(x["stars"])))
    with CANDIDATES.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=CAND_FIELDS); w.writeheader(); w.writerows(candidates)
    write_additional(promoted)
    SUMMARY.write_text(json.dumps({
        "generated_at":NOW.isoformat(),"queries":len(QUERIES),"raw_unique":len(raw),"new_candidates":len(candidates),
        "auto_added":len(promoted),"review_only":sum(1 for x in candidates if x["decision"]=="review"),
        "auto_added_repositories":[x["repository"] for x in promoted],
    },indent=2)+"\n",encoding="utf-8")
    print(f"Discovery complete: {len(candidates)} candidates, {len(promoted)} auto-added")

if __name__=="__main__": main()
