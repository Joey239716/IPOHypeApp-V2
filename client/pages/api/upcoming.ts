// pages/api/upcoming.ts
export const runtime = "edge";

import type { NextApiRequest, NextApiResponse } from "next";
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const PUBLIC_KV_API = "https://ipo-api.theipostreet.workers.dev/api/public?all=true";

interface KvIpoRow {
  cik: string;
  company_name: string;
  exchange: string | null;
  shares_offered: string | number | null;
  share_price: string | number | null;
  estimated_ipo_date: string | null;
  latest_filing_type: string | null;
  market_cap: string | number | null;
  logo_url: string | null;
  [key: string]: unknown;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // ✅ Create Supabase client
  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  // ✅ Get token from Authorization header
  const token = req.headers.authorization?.replace("Bearer ", "");

  if (!token) {
    return res.status(401).json({ rows: [], error: "Unauthorized" });
  }

  // ✅ Validate user with access token
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser(token);

  if (userError || !user) {
    console.error("[AUTH ERROR]", userError?.message || "No user found");
    return res.status(401).json({ rows: [], error: "Unauthorized" });
  }

  // 1️⃣ Fetch from KV
  let kvRows: KvIpoRow[] = [];
  try {
    const kvRes = await fetch(PUBLIC_KV_API, { cache: "no-store" });
    const kvJson = await kvRes.json();
    kvRows = Array.isArray(kvJson.rows) ? (kvJson.rows as KvIpoRow[]) : [];
  } catch (err) {
    console.error("[KV ERROR]", err);
    return new Response(
      JSON.stringify({ rows: [], error: "Failed to fetch IPOs from KV" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // 2️⃣ Fetch watchlist CIKs from Supabase
  const { data: watchlist, error: watchlistError } = await supabase
    .from("watchlist")
    .select("cik")
    .eq("user_id", user.id);

  if (watchlistError) {
    console.error("[WATCHLIST ERROR]", watchlistError.message);
    return new Response(
      JSON.stringify({ rows: [], error: "Failed to fetch watchlist" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  const starredCiks = new Set(watchlist.map((row) => row.cik));

  // 3️⃣ Merge `isStarred`
  const enrichedRows = kvRows.map((row) => ({
    ...row,
    isStarred: starredCiks.has(row.cik),
  }));

  // 4️⃣ Respond
  return new Response(JSON.stringify({ rows: enrichedRows, source: "kv+supabase" }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "s-maxage=60, stale-while-revalidate",
    },
  });
}
