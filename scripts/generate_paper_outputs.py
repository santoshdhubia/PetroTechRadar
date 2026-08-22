#!/usr/bin/env python3
import csv,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/"catalog"/"PAPERS_WITH_CODE.csv"
README=ROOT/"README.md"

with CAT.open(newline="",encoding="utf-8") as f:
    rows=list(csv.DictReader(f))

def n(v):
    try:return float(v)
    except:return 0

# Main ranking
ranked=sorted(rows,key=lambda r:(n(r.get("papers_with_code_score")),n(r.get("citations"))),reverse=True)
lines=[
"# Papers with Code","",
"Curated geophysics and computational-geophysics papers with publicly available code repositories.","",
"| Rank | Paper | Journal | Year | Topic | Citations | Cit./yr | GitHub ★ | Reproducibility | Score |",
"|---:|---|---|---:|---|---:|---:|---:|---|---:|"
]
for i,r in enumerate(ranked,1):
    paper=f"[{r['paper_title']}]({r['paper_url']})" if r.get("paper_url") else r["paper_title"]
    lines.append(
        f"| {i} | {paper} · [code]({r['repo_url']}) | {r['journal']} | {r['year']} | {r['topic']} | "
        f"{r.get('citations') or '—'} | {r.get('citations_per_year') or '—'} | {r.get('repo_stars') or '—'} | "
        f"{r['reproducibility']} | {r.get('papers_with_code_score') or '—'} |"
    )
lines += [
"","**Citation counts are age-normalized through citations/year so recent papers are not automatically penalized.**","",
"_Citation data: OpenAlex · Repository metrics: GitHub._"
]
(ROOT/"catalog/PAPERS_WITH_CODE.md").write_text("\n".join(lines),encoding="utf-8")
(ROOT/"docs/data/papers.json").write_text(json.dumps({"papers":ranked},indent=2),encoding="utf-8")

# Top cited table
cited=[r for r in rows if n(r.get("citations"))>0]
cited.sort(key=lambda r:n(r.get("citations")),reverse=True)
top=cited[:7]

top_lines=[
"# Top Cited Papers with Code","",
"Highest-cited paper-code pairs currently tracked by PetroTechRadar.","",
"| Paper | Journal | Year | Citations | Cit./yr | Code |",
"|---|---|---:|---:|---:|---|"
]
for r in top:
    p=f"[{r['paper_title']}]({r['paper_url']})" if r.get("paper_url") else r["paper_title"]
    top_lines.append(f"| {p} | {r['journal']} | {r['year']} | **{int(n(r['citations'])):,}** | {n(r.get('citations_per_year')):.1f} | [GitHub]({r['repo_url']}) |")
top_lines += ["","_Citation counts refresh from OpenAlex._",""]
(ROOT/"catalog/TOP_CITED_PAPERS.md").write_text("\n".join(top_lines),encoding="utf-8")

# Automatically refresh the landing-page top-cited block
if README.exists():
    readme=README.read_text(encoding="utf-8")
    start="<!-- TOP-CITED-PAPERS:START -->"
    end="<!-- TOP-CITED-PAPERS:END -->"

    if top:
        block=[
            start,
            "",
            "### 🔥 Top Cited Papers with Code",
            "",
            "| Paper | Journal | Year | Citations | Cit./yr | Code |",
            "|---|---|---:|---:|---:|---|"
        ]
        for r in top[:5]:
            p=f"[{r['paper_title']}]({r['paper_url']})" if r.get("paper_url") else r["paper_title"]
            block.append(
                f"| {p} | {r['journal']} | {r['year']} | **{int(n(r['citations'])):,}** | "
                f"{n(r.get('citations_per_year')):.1f} | [GitHub]({r['repo_url']}) |"
            )
        block += [
            "",
            "**[→ View all Papers with Code](catalog/PAPERS_WITH_CODE.md)** · "
            "**[Rank by citations](catalog/TOP_CITED_PAPERS.md)**",
            "",
            "_Citations: OpenAlex · automatically refreshed._",
            "",
            end
        ]
    else:
        block=[
            start,"",
            "### 🔥 Top Cited Papers with Code","",
            "_Citation metrics have not been refreshed yet. Run **Actions → Refresh PetroTechRadar** once to populate this table._",
            "",end
        ]
    block_text="\n".join(block)

    if start in readme and end in readme:
        readme=re.sub(re.escape(start)+r".*?"+re.escape(end),block_text,readme,flags=re.S)
    else:
        anchor="Citation metrics refresh from **OpenAlex**; repository-health metrics refresh from GitHub."
        readme=readme.replace(anchor,anchor+"\n\n"+block_text)

    README.write_text(readme,encoding="utf-8")
