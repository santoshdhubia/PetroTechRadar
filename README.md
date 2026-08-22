# PetroTechRadar

**A curated radar of emerging software, open-source projects, research code, AI-assisted tools and developer experiments for oil & gas, geoscience and subsurface engineering.**

PetroTechRadar is intended to answer a simple question:

> **What useful software is being built right now for oil & gas and subsurface workflows?**

The radar covers both established open-source foundations and early-stage projects, including small prototypes, research repositories, AI/ML experiments, agentic tools, data utilities, visualization applications and "vibe-coded" technical software.

## Scope

The catalogue is organized around the petroleum and subsurface workflow:

- Seismic processing, imaging, RTM, FWI and inversion
- Geological interpretation and geomodelling
- Petrophysics and well-log analysis
- Reservoir engineering and simulation
- Drilling and well engineering
- Production engineering and optimization
- Data standards, SEG-Y, LAS and OSDU
- AI/ML, LLMs, agents and document intelligence
- Visualization and technical applications
- Geothermal and adjacent subsurface technologies

## Radar classification

Each project is classified by **domain**, **maturity** and **emerging-technology signal**.

### Maturity

`Idea → Prototype → Research → Usable → Established → Mature`

### Emerging signal

Projects can be flagged as emerging where they involve newer development patterns such as:

`LLM` · `Agent` · `RAG` · `Machine Learning` · `Computer Vision` · `GPU/CUDA` · `Streamlit` · `Gradio` · `Rapid Prototype` · `Vibe Coding`

## Catalogue

The structured master catalogue is maintained in:

- [`catalog/projects.csv`](catalog/projects.csv)
- [`catalog/NEW_THIS_WEEK.md`](catalog/NEW_THIS_WEEK.md)
- [`catalog/EMERGING_PROJECTS.md`](catalog/EMERGING_PROJECTS.md)

## Categories

| Domain | Catalogue |
|---|---|
| Seismic & Imaging | [`categories/seismic.md`](categories/seismic.md) |
| Petrophysics | [`categories/petrophysics.md`](categories/petrophysics.md) |
| Reservoir Engineering | [`categories/reservoir.md`](categories/reservoir.md) |
| AI / ML / Agents | [`categories/ai-ml.md`](categories/ai-ml.md) |
| Drilling & Wells | [`categories/drilling.md`](categories/drilling.md) |
| Geological / Subsurface | [`categories/geology.md`](categories/geology.md) |
| Data / OSDU / Formats | [`categories/data.md`](categories/data.md) |
| Geothermal | [`categories/geothermal.md`](categories/geothermal.md) |

## Initial seed projects

| Project | Area | Why it is on the radar |
|---|---|---|
| [equinor/segyio](https://github.com/equinor/segyio) | Seismic data | Important open SEG-Y foundation |
| [OPM/ResInsight](https://github.com/OPM/ResInsight) | Reservoir | Mature open reservoir visualization |
| [agilescientific/welly](https://github.com/agilescientific/welly) | Petrophysics | Practical Python well-log toolkit |
| [NDF-Poli-USP/spyro](https://github.com/NDF-Poli-USP/spyro) | Seismic / FWI | Research wave-propagation and FWI software |
| [EugPal/reservoir-surrogate](https://github.com/EugPal/reservoir-surrogate) | AI / Reservoir | Emerging surrogate-model experiment |
| [Ursula-Iturraran/ML_full_wave_Inversion](https://github.com/Ursula-Iturraran/ML_full_wave_Inversion) | AI / FWI | ML + seismic inversion experiment |

## What belongs here?

A project is a good candidate if it is useful or potentially useful to petroleum, geoscience or subsurface professionals and falls into at least one of these groups:

1. Open-source technical software
2. Research code with practical potential
3. Newly developed AI/ML or LLM-based tools
4. Small experimental applications
5. Rapidly built / vibe-coded prototypes
6. Data conversion, QC or visualization utilities
7. New developer frameworks relevant to subsurface workflows

This repository is intentionally broader than a traditional "awesome list". The objective is not only to catalogue established software, but to identify **what is emerging**.

## Suggested project record

See [`templates/project-entry.md`](templates/project-entry.md).

## Status

**Private working repository — initial build.**
