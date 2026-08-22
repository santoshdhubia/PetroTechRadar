<div align="center">

# ⛽ PetroTechRadar

### Open-source & emerging technology radar for oil & gas, geoscience and subsurface engineering

**115 curated repositories · live GitHub metrics · AI/Agent radar · FWI/Seismic · Petrophysics · Reservoir · Drilling · OSDU · Geothermal**

[![Live Dashboard](https://img.shields.io/badge/Live%20Dashboard-Explore%20Radar-2ea44f?style=for-the-badge)](https://santoshdhubia.github.io/PetroTechRadar/)
[![Repository Matrix](https://img.shields.io/badge/Repository%20Matrix-CSV-blue?style=for-the-badge)](catalog/PETROTECHRADAR_V1.csv)
[![Weekly Refresh](https://img.shields.io/badge/Metrics-Weekly%20Refresh-orange?style=for-the-badge)](.github/workflows/refresh-radar.yml)

</div>

---

## What is PetroTechRadar?

**PetroTechRadar** tracks software being built across the oil & gas and subsurface technology ecosystem — from mature open-source foundations to new AI agents, MCP servers, research code, rapid prototypes and vibe-coded engineering tools.

> **Find what is useful, what is emerging, and what is worth watching.**

Unlike a traditional “awesome list”, PetroTechRadar combines **technical curation** with **live GitHub metrics** so established tools and newer high-potential projects can be compared more fairly.

---

## Radar Snapshot

| Metric | Current V1 |
|---|---:|
| **Repositories tracked** | **115** |
| **Core tools** | **32** |
| **Emerging / AI / vibe-coded** | **43** |
| **Research repositories** | **28** |
| **Reference resources** | **12** |
| **Metrics refresh** | **Weekly** |

---

## Explore the Radar

| Radar | What you will find |
|---|---|
| 🤖 **[AI Agents, MCP & Engineering Copilots](catalog/AI_AGENT_RADAR.md)** | Petroleum agents, reservoir copilots, drilling RAG, OSDU agents and MCP servers |
| 🌊 **[Seismic & Geophysics](catalog/SEISMIC_RADAR.md)** | FWI, RTM, inversion, SEG-Y, wave propagation, seismic ML and visualization |
| 🧪 **[Research Radar](catalog/RESEARCH_RADAR.md)** | Reproducible papers, datasets, research implementations and benchmarks |
| 🚀 **[Emerging & Vibe-Coded](catalog/EMERGING_RADAR.md)** | New apps, experimental tools, rapid prototypes and early-stage projects |
| 🏆 **[Top Ranked Repositories](catalog/TOP_REPOSITORIES.md)** | Highest PetroTechRadar scores based on technical relevance + activity |
| 📊 **[Full Live Matrix](catalog/PETROTECHRADAR_V1.csv)** | Complete repository dataset and metrics |

---

## Technology Areas

| Area | Coverage |
|---|---|
| 🌊 **Seismic & Imaging** | FWI, RTM, inversion, velocity modelling, SEG-Y, seismic ML |
| 🧾 **Petrophysics** | LAS, well logs, saturation, permeability, rock physics |
| 🛢 **Reservoir** | Simulation, PVT, DCA, material balance, EOR, surrogate models |
| 🛠 **Drilling & Wells** | MWD/LWD, ROP, pore pressure, drilling reports, wellbore analytics |
| 🤖 **AI / Agents** | LLMs, MCP, RAG, multi-agent systems, engineering copilots |
| 🗄 **Data & OSDU** | OSDU, interoperability, conversion, standards, semantic layers |
| 🌋 **Geothermal** | Prospectivity, seismicity, exploration and geothermal AI |
| 🗺 **Geoscience** | Interpretation, geostatistics, geological ML and visualization |
| ⚙ **Production** | Optimization, predictive maintenance and operational analytics |

---

## Featured Emerging Projects

| Project | Area | Why it is interesting |
|---|---|---|
| **[opm-ai](https://github.com/pranay-gpt/opm-ai)** | AI + Reservoir Simulation | Natural-language reservoir simulation around OPM Flow |
| **[pyrestoolbox-mcp](https://github.com/gabrielserrao/pyrestoolbox-mcp)** | MCP + Reservoir Engineering | Deterministic reservoir calculations exposed to AI assistants |
| **[petro-agent](https://github.com/OilCoder/petro-agent)** | AI + Petrophysics | Agentic LAS-to-petrophysics workflow with deterministic calculations |
| **[SiameseFit-pub](https://github.com/DeepWave-KAUST/SiameseFit-pub)** | FWI + ML | Learned seismic comparison for cycle-skipping mitigation |
| **[og-agentic-patterns](https://github.com/rkkalluri-dbx/og-agentic-patterns)** | Oil & Gas Agents | Agentic workflows for SCADA, alarms, wells and HSE |
| **[drilling-report-qa](https://github.com/mosalama74/drilling-report-qa)** | RAG + Drilling | Local document intelligence for Daily Drilling Reports |
| **[Seismo-Lingo](https://github.com/yberkayozkan/Seismo-Lingo-Smart-Geophysical-Assistant)** | AI + Geophysics | Natural-language interaction with SEG-Y and LAS |

---

## Live Repository Matrix

Every tracked repository can include:

**⭐ Stars · 🍴 Forks · 🧩 Issues · 👀 Watchers · 💻 Language · 📜 License · 📅 Created · 🔄 Last push · 📈 Stars/month · ⚡ Activity Score · 🎯 PetroTechRadar Score**

### **[→ Open the full PetroTechRadar matrix](catalog/PETROTECHRADAR_V1.csv)**

---

## How Ranking Works

GitHub popularity is useful, but **stars do not define technical value**.

```text
PetroTechRadar Score
├── 70% Curated technical tier
└── 30% GitHub activity
       ├── Stars
       ├── Forks
       ├── Last activity
       └── Issue activity
```

The GitHub component is logarithmically scaled so very large repositories do not overwhelm smaller but technically important projects.

---

## 🌐 Live Dashboard

Search, filter and sort the whole radar by:

**Domain · Tier · Stars · Stars/month · Latest activity · PetroTechRadar Score**

### **[Open PetroTechRadar Live Dashboard](https://santoshdhubia.github.io/PetroTechRadar/)**

> The dashboard becomes active after GitHub Pages is enabled.

---

## Radar Tiers

| Tier | Meaning |
|---|---|
| 🟢 **Core** | Established and practically useful software |
| 🔵 **Emerging** | AI, agents, MCP, new apps and rapid-development projects |
| 🟣 **Research** | Reproducible methods, datasets and research implementations |
| ⚪ **Reference** | Standards, tutorials, datasets and supporting tools |

---

## Automated Weekly Refresh

```text
GitHub repositories
        ↓
Live metadata collection
        ↓
Stars / forks / issues / activity
        ↓
PetroTechRadar score
        ↓
Markdown matrices + JSON + CSV
        ↓
GitHub Pages dashboard
```

Run manually from **Actions → Refresh PetroTechRadar → Run workflow**, or let the scheduled workflow refresh it each week.

---

## Repository Structure

```text
catalog/
├── PETROTECHRADAR_V1.csv
├── TOP_REPOSITORIES.md
├── EMERGING_RADAR.md
├── AI_AGENT_RADAR.md
├── SEISMIC_RADAR.md
└── RESEARCH_RADAR.md

scripts/
├── update_github_metrics.py
└── generate_outputs.py

docs/
├── index.html
└── data/
    ├── radar.json
    ├── radar.csv
    └── stats.json
```

---

## What belongs here?

Projects are considered when they offer meaningful relevance to:

**Exploration · Geophysics · Geology · Petrophysics · Reservoir Engineering · Drilling · Production · Subsurface Data · AI for Energy · Geothermal**

Priority is given to repositories with meaningful technical implementation, petroleum/subsurface-specific logic, reproducible research, active development, emerging AI/agent workflows, useful domain formats, or new approaches to engineering automation.

---

<div align="center">

### PetroTechRadar

**Discover what is being built for the subsurface.**

[Live Dashboard](https://santoshdhubia.github.io/PetroTechRadar/) ·
[Full Matrix](catalog/PETROTECHRADAR_V1.csv) ·
[Emerging Radar](catalog/EMERGING_RADAR.md) ·
[AI Agent Radar](catalog/AI_AGENT_RADAR.md)

</div>
