#!/usr/bin/env python3
"""Build a public API/capability index for PetroTechRadar repositories.

V0.1 intentionally indexes a representative test set. The extractor prefers
public/documented APIs and avoids indexing every internal helper.
"""
from __future__ import annotations

import ast
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "data"
TOKEN = os.getenv("GITHUB_TOKEN", "")
MODE = os.getenv("CAPABILITY_MODE", "test")

TEST_REPOS = [
    "equinor/segyio",
    "trhallam/segysak",
    "PyLops/pylops",
    "simpeg/simpeg",
    "devitocodes/devito",
    "ar4/deepwave",
    "OPM/opm-simulators",
    "OPM/ResInsight",
    "GEOS-DEV/GEOS",
    "equinor/xtgeo",
]

# In all-mode we start from the live radar and target established/core repos
# from named organizations. This can be broadened after reviewing extraction QC.
MAJOR_ORGS = {
    "Equinor", "OPM", "NVIDIA", "GEOS Consortium", "SimPEG", "PyLops",
    "GemPy", "pyGIMLi", "Loop3D", "Devito", "OpendTect", "SEG-Y",
}

CAPABILITY_TERMS = {
    "SEG-Y I/O": ["seg-y", "segy", "trace header", "binary header"],
    "seismic processing": ["seismic processing", "filter", "stack", "migration"],
    "inversion": ["inversion", "inverse problem", "adjoint", "gradient"],
    "FWI": ["full waveform inversion", "fwi"],
    "wave simulation": ["wave equation", "wave propagation", "acoustic", "elastic"],
    "reservoir simulation": ["reservoir simulation", "black oil", "compositional", "flow simulator"],
    "geomechanics": ["geomechanics", "poroelastic", "mechanics"],
    "geological modelling": ["geological model", "structural model", "implicit modelling"],
    "grids and surfaces": ["grid", "surface", "mesh"],
    "well data": ["well log", "well data", "trajectory", "well path"],
    "visualization": ["visualization", "viewer", "plot"],
    "data assimilation": ["data assimilation", "ensemble smoother", "history matching"],
}


def api(url: str):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "PetroTechRadar-CapabilityIndexer/0.1"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def raw(url: str) -> str:
    headers = {"User-Agent": "PetroTechRadar-CapabilityIndexer/0.1"}
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def get_repo_meta(repo: str):
    return api(f"https://api.github.com/repos/{repo}")


def get_tree(repo: str, branch: str):
    ref = api(f"https://api.github.com/repos/{repo}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1")
    return ref.get("tree", [])


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
            out.append({"name": f"{mod}.{node.name}" if mod else node.name, "kind": "function", "signature": py_signature(node), "description": doc.split("\n\n")[0][:500], "source_file": path})
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            doc = ast.get_docstring(node) or ""
            out.append({"name": f"{mod}.{node.name}" if mod else node.name, "kind": "class", "signature": node.name, "description": doc.split("\n\n")[0][:500], "source_file": path})
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                    cdoc = ast.get_docstring(child) or ""
                    out.append({"name": f"{mod}.{node.name}.{child.name}", "kind": "method", "signature": py_signature(child), "description": cdoc.split("\n\n")[0][:500], "source_file": path})
    return out


def extract_cpp(path: str, source: str):
    out = []
    # Conservative public declaration matcher for headers; skips operators/macros.
    rx = re.compile(r"^[ \t]*(?:inline\s+|static\s+|virtual\s+|constexpr\s+)*([\w:<>,*&\s]+?)\s+([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*(?:const\s*)?(?:noexcept\s*)?;", re.M)
    for ret, name, args in rx.findall(source):
        if name.startswith("_") or name in {"if", "for", "while", "switch"}: continue
        out.append({"name": name, "kind": "function/declaration", "signature": f"{name}({re.sub(r'\\s+', ' ', args).strip()})", "description": "", "source_file": path})
    return out[:250]


def extract_java(path: str, source: str):
    out = []
    rx = re.compile(r"public\s+(?:static\s+)?(?:final\s+)?[\w<>\[\], ?]+\s+([A-Za-z_]\w*)\s*\(([^)]*)\)")
    for name, args in rx.findall(source):
        if name.startswith("_"): continue
        out.append({"name": name, "kind": "method", "signature": f"{name}({re.sub(r'\\s+', ' ', args).strip()})", "description": "", "source_file": path})
    return out[:250]


def extract_ts(path: str, source: str):
    out = []
    rx = re.compile(r"export\s+(?:async\s+)?(?:function|class)\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?")
    for name, args in rx.findall(source):
        out.append({"name": name, "kind": "export", "signature": f"{name}({re.sub(r'\\s+', ' ', args).strip()})" if args else name, "description": "", "source_file": path})
    return out[:250]


def infer_capabilities(text: str):
    low = text.lower()
    return [cap for cap, terms in CAPABILITY_TERMS.items() if any(t in low for t in terms)]


def candidate_files(tree):
    files = [x["path"] for x in tree if x.get("type") == "blob" and x.get("size", 0) <= 250_000]
    selected = []
    for p in files:
        low = p.lower()
        base = low.rsplit("/", 1)[-1]
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
    # Keep CI/API cost bounded. Public API quality matters more than exhaustive internals.
    return selected[:40]


def index_repo(repo: str):
    print(f"Indexing {repo}", flush=True)
    meta = get_repo_meta(repo)
    branch = meta.get("default_branch", "main")
    tree = get_tree(repo, branch)
    readme = get_readme(repo)
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
    # Prefer documented symbols, then keep a capped, deduplicated public API sample.
    dedup = {}
    for f in funcs:
        key = (f["name"], f.get("signature", ""))
        if key not in dedup or (not dedup[key].get("description") and f.get("description")):
            dedup[key] = f
    funcs = sorted(dedup.values(), key=lambda f: (0 if f.get("description") else 1, f["name"]))[:500]
    combined = "\n".join([meta.get("description") or "", readme[:120_000]] + [f.get("description", "") for f in funcs if f.get("description")])
    caps = infer_capabilities(combined)
    return {
        "repository": repo,
        "url": meta.get("html_url"),
        "language": meta.get("language"),
        "description": meta.get("description"),
        "default_branch": branch,
        "capabilities": caps,
        "public_api_count": len(funcs),
        "functions": funcs,
    }


def choose_repos():
    if MODE == "test":
        return TEST_REPOS
    radar = json.loads((OUT_DIR / "radar.json").read_text(encoding="utf-8"))
    repos = []
    for r in radar.get("repositories", []):
        if r.get("tier") == "Core" and r.get("organization") in MAJOR_ORGS:
            repos.append(r["repository"])
    return sorted(set(repos))


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
        "generated_at": generated_at,
        "mode": MODE,
        "repository_count": len(indexed),
        "errors": errors,
        "repositories": [{k: v for k, v in r.items() if k != "functions"} for r in indexed],
    }
    functions = {
        "generated_at": generated_at,
        "mode": MODE,
        "repository_count": len(indexed),
        "function_count": sum(len(r["functions"]) for r in indexed),
        "repositories": [{"repository": r["repository"], "functions": r["functions"]} for r in indexed],
    }
    (OUT_DIR / "capabilities.json").write_text(json.dumps(capabilities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "functions.json").write_text(json.dumps(functions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Indexed {len(indexed)} repos, {functions['function_count']} public API symbols, {len(errors)} errors")


if __name__ == "__main__":
    main()
