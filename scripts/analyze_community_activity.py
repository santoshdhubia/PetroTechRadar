#!/usr/bin/env python3
"""Internal PetroTechRadar community/development activity analysis.

This script is intentionally not wired into the public website yet. It reads the
live radar catalogue, samples recent GitHub issues and pull requests for the
highest-signal repositories, and writes internal JSON/CSV outputs that can be
reviewed before deciding whether to expose a public Community Activity metric.

Environment:
  GITHUB_TOKEN   Optional but strongly recommended for higher API limits.

Usage:
  python scripts/analyze_community_activity.py
  python scripts/analyze_community_activity.py --top 25 --days 180
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADAR = ROOT / "docs" / "data" / "radar.json"
OUTDIR = ROOT / "analysis" / "community_activity"
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
NOW = datetime.now(timezone.utc)


def request_json(url: str):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "PetroTechRadar-community-analysis")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def search_count(query: str) -> int:
    url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(query)
    return int(request_json(url).get("total_count", 0))


def search_items(query: str, per_page: int = 100):
    url = (
        "https://api.github.com/search/issues?q="
        + urllib.parse.quote(query)
        + f"&per_page={min(per_page,100)}&sort=created&order=desc"
    )
    return request_json(url).get("items", [])


def repo_owner(repo: str) -> str:
    return repo.split("/", 1)[0].lower()


def safe_log(x: float) -> float:
    return math.log10(max(0.0, x) + 1.0)


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def classify_author(login: str, owner: str, association: str | None) -> str:
    """Conservative public-data classification only.

    GitHub author_association is not an employer field. We use it only to infer
    whether the author appears connected to the repository or external to it.
    """
    association = (association or "NONE").upper()
    if login.lower().endswith("[bot]"):
        return "bot"
    if association in {"OWNER", "MEMBER", "COLLABORATOR"}:
        return "project-connected"
    if association in {"CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR"}:
        return "contributor"
    return "external-or-unclassified"


def analyse_repo(repo_record: dict, since: datetime) -> dict:
    repo = repo_record["repository"]
    since_date = since.date().isoformat()

    issue_q = f"repo:{repo} is:issue created:>={since_date}"
    pr_q = f"repo:{repo} is:pr created:>={since_date}"
    closed_issue_q = f"repo:{repo} is:issue closed:>={since_date}"
    merged_pr_q = f"repo:{repo} is:pr is:merged merged:>={since_date}"

    issue_items = search_items(issue_q, 100)
    pr_items = search_items(pr_q, 100)
    issues_created = search_count(issue_q)
    prs_created = search_count(pr_q)
    issues_closed = search_count(closed_issue_q)
    prs_merged = search_count(merged_pr_q)

    issue_authors = Counter()
    author_classes = Counter()
    responded = 0
    assigned = 0
    response_hours = []

    for item in issue_items:
        user = (item.get("user") or {}).get("login") or "unknown"
        issue_authors[user] += 1
        author_classes[classify_author(user, repo_owner(repo), item.get("author_association"))] += 1
        if item.get("assignee") or item.get("assignees"):
            assigned += 1
        if int(item.get("comments") or 0) > 0:
            responded += 1
            try:
                comments_url = item.get("comments_url")
                comments = request_json(comments_url) if comments_url else []
                if comments:
                    created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                    first = datetime.fromisoformat(comments[0]["created_at"].replace("Z", "+00:00"))
                    response_hours.append(max(0.0, (first - created).total_seconds() / 3600.0))
            except Exception:
                pass

    pr_authors = Counter()
    for item in pr_items:
        user = (item.get("user") or {}).get("login") or "unknown"
        pr_authors[user] += 1

    distinct_issue_authors = len(issue_authors)
    distinct_pr_authors = len(pr_authors)
    external = author_classes.get("external-or-unclassified", 0)
    connected = author_classes.get("project-connected", 0) + author_classes.get("contributor", 0)
    author_total = max(1, sum(author_classes.values()))
    external_share = external / author_total

    response_rate = responded / max(1, len(issue_items))
    assignment_rate = assigned / max(1, len(issue_items))
    closure_ratio = issues_closed / max(1, issues_created)
    merge_ratio = prs_merged / max(1, prs_created)
    median_response_h = None
    if response_hours:
        s = sorted(response_hours)
        m = len(s) // 2
        median_response_h = s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2

    # Experimental internal score. High backlog is NOT rewarded. The score favors
    # breadth, recent participation, issue handling and PR throughput.
    breadth = clamp(22 * safe_log(distinct_issue_authors + distinct_pr_authors))
    participation = clamp(70 * external_share + 30 * min(1.0, connected / author_total))
    responsiveness = clamp(55 * response_rate + 25 * assignment_rate + 20 * min(1.0, closure_ratio))
    throughput = clamp(55 * min(1.0, merge_ratio) + 25 * safe_log(prs_created) + 20 * safe_log(issues_closed))
    score = round(0.30 * breadth + 0.20 * participation + 0.30 * responsiveness + 0.20 * throughput, 1)

    return {
        "repository": repo,
        "organization": repo_record.get("organization", ""),
        "tier": repo_record.get("tier", ""),
        "radar_score": float(repo_record.get("petrotech_radar_score") or 0),
        "window_start": since.isoformat(),
        "issues_created": issues_created,
        "issues_closed": issues_closed,
        "prs_created": prs_created,
        "prs_merged": prs_merged,
        "sampled_recent_issues": len(issue_items),
        "distinct_issue_authors": distinct_issue_authors,
        "distinct_pr_authors": distinct_pr_authors,
        "external_or_unclassified_issue_share": round(external_share, 3),
        "project_connected_issue_events": connected,
        "response_rate_sample": round(response_rate, 3),
        "assignment_rate_sample": round(assignment_rate, 3),
        "median_first_response_hours_sample": round(median_response_h, 1) if median_response_h is not None else None,
        "issue_closure_ratio": round(closure_ratio, 3),
        "pr_merge_ratio": round(merge_ratio, 3),
        "community_activity_score_experimental": score,
        "top_issue_authors_sample": issue_authors.most_common(8),
        "top_pr_authors_sample": pr_authors.most_common(8),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20, help="Number of radar repositories to analyse")
    ap.add_argument("--days", type=int, default=90, help="Lookback window in days")
    args = ap.parse_args()

    if not RADAR.exists():
        raise SystemExit(f"Missing {RADAR}. Run the PetroTechRadar refresh first.")

    payload = json.loads(RADAR.read_text(encoding="utf-8"))
    repos = payload.get("repositories", [])
    repos = sorted(
        repos,
        key=lambda r: float(r.get("petrotech_radar_score") or 0),
        reverse=True,
    )[: max(1, args.top)]

    since = NOW - timedelta(days=max(1, args.days))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    results = []
    errors = []

    for i, record in enumerate(repos, 1):
        repo = record.get("repository", "")
        if not repo:
            continue
        print(f"[{i}/{len(repos)}] {repo}")
        try:
            results.append(analyse_repo(record, since))
        except Exception as exc:
            errors.append({"repository": repo, "error": str(exc)})
            print(f"  ERROR: {exc}")
        time.sleep(0.15)

    results.sort(key=lambda r: r["community_activity_score_experimental"], reverse=True)

    json_out = {
        "generated_at": NOW.isoformat(),
        "experimental": True,
        "public_site_enabled": False,
        "lookback_days": args.days,
        "repository_sample_size": len(repos),
        "successful": len(results),
        "errors": errors,
        "method_note": (
            "Experimental internal metric. GitHub author_association is used only as a repository relationship signal, "
            "not as employer identity. Open issue counts alone are not treated as quality or activity scores."
        ),
        "repositories": results,
    }
    (OUTDIR / "community_activity.json").write_text(json.dumps(json_out, indent=2), encoding="utf-8")

    if results:
        fields = [k for k in results[0].keys() if not k.startswith("top_")]
        with (OUTDIR / "community_activity.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in results:
                w.writerow({k: r.get(k) for k in fields})

    md = [
        "# Internal Community Activity Analysis",
        "",
        f"Generated: {NOW.isoformat()}",
        f"Lookback window: {args.days} days",
        "",
        "> Experimental internal analysis. Do not interpret open issue volume as software quality.",
        "",
        "| Rank | Repository | Score | Issue authors | PR authors | Issues created | Issues closed | PRs created | PRs merged | Response rate |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(results, 1):
        md.append(
            f"| {i} | {r['repository']} | {r['community_activity_score_experimental']:.1f} | "
            f"{r['distinct_issue_authors']} | {r['distinct_pr_authors']} | {r['issues_created']} | "
            f"{r['issues_closed']} | {r['prs_created']} | {r['prs_merged']} | {r['response_rate_sample']:.0%} |"
        )
    md += [
        "",
        "## Interpretation",
        "",
        "The score combines contributor breadth, repository-connected vs external participation, sampled issue response/assignment behavior, issue closure activity, and PR merge throughput. It is deliberately separate from the public PetroTechRadar score until the methodology has been validated.",
        "",
    ]
    (OUTDIR / "README.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\nWrote internal outputs to {OUTDIR.relative_to(ROOT)}")
    if errors:
        print(f"Completed with {len(errors)} errors; see community_activity.json")


if __name__ == "__main__":
    main()
