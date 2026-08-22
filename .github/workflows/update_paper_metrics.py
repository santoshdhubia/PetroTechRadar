#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "catalog" / "PAPERS_WITH_CODE.csv"
NOW = datetime.now(timezone.utc)
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

TITLE_THRESHOLD = 0.88
OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO", "").strip()

def http_json(url, github=False, retries=3):
    headers = {"User-Agent": "PetroTechRadar/1.0"}
    if OPENALEX_MAILTO and "openalex.org" in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}mailto={urllib.parse.quote(OPENALEX_MAILTO)}"

    req = urllib.request.Request(url, headers=headers)

    if github:
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if TOKEN:
            req.add_header("Authorization", f"Bearer {TOKEN}")

    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_err

def normalize_doi(doi):
    doi = (doi or "").strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    return doi.strip().lower()

def normalize_title(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())

def title_similarity(a, b):
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()

def openalex_by_doi(doi):
    doi = normalize_doi(doi)
    if not doi:
        return None

    # 1) Direct work lookup
    try:
        return http_json(
            "https://api.openalex.org/works/https://doi.org/" +
            urllib.parse.quote(doi, safe="/:")
        )
    except Exception:
        pass

    # 2) DOI filter fallback
    try:
        data = http_json(
            "https://api.openalex.org/works?filter=doi:" +
            urllib.parse.quote(doi, safe="/:")
        )
        results = data.get("results", [])
        if results:
            return results[0]
    except Exception:
        pass

    return None

def openalex_by_title(title, expected_year):
    if not title:
        return None, "unverified"

    try:
        data = http_json(
            "https://api.openalex.org/works?search=" +
            urllib.parse.quote(title) +
            "&per-page=10"
        )
    except Exception:
        return None, "unverified"

    best = None
    best_score = 0.0

    for item in data.get("results", []):
        sim = title_similarity(title, item.get("title", ""))
        yr = item.get("publication_year")
        year_ok = (
            not expected_year or
            not yr or
            abs(int(expected_year) - int(yr)) <= 1
        )
        if year_ok and sim > best_score:
            best = item
            best_score = sim

    if best is not None and best_score >= TITLE_THRESHOLD:
        return best, f"title:{best_score:.3f}"

    return None, "unverified"

def openalex_match(doi, title, expected_year):
    work = openalex_by_doi(doi)
    if work:
        return work, "doi"

    return openalex_by_title(title, expected_year)

def citation_score(c):
    return round(min(100, 33.3 * math.log10(max(c, 0) + 1)), 1)

def velocity_score(v):
    return round(min(100, 50 * math.log10(max(v, 0) + 1)), 1)

def repro_score(v):
    return {"Very High": 100, "High": 88, "Medium": 70, "Low": 45}.get(v, 60)

def github_score(stars, forks, push):
    traction = min(
        100,
        22 * math.log10(stars + 1) +
        14 * math.log10(forks + 1)
    )

    recency = 0
    if push:
        dt = datetime.fromisoformat(push.replace("Z", "+00:00"))
        days = max((NOW - dt).total_seconds() / 86400, 0)
        recency = max(0, 100 - min(days, 730) / 7.3)

    return round(0.65 * traction + 0.35 * recency, 1)

with CAT.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    status = []

    # Preserve previous verified citation values if OpenAlex is temporarily unavailable.
    previous = {
        "citations": r.get("citations", ""),
        "citations_per_year": r.get("citations_per_year", ""),
        "openalex_id": r.get("openalex_id", ""),
        "citation_score": r.get("citation_score", ""),
        "citation_velocity_score": r.get("citation_velocity_score", ""),
    }

    try:
        work, match_type = openalex_match(
            r.get("doi", ""),
            r.get("paper_title", ""),
            r.get("year", "")
        )

        if work:
            citations = int(work.get("cited_by_count", 0) or 0)
            age = max(NOW.year - int(r["year"]) + 1, 1)
            cpy = round(citations / age, 2)

            r["citations"] = citations
            r["citations_per_year"] = cpy
            r["openalex_id"] = work.get("id", "")
            r["citation_score"] = citation_score(citations)
            r["citation_velocity_score"] = velocity_score(cpy)
            status.append("citation-ok:" + match_type)
        else:
            if previous["citations"] not in ("", None):
                status.append("citation-stale-preserved")
            else:
                r["citations"] = ""
                r["citations_per_year"] = ""
                r["openalex_id"] = ""
                r["citation_score"] = ""
                r["citation_velocity_score"] = ""
                status.append("citation-unverified")
    except Exception:
        if previous["citations"] not in ("", None):
            status.append("citation-stale-preserved")
        else:
            status.append("citation-unavailable")

    try:
        m = http_json(
            "https://api.github.com/repos/" + r["repository"],
            github=True
        )
        stars = int(m.get("stargazers_count", 0) or 0)
        forks = int(m.get("forks_count", 0) or 0)
        push = m.get("pushed_at") or ""

        r["repo_stars"] = stars
        r["repo_forks"] = forks
        r["repo_last_push"] = push
        r["repo_license"] = ((m.get("license") or {}).get("spdx_id") or "")
        r["github_score"] = github_score(stars, forks, push)
        status.append("github-ok")
    except Exception:
        status.append("github-error")

    r["reproducibility_score"] = repro_score(r.get("reproducibility", ""))

    tech = float(r.get("technical_relevance") or 0)
    repro = float(r.get("reproducibility_score") or 0)
    gh = float(r.get("github_score") or 0)
    venue = float(r.get("venue_score") or 0)
    cs = float(r.get("citation_score") or 0)
    cv = float(r.get("citation_velocity_score") or 0)

    code = {
        "Very High": 100,
        "High": 90,
        "Medium": 72,
        "Low": 45
    }.get(r.get("code_health", ""), 60)

    r["papers_with_code_score"] = round(
        .20 * tech +
        .20 * repro +
        .15 * code +
        .10 * venue +
        .15 * cs +
        .10 * cv +
        .10 * gh,
        1
    )

    r["metrics_status"] = ";".join(status)
    r["last_verified"] = NOW.date().isoformat()

with CAT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
