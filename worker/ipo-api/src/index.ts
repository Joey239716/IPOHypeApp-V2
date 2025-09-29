// src/index.ts

export interface Env {
  PublicIPO_KV: KVNamespace;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get("page") || "1");
    const perPage = parseInt(url.searchParams.get("per_page") || "20");
    const exchange = url.searchParams.get("exchange");
    const minCap = Number(url.searchParams.get("min_market_cap") || "0");
    const search = url.searchParams.get("search")?.toLowerCase();

    const raw = await env.PublicIPO_KV.get("ipo_table", "json");
    const data = Array.isArray(raw) ? raw : [];

    const filtered = data.filter((row: any) =>
      (!exchange || row.exchange === exchange) &&
      (!minCap || Number(row.market_cap || 0) >= minCap) &&
      (!search || row.company_name?.toLowerCase().includes(search) || row.ticker?.toLowerCase().includes(search))
    );

    const total = filtered.length;
    const totalPages = Math.ceil(total / perPage);
    const start = (page - 1) * perPage;
    const paginated = filtered.slice(start, start + perPage);

    return new Response(JSON.stringify({
      source: "kv",
      page,
      per_page: perPage,
      total,
      total_pages: totalPages,
      rows: paginated,
    }), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      }
    });
  }
};

