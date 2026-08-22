# PetroTechRadar

**A live technology radar for oil & gas, geoscience and subsurface software.**

PetroTechRadar tracks established open-source tools together with emerging AI-assisted, agentic, research and rapidly developed software for petroleum and subsurface workflows.

## Live radar

The repository maintains a refreshable matrix of **100+ curated repositories** with:

**Stars · Forks · Open issues · Watchers · Language · License · Created date · Last push · Repository age · Stars/month · GitHub Activity Score · PetroTechRadar Score**

GitHub metrics are refreshed automatically every week.

### Explore the matrices

- [Full live repository matrix](catalog/PETROTECHRADAR_V1.csv)
- [Top-ranked repositories](catalog/TOP_REPOSITORIES.md)
- [Emerging & vibe-coded radar](catalog/EMERGING_RADAR.md)
- [AI agents, MCP & engineering copilots](catalog/AI_AGENT_RADAR.md)
- [Seismic & geophysics radar](catalog/SEISMIC_RADAR.md)
- [Research radar](catalog/RESEARCH_RADAR.md)

## Interactive dashboard

After GitHub Pages is enabled, the dashboard is available at:

**https://santoshdhubia.github.io/PetroTechRadar/**

It supports search, domain/tier filters, and sorting by PetroTechRadar Score, stars, stars/month and latest activity.

## What makes PetroTechRadar different?

This is not only an “awesome list”. It separates **technical relevance** from **GitHub popularity**. A new petroleum-specific AI agent or FWI implementation may have few stars while still being technically important, so stars contribute to the ranking but do not dominate it.

## Radar tiers

| Tier | Meaning |
|---|---|
| **Core** | Established and practically useful software |
| **Emerging** | New AI, agentic, MCP, LLM and rapid-development projects |
| **Research** | Reproducible research code, datasets and technical methods |
| **Reference** | Useful standards, tutorials, supporting tools and datasets |

## Automated refresh

`.github/workflows/refresh-radar.yml` runs every Sunday and can also be started manually from **Actions → Refresh PetroTechRadar → Run workflow**.

It refreshes repository metrics, recalculates scores, regenerates Markdown matrices, regenerates the JSON/CSV dashboard feed, and commits only when data changes.

Automated refresh commits use the author name **Santosh Dhubia**.

## Status

**Private development repository — preparing for V1 public release.**
