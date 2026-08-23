#!/usr/bin/env python3
"""Keep the GitHub Pages landing page synchronized with generated live data."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"


def main():
    text = INDEX.read_text(encoding="utf-8")

    # Add the Community Pulse navigation entry once.
    if 'href="issues.html"' not in text:
        old = '<button class="navlink" type="button" data-nav="repositories">Repositories</button><a class="navlink" href="papers.html">Papers</a>'
        new = '<button class="navlink" type="button" data-nav="repositories">Repositories</button><a class="navlink" href="issues.html">Community Pulse</a><a class="navlink" href="papers.html">Papers</a>'
        text = text.replace(old, new, 1)

    # Force catalogue fetches to bypass stale GitHub Pages/browser copies.
    text = text.replace("fetch('./data/radar.json',{cache:'no-store'})", "fetch('./data/radar.json?v='+Date.now(),{cache:'reload'})")
    text = text.replace("fetch('./data/papers.json',{cache:'no-store'})", "fetch('./data/papers.json?v='+Date.now(),{cache:'reload'})")

    # Add an authoritative stats overlay. This intentionally runs after the
    # existing dashboard loader so README and landing-page counts share the
    # same generated stats.json source of truth.
    marker = 'id="ptr-live-stats-sync"'
    if marker not in text:
        script = r'''<script id="ptr-live-stats-sync">
(()=>{function apply(){fetch('./data/stats.json?v='+Date.now(),{cache:'reload'}).then(r=>r.ok?r.json():null).then(s=>{if(!s)return;const set=(id,v)=>{const e=document.getElementById(id);if(e&&v!==undefined&&v!==null)e.textContent=v};set('ptr-count-repos',s.repository_count);set('ptr-count-core',s.tiers&&s.tiers.Core);set('ptr-count-emerging',s.tiers&&s.tiers.Emerging);set('ptr-count-research',s.tiers&&s.tiers.Research)}).catch(()=>{})}window.addEventListener('load',()=>{apply();setTimeout(apply,800);setTimeout(apply,2500)})})();
</script>'''
        if '</body>' in text:
            text = text.replace('</body>', script + '\n</body>', 1)
        else:
            text += '\n' + script + '\n'

    INDEX.write_text(text, encoding="utf-8")
    print("Dashboard navigation and live statistics synchronized.")


if __name__ == "__main__":
    main()
