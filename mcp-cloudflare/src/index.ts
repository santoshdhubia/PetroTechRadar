import { McpServer } from "@modelcontextprotocol/server";
import { createMcpHandler } from "agents/mcp/server";
import { z } from "zod";

const BASE = "https://santoshdhubia.github.io/PetroTechRadar/data";

type Repo = Record<string, unknown> & {
  repository?: string;
  url?: string;
  organization?: string;
  domain?: string;
  focus?: string;
  tier?: string;
  language?: string;
  license?: string;
  stars?: string | number;
  forks?: string | number;
  open_issues?: string | number;
  pushed_at?: string;
  petrotech_radar_score?: string | number;
};

type Paper = Record<string, unknown> & {
  paper_title?: string;
  topic?: string;
  journal?: string;
  year?: string | number;
  repository?: string;
  repo_url?: string;
  paper_url?: string;
  citations?: string | number;
  repo_stars?: string | number;
  papers_with_code_score?: string | number;
};

type IssueRepo = Record<string, unknown> & {
  repository?: string;
  organization?: string;
  domain?: string;
  repo_url?: string;
  issues_7d_url?: string;
  issues_180d_url?: string;
  open_7d?: number;
  open_180d?: number;
  no_response_7d?: number;
  unassigned_7d?: number;
  radar_score?: number;
};

async function getJson<T>(name: string): Promise<T> {
  const response = await fetch(`${BASE}/${name}`, {
    cf: { cacheTtl: 300, cacheEverything: true },
    headers: { "user-agent": "PetroTechRadar-MCP/0.1" },
  });
  if (!response.ok) throw new Error(`Could not load ${name}: ${response.status}`);
  return response.json<T>();
}

function num(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function textResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
  };
}

function repoSummary(r: Repo) {
  return {
    repository: r.repository,
    organization: r.organization,
    domain: r.domain,
    focus: r.focus,
    tier: r.tier,
    language: r.language,
    license: r.license,
    stars: num(r.stars),
    forks: num(r.forks),
    open_issues: num(r.open_issues),
    last_push: r.pushed_at,
    radar_score: num(r.petrotech_radar_score),
    url: r.url,
  };
}

function createServer() {
  const server = new McpServer({
    name: "PetroTechRadar",
    version: "0.1.0",
  });

  server.registerTool(
    "get_radar_stats",
    {
      description: "Return the current PetroTechRadar repository counts, tiers, domains and organizations.",
      inputSchema: {},
    },
    async () => textResult(await getJson("stats.json")),
  );

  server.registerTool(
    "search_repositories",
    {
      description: "Search curated subsurface repositories by capability, topic, repository, organization, domain, language or focus.",
      inputSchema: {
        query: z.string().min(1).describe("Natural-language keywords, e.g. SEG-Y, FWI, petrophysics, geothermal, OSDU"),
        tier: z.enum(["Core", "Emerging", "Research", "Reference"]).optional(),
        organization: z.string().optional(),
        limit: z.number().int().min(1).max(25).default(10),
      },
    },
    async ({ query, tier, organization, limit }) => {
      const payload = await getJson<{ repositories?: Repo[] }>("radar.json");
      const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
      const org = organization?.toLowerCase().trim();
      const scored = (payload.repositories ?? [])
        .filter((r) => !tier || r.tier === tier)
        .filter((r) => !org || String(r.organization ?? "").toLowerCase().includes(org))
        .map((r) => {
          const blob = [r.repository, r.organization, r.domain, r.focus, r.language, r.license, r.tier]
            .join(" ")
            .toLowerCase();
          const matches = tokens.reduce((sum, t) => sum + (blob.includes(t) ? 1 : 0), 0);
          const exactBoost = blob.includes(query.toLowerCase()) ? 3 : 0;
          return { r, score: matches + exactBoost + num(r.petrotech_radar_score) / 1000 };
        })
        .filter((x) => x.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .map((x) => repoSummary(x.r));
      return textResult({ query, count: scored.length, repositories: scored });
    },
  );

  server.registerTool(
    "get_repository",
    {
      description: "Return the full PetroTechRadar record for one repository.",
      inputSchema: { repository: z.string().min(1).describe("owner/repository, or a distinctive repository name") },
    },
    async ({ repository }) => {
      const payload = await getJson<{ repositories?: Repo[] }>("radar.json");
      const q = repository.toLowerCase();
      const exact = (payload.repositories ?? []).find((r) => String(r.repository ?? "").toLowerCase() === q);
      const partial = exact ?? (payload.repositories ?? []).find((r) => String(r.repository ?? "").toLowerCase().includes(q));
      return textResult(partial ?? { error: "Repository not found", repository });
    },
  );

  server.registerTool(
    "find_by_organization",
    {
      description: "List curated open-source repositories associated with a major organization or research community.",
      inputSchema: {
        organization: z.string().min(1),
        limit: z.number().int().min(1).max(30).default(15),
      },
    },
    async ({ organization, limit }) => {
      const payload = await getJson<{ repositories?: Repo[] }>("radar.json");
      const q = organization.toLowerCase();
      const repos = (payload.repositories ?? [])
        .filter((r) => String(r.organization ?? "").toLowerCase().includes(q) || String(r.repository ?? "").toLowerCase().startsWith(`${q}/`))
        .sort((a, b) => num(b.petrotech_radar_score) - num(a.petrotech_radar_score))
        .slice(0, limit)
        .map(repoSummary);
      return textResult({ organization, count: repos.length, repositories: repos });
    },
  );

  server.registerTool(
    "get_community_pulse",
    {
      description: "Show repositories with unresolved GitHub issues opened in the last 7 days, useful for current contribution opportunities.",
      inputSchema: { limit: z.number().int().min(1).max(25).default(10) },
    },
    async ({ limit }) => {
      const payload = await getJson<{ summary?: unknown; repositories?: IssueRepo[] }>("issues.json");
      const repos = (payload.repositories ?? [])
        .filter((r) => num(r.open_7d) > 0)
        .sort((a, b) => num(b.open_7d) - num(a.open_7d) || num(b.open_180d) - num(a.open_180d))
        .slice(0, limit);
      return textResult({ summary: payload.summary, repositories: repos });
    },
  );

  server.registerTool(
    "find_contribution_opportunities",
    {
      description: "Find tracked repositories with open GitHub issues created in the last six months and direct contribution links.",
      inputSchema: {
        query: z.string().optional().describe("Optional domain, repository or organization filter"),
        limit: z.number().int().min(1).max(30).default(15),
      },
    },
    async ({ query, limit }) => {
      const payload = await getJson<{ summary?: unknown; repositories?: IssueRepo[] }>("issues.json");
      const q = query?.toLowerCase().trim();
      const repos = (payload.repositories ?? [])
        .filter((r) => num(r.open_180d) > 0)
        .filter((r) => !q || `${r.repository} ${r.organization} ${r.domain}`.toLowerCase().includes(q))
        .sort((a, b) => num(b.open_7d) - num(a.open_7d) || num(b.open_180d) - num(a.open_180d))
        .slice(0, limit);
      return textResult({ query: query ?? null, count: repos.length, repositories: repos });
    },
  );

  server.registerTool(
    "search_papers",
    {
      description: "Search PetroTechRadar Papers with Code by paper title, topic, journal or repository.",
      inputSchema: {
        query: z.string().min(1),
        limit: z.number().int().min(1).max(25).default(10),
      },
    },
    async ({ query, limit }) => {
      const payload = await getJson<{ papers?: Paper[] }>("papers.json");
      const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
      const papers = (payload.papers ?? [])
        .map((p) => {
          const blob = `${p.paper_title} ${p.topic} ${p.journal} ${p.repository}`.toLowerCase();
          const score = tokens.reduce((s, t) => s + (blob.includes(t) ? 1 : 0), 0) + num(p.papers_with_code_score) / 1000;
          return { p, score };
        })
        .filter((x) => x.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .map(({ p }) => ({
          title: p.paper_title,
          topic: p.topic,
          journal: p.journal,
          year: p.year,
          citations: num(p.citations),
          repository: p.repository,
          github_stars: num(p.repo_stars),
          score: num(p.papers_with_code_score),
          paper_url: p.paper_url,
          repo_url: p.repo_url,
        }));
      return textResult({ query, count: papers.length, papers });
    },
  );

  server.registerTool(
    "recommend_repositories",
    {
      description: "Recommend repositories for a subsurface task using PetroTechRadar capability text, maturity tier, activity and radar score.",
      inputSchema: {
        task: z.string().min(3).describe("Describe what you need to do, e.g. read SEG-Y in Python, run reservoir simulation, perform geophysical inversion"),
        prefer_established: z.boolean().default(true),
        limit: z.number().int().min(1).max(15).default(5),
      },
    },
    async ({ task, prefer_established, limit }) => {
      const payload = await getJson<{ repositories?: Repo[] }>("radar.json");
      const tokens = task.toLowerCase().split(/[^a-z0-9+#.-]+/).filter((t) => t.length > 1);
      const ranked = (payload.repositories ?? [])
        .map((r) => {
          const blob = `${r.repository} ${r.organization} ${r.domain} ${r.focus} ${r.language}`.toLowerCase();
          const match = tokens.reduce((s, t) => s + (blob.includes(t) ? 1 : 0), 0);
          const maturity = prefer_established && r.tier === "Core" ? 1.5 : 0;
          const activity = r.pushed_at && Date.parse(String(r.pushed_at)) > Date.now() - 365 * 86400000 ? 0.5 : 0;
          return { r, score: match * 2 + maturity + activity + num(r.petrotech_radar_score) / 100 };
        })
        .filter((x) => x.score >= 2)
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .map((x) => ({ ...repoSummary(x.r), recommendation_score: Number(x.score.toFixed(2)) }));
      return textResult({ task, note: "Recommendations use the current curated metadata; function-level capability indexing will be added in a later version.", repositories: ranked });
    },
  );

  return server;
}

const mcpHandler = createMcpHandler(createServer, { route: "/mcp" });

export default {
  async fetch(request: Request, env: unknown, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "/health") {
      return Response.json({
        name: "PetroTechRadar MCP",
        version: "0.1.0",
        status: "ok",
        mcp_endpoint: "/mcp",
        data_source: "https://santoshdhubia.github.io/PetroTechRadar/",
      });
    }
    return mcpHandler(request, env, ctx);
  },
} satisfies ExportedHandler;
