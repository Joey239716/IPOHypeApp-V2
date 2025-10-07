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

    // Check if requesting a single company by CIK
    const cik = url.searchParams.get("cik");
    
    if (cik) {
      const raw = await env.PublicIPO_KV.get("ipo_table", "json");
      const data = Array.isArray(raw) ? raw : [];
      const company = data.find((row: any) => String(row.cik) === String(cik));
      
      if (!company) {
        return new Response(JSON.stringify({ error: "Company not found" }), {
          status: 404,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
          },
        });
      }
      
      return new Response(JSON.stringify(company), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    // Continue with normal list/pagination logic
    const all = url.searchParams.get("all") === "true";
    const page = parseInt(url.searchParams.get("page") || "1");
    const perPage = parseInt(url.searchParams.get("per_page") || "20");

    const exchange = url.searchParams.get("exchange");
    const minCap = Number(url.searchParams.get("min_market_cap") || "0");
    const rawSearch = url.searchParams.get("search");
    const search =
      rawSearch && rawSearch.trim().length > 0
        ? rawSearch.toLowerCase()
        : null;

    const raw = await env.PublicIPO_KV.get("ipo_table", "json");
    const data = Array.isArray(raw) ? raw : [];

    // Optional logging
    console.log("🔍 Filters:", { all, exchange, minCap, search });
    console.log("📦 Total in KV:", data.length);

    const filtered = all
      ? data // skip filtering if all=true
      : data.filter((row: any) =>
          (!exchange || row.exchange === exchange) &&
          (!minCap || Number(row.market_cap || 0) >= minCap) &&
          (!search ||
            row.company_name?.toLowerCase().includes(search) ||
            row.ticker?.toLowerCase().includes(search))
        );

    const total = filtered.length;
    const totalPages = Math.ceil(total / perPage);
    const start = (page - 1) * perPage;
    const paginated = filtered.slice(start, start + perPage);

    const responseData = all
      ? {
          source: "kv",
          rows: filtered, // send full dataset
        }
      : {
          source: "kv",
          page,
          per_page: perPage,
          total,
          total_pages: totalPages,
          rows: paginated,
        };

    return new Response(JSON.stringify(responseData), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  },
};