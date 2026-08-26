# PetroTechRadar MCP — Cloudflare Worker

This is the first public remote MCP layer for PetroTechRadar. It is intentionally stateless and read-only. The Worker reads the same live JSON data that powers the PetroTechRadar website.

## MCP endpoint

After deployment, the endpoint will be:

`https://petrotechradar-mcp.<your-cloudflare-subdomain>.workers.dev/mcp`

The root URL and `/health` return a small JSON health response.

## Tools in v0.1

- `get_radar_stats` — current repository/tier/domain/organization counts
- `search_repositories` — keyword/capability search across the curated radar
- `get_repository` — full metadata for a repository
- `find_by_organization` — open-source projects from an organization/community
- `get_community_pulse` — unresolved issues opened in the last 7 days
- `find_contribution_opportunities` — open issues created in the last 6 months
- `search_papers` — search Papers with Code
- `recommend_repositories` — recommend available repositories for a described task

Function/API-level repository indexing is planned for a later version. v0.1 recommends tools using the curated repository metadata, focus descriptions, maturity tier and activity signals.

## Data sources

The Worker reads:

- `https://santoshdhubia.github.io/PetroTechRadar/data/radar.json`
- `https://santoshdhubia.github.io/PetroTechRadar/data/stats.json`
- `https://santoshdhubia.github.io/PetroTechRadar/data/issues.json`
- `https://santoshdhubia.github.io/PetroTechRadar/data/papers.json`

No database or AI inference is required for v0.1.

## Run locally

Requirements: Node.js 20+ (Node 22 recommended).

```bash
cd mcp-cloudflare
npm install
npm run typecheck
npm run dev
```

The Worker normally starts on `http://localhost:8787` and the MCP endpoint is:

`http://localhost:8787/mcp`

Test it with MCP Inspector:

```bash
npx @modelcontextprotocol/inspector@latest
```

Then connect the inspector to `http://localhost:8787/mcp` and choose **List Tools**.

## Deploy to Cloudflare Workers

Log in once:

```bash
npx wrangler login
```

Then deploy:

```bash
npm run deploy
```

Wrangler will return the public `workers.dev` URL. Append `/mcp` when configuring an MCP client.

## Initial deployment strategy

v0.1 is deliberately public and read-only. It does not require OAuth because it exposes only public curated data. If usage grows, add rate limiting and authentication without changing the underlying PetroTechRadar data pipeline.

## Example questions after connecting

- Find established Python repositories for SEG-Y data.
- Which open-source geothermal projects are available?
- Show Equinor repositories related to reservoir modelling.
- Where can I contribute to subsurface projects this week?
- Find papers with code related to FWI.
- Recommend open-source tools for geophysical inversion.

## Cost

The initial design is intended to fit comfortably inside Cloudflare Workers Free limits because the Worker performs lightweight filtering and retrieval while PetroTechRadar's scheduled GitHub workflows handle catalogue refreshes.
