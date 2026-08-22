#!/usr/bin/env python3
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/"catalog"/"PAPERS_WITH_CODE.csv"
with CAT.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
def n(v):
    try:return float(v)
    except:return 0
rows.sort(key=lambda r:(n(r.get("papers_with_code_score")),n(r.get("citations"))),reverse=True)
lines=["# Papers with Code","","Curated geophysics and computational-geophysics papers with publicly available code repositories.","","| Rank | Paper | Journal | Year | Topic | Citations | Cit./yr | GitHub ★ | Reproducibility | Score |","|---:|---|---|---:|---|---:|---:|---:|---|---:|"]
for i,r in enumerate(rows,1):
    paper=f"[{r['paper_title']}]({r['paper_url']})" if r.get("paper_url") else r["paper_title"]
    lines.append(f"| {i} | {paper} · [code]({r['repo_url']}) | {r['journal']} | {r['year']} | {r['topic']} | {r.get('citations') or '—'} | {r.get('citations_per_year') or '—'} | {r.get('repo_stars') or '—'} | {r['reproducibility']} | {r.get('papers_with_code_score') or '—'} |")
lines+=["","**Citation counts are age-normalized through citations/year so recent papers are not automatically penalized.**","","_Citation data: OpenAlex · Repository metrics: GitHub._"]
(ROOT/"catalog/PAPERS_WITH_CODE.md").write_text("\n".join(lines),encoding="utf-8")
(ROOT/"docs/data/papers.json").write_text(json.dumps({"papers":rows},indent=2),encoding="utf-8")
