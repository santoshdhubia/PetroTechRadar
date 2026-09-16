#!/usr/bin/env python3
"""Apply human-reviewed discovery decisions before the weekly radar refresh."""
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "catalog"
REVIEW = CAT / "REVIEW_RECOMMENDATIONS.csv"
CAND = CAT / "DISCOVERY_CANDIDATES.csv"
ADDITIONAL = CAT / "ADDITIONAL_REPOSITORIES.csv"
NOW = datetime.now(timezone.utc)

with REVIEW.open(newline="", encoding="utf-8") as f:
    decisions = {r["repository"].lower(): r for r in csv.DictReader(f)}
with CAND.open(newline="", encoding="utf-8") as f:
    candidates = list(csv.DictReader(f))
with ADDITIONAL.open(newline="", encoding="utf-8") as f:
    additional = list(csv.DictReader(f))

fields = list(additional[0].keys())
have = {r["repository"].lower() for r in additional}
remaining = []
promoted = []

for c in candidates:
    review = decisions.get(c["repository"].lower())
    decision = (review or {}).get("suggested_decision", "review").lower()
    if decision == "approve":
        if c["repository"].lower() not in have:
            row = {k: "" for k in fields}
            row.update({
                "repository": c["repository"], "url": c["url"], "domain": c["domain"],
                "focus": c["focus"], "tier": c["suggested_tier"], "stars": c["stars"],
                "forks": c["forks"], "open_issues": c["open_issues"], "language": c["language"],
                "license": c["license"], "created_at": c["created_at"], "pushed_at": c["pushed_at"],
                "archived": c["archived"], "metrics_status": "REVIEW-APPROVED",
                "last_verified": NOW.date().isoformat(),
            })
            additional.append(row); have.add(c["repository"].lower()); promoted.append(c["repository"])
    else:
        if review:
            c["decision"] = decision
            if "review_note" in c: c["review_note"] = review.get("review_reason", "")
            if "reviewed_at" in c: c["reviewed_at"] = NOW.isoformat()
        remaining.append(c)

with ADDITIONAL.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(additional)
with CAND.open("w", newline="", encoding="utf-8") as f:
    cfields = list(candidates[0].keys()) if candidates else []
    if cfields:
        w = csv.DictWriter(f, fieldnames=cfields); w.writeheader(); w.writerows(remaining)

print(f"Promoted {len(promoted)} reviewed repositories: {', '.join(promoted) if promoted else 'none'}")
