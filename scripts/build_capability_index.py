#!/usr/bin/env python3
"""Build a quality-ranked public API/capability index for PetroTechRadar.

The index is intentionally selective: it prefers exported/documented APIs,
labels API quality, suppresses obvious internal helpers, and separates primary
capabilities from broader secondary associations.
"""
from __future__ import annotations

import ast
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "data"
TOKEN = os.getenv("GITHUB_TOKEN", "")
MODE = os.getenv("CAPABILITY_MODE", "test")

TEST_REPOS = [
    "equinor/segyio", "trhallam/segysak", "PyLops/pylops", "simpeg/simpeg",
    "devitocodes/devito", "ar4/deepwave", "OPM/opm-simulators",
    "OPM/ResInsight", "GEOS-DEV/GEOS", "equinor/xtgeo",
]

MAJOR_ORGS = {
    "Equinor", "OPM", "NVIDIA", "GEOS Consortium", "SimPEG", "PyLops",
    "GemPy", "pyGIMLi", "Loop3D", "Devito", "OpendTect", "SEG-Y",
}

CAPABILITY_TERMS = {
    "SEG-Y I/O": ["seg-y", "segy", "trace header", "binary header"],
    "seismic processing": ["seismic processing", "filtering", "stacking", "migration"],
    "inversion": ["inversion", "inverse problem", "adjoint", "gradient based"],
    "FWI": ["full waveform inversion", "fwi"],
    "wave simulation": ["wave equation", "wave propagation", "acoustic", "elastic wave"],
    "reservoir simulation": ["reservoir simulation", "black oil", "compositional", "flow simulator"],
    "geomechanics": ["geomechanics", "poroelastic", "rock mechanics"],
    "geological modelling": ["geological model", "structural model", "implicit modelling"],
    "grids and surfaces": ["grid model", "surface model", "corner point grid", "mesh"],
    "well data": ["well log", "well data", "trajectory", "well path"],
    "visualization": ["visualization", "3d viewer", "interactive viewer"],
    "data assimilation": ["data assimilation", "ensemble smoother", "history matching"],
}

GENERIC_LOW_VALUE = {
    "keys", "values", "items", "update", "close", "flush", "reload", "sort",
    "copy", "get", "set", "read", "write", "run", "main", "size", "begin", "end",
}


def api(url: str):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "PetroTechRadar-CapabilityIndexer/0.2"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def raw(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "PetroTechRadar-CapabilityIndexer/0.2"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def get_repo_meta(repo: str):
    return api(f"https://api.github.com/repos/{repo}")


def get_tree(repo: str, branch: str):
    d = api(f"https://api.github.com/repos/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1")
    return d.get("tree", [])


def get_readme(repo: str) -> str:
    try:
        d = api(f"https://api.github.com/repos/{repo}/readme")
        return raw(d["download_url"]) if d.get("download_url") else ""
    except Exception:
        return ""


def module_name(path: str) -> str:
    p = path.replace("/", ".")
    for prefix in ("src.", "python."):
        if p.startswith(prefix):
            p = p[len(prefix):]
    return re.sub(r"\.(py|pyi)$", "", p).replace(".__init__", "")


def py_signature(node) -> str:
    args = []
    a = node.args
    positional = list(a.posonlyargs) + list(a.args)
    defaults_pad = [None] * (len(positional) - len(a.defaults)) + list(a.defaults)
    for arg, default in zip(positional, defaults_pad):
        s = arg.arg
        if arg.annotation:
            try: s += ": " + ast.unparse(arg.annotation)
            except Exception: pass
        if default is not None:
            try: s += "=" + ast.unparse(default)
            except Exception: s += "=..."
        args.append(s)
    if a.vararg: args.append("*" + a.vararg.arg)
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        s = arg.arg
        if default is not None:
            try: s += "=" + ast.unparse(default)
            except Exception: s += "=..."
        args.append(s)
    if a.kwarg: args.append("**" + a.kwarg.arg)
    return f"{node.name}({', '.join(args)})"


def entry(name, kind, signature, description, path):
    return {
        "name": name,
        "kind": kind,
        "signature": signature,
        "description": description.strip()[:500],
        "source_file": path,
    }


def extract_python(path: str, source: str):
    out = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    mod = module_name(path)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            doc = ast.get_docstring(node) or ""
            out.append(entry(f"{mod}.{node.name}" if mod else node.name, "function", py_signature(node), doc.split("\n\n")[0], path))
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            doc = ast.get_docstring(node) or ""
            cname = f"{mod}.{node.name}" if mod else node.name
            out.append(entry(cname, "class", node.name, doc.split("\n\n")[0], path))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                    cdoc = ast.get_docstring(child) or ""
                    out.append(entry(f"{cname}.{child.name}", "method", py_signature(child), cdoc.split("\n\n")[0], path))
    return out


def extract_cpp(path: str, source: str):
    out = []
    rx = re.compile(r"^[ \t]*(?:inline\s+|static\s+|virtual\s+|constexpr\s+)*([\w:<>,*&\s]+?)\s+([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*(?:const\s*)?(?:noexcept\s*)?;", re.M)
    for _, name, args in rx.findall(source):
        if name.startswith("_") or name in {"if", "for", "while", "switch"}: continue
        out.append(entry(name, "function/declaration", f"{name}({re.sub(r'\s+', ' ', args).strip()})", "", path))
    return out[:300]


def extract_java(path: str, source: str):
    out = []
    rx = re.compile(r"public\s+(?:static\s+)?(?:final\s+)?[\w<>\[\], ?]+\s+([A-Za-z_]\w*)\s*\(([^)]*)\)")
    for name, args in rx.findall(source):
        out.append(entry(name, "method", f"{name}({re.sub(r'\s+', ' ', args).strip()})", "", path))
    return out[:300]


def extract_ts(path: str, source: str):
    out = []
    rx = re.compile(r"export\s+(?:async\s+)?(?:function|class)\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?")
    for name, args in rx.findall(source):
        sig = f"{name}({re.sub(r'\s+', ' ', args).strip()})" if args else name
        out.append(entry(name, "export", sig, "", path))
    return out[:300]


def simple_name(symbol: str) -> str:
    return symbol.rsplit(".", 1)[-1]


def classify_symbol(f: dict, readme_low: str) -> tuple[str, int, list[str]]:
    """Return (api_level, quality_score, evidence)."""
    evidence = []
    score = 0
    desc = (f.get("description") or "").strip()
    name = f["name"]
    short = simple_name(name)
    path = f.get("source_file", "").lower()

    if desc:
        score += 3
        evidence.append("docstring/documentation")
    if len(desc) >= 40:
        score += 1
    # Exact-ish symbol mention in README is a strong public-use signal.
    if len(short) >= 4 and re.search(rf"(?<!\w){re.escape(short.lower())}(?!\w)", readme_low):
        score += 4
        evidence.append("mentioned in README")
    if path.endswith("/__init__.py") or path.endswith("/index.ts") or path.endswith("/index.js") or "/api/" in path:
        score += 3
        evidence.append("export/API entrypoint")
    if "/include/" in path:
        score += 2
        evidence.append("public header")
    if "internal use" in desc.lower() or "/internal/" in path or "/detail/" in path:
        score -= 5
        evidence.append("internal hint")
    if short.lower() in GENERIC_LOW_VALUE and not desc and "mentioned in README" not in evidence:
        score -= 3
        evidence.append("generic undocumented method")

    if score >= 6:
        return "primary_public", score, evidence
    if score >= 2:
        return "documented_public", score, evidence
    return "internal_or_low_value", score, evidence


def infer_capabilities(description: str, readme: str):
    desc_low = (description or "").lower()
    readme_low = readme.lower()
    primary, secondary, scores = [], [], {}
    for cap, terms in CAPABILITY_TERMS.items():
        desc_hits = sum(1 for t in terms if t in desc_low)
        readme_hits = sum(readme_low.count(t) for t in terms)
        score = desc_hits * 5 + min(readme_hits, 5)
        scores[cap] = score
        if desc_hits or readme_hits >= 2:
            primary.append(cap)
        elif readme_hits == 1:
            secondary.append(cap)
    return primary, secondary, {k: v for k, v in scores.items() if v > 0}


def candidate_files(tree):
    files = [x["path"] for x in tree if x.get("type") == "blob" and x.get("size", 0) <= 250_000]
    selected = []
    for p in files:
        low = p.lower(); base = low.rsplit("/", 1)[-1]
        if any(part in low for part in ("/test/", "/tests/", "/example/", "/examples/", "/vendor/", "/third_party/", "/build/")):
            continue
        if p.endswith((".py", ".pyi")) and ("/__init__.py" in low or "/api" in low or "/io" in low or "/tools" in low or "/core" in low or low.count("/") <= 3):
            selected.append(p)
        elif p.endswith((".h", ".hpp", ".hh")) and ("include/" in low or "/api" in low):
            selected.append(p)
        elif p.endswith(".java") and ("src/main/" in low or low.count("/") <= 4):
            selected.append(p)
        elif p.endswith((".ts", ".tsx", ".js")) and ("src/" in low and ("index." in base or "api" in low)):
            selected.append(p)
    return selected[:50]


def index_repo(repo: str):
    print(f"Indexing {repo}", flush=True)
    meta = get_repo_meta(repo)
    branch = meta.get("default_branch", "main")
    tree = get_tree(repo, branch)
    readme = get_readme(repo)
    readme_low = readme.lower()
    funcs = []
    for path in candidate_files(tree):
        url = f"https://raw.githubusercontent.com/{repo}/{urllib.parse.quote(branch, safe='')}/{urllib.parse.quote(path, safe='/')}"
        try:
            src = raw(url)
        except Exception as e:
            print(f"  skip {path}: {e}")
            continue
        if path.endswith((".py", ".pyi")): funcs.extend(extract_python(path, src))
        elif path.endswith((".h", ".hpp", ".hh")): funcs.extend(extract_cpp(path, src))
        elif path.endswith(".java"): funcs.extend(extract_java(path, src))
        elif path.endswith((".ts", ".tsx", ".js")): funcs.extend(extract_ts(path, src))
        time.sleep(0.02)

    dedup = {}
    for f in funcs:
        key = (f["name"], f.get("signature", ""))
        if key not in dedup or (not dedup[key].get("description") and f.get("description")):
            dedup[key] = f

    classified = []
    level_counts = {"primary_public": 0, "documented_public": 0, "internal_or_low_value": 0}
    for f in dedup.values():
        level, score, evidence = classify_symbol(f, readme_low)
        f["api_level"] = level
        f["quality_score"] = score
        f["evidence"] = evidence
        level_counts[level] += 1
        classified.append(f)

    # Publish only usable API entries; low-value/internal entries remain summarized in counts.
    usable = [f for f in classified if f["api_level"] != "internal_or_low_value"]
    usable.sort(key=lambda f: (-f["quality_score"], 0 if f.get("description") else 1, f["name"]))
    usable = usable[:500]

    primary_caps, secondary_caps, cap_scores = infer_capabilities(meta.get("description") or "", readme[:150_000])
    return {
        "repository": repo,
        "url": meta.get("html_url"),
        "language": meta.get("language"),
        "description": meta.get("description"),
        "default_branch": branch,
        "primary_capabilities": primary_caps,
        "secondary_capabilities": secondary_caps,
        "capability_scores": cap_scores,
        "public_api_count": len(usable),
        "api_level_counts": level_counts,
        "functions": usable,
    }


def choose_repos():
    if MODE == "test":
        return TEST_REPOS
    radar = json.loads((OUT_DIR / "radar.json").read_text(encoding="utf-8"))
    return sorted({r["repository"] for r in radar.get("repositories", []) if r.get("tier") == "Core" and r.get("organization") in MAJOR_ORGS})


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    indexed, errors = [], []
    for repo in choose_repos():
        try:
            indexed.append(index_repo(repo))
        except Exception as e:
            print(f"ERROR {repo}: {e}", flush=True)
            errors.append({"repository": repo, "error": str(e)})
    generated_at = datetime.now(timezone.utc).isoformat()
    capabilities = {
        "generated_at": generated_at, "mode": MODE, "repository_count": len(indexed),
        "errors": errors,
        "repositories": [{k: v for k, v in r.items() if k != "functions"} for r in indexed],
    }
    functions = {
        "generated_at": generated_at, "mode": MODE, "repository_count": len(indexed),
        "function_count": sum(len(r["functions"]) for r in indexed),
        "repositories": [{"repository": r["repository"], "functions": r["functions"]} for r in indexed],
    }
    (OUT_DIR / "capabilities.json").write_text(json.dumps(capabilities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "functions.json").write_text(json.dumps(functions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Indexed {len(indexed)} repos, {functions['function_count']} usable public API symbols, {len(errors)} errors")


if __name__ == "__main__":
    main()
