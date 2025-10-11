// pages/api/upcoming.ts
export const runtime = "edge";

import type { NextApiRequest, NextApiResponse } from "next";
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const PUBLIC_KV_API = "https://ipo-api.theipostreet.workers.dev/api/public?all=true";

// ✅ Define a lightweight type for IPO rows from KV
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
  [key: string]: unknown; // allow safe extension for future KV fields
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // ✅ Create Supabase client
  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  // ✅ Extract all cookies into a map
  const cookieHeader = req.headers.cookie ?? "";
  const cookies = cookieHeader.split("; ").reduce((acc, cookie) => {
    const [name, ...rest] = cookie.split("=");
    if (name) {
      acc[name] = rest.join("=");
    }
    return acc;
  }, {} as Record<string, string>);

  // Look for Supabase auth token - it's typically stored as sb-{project-ref}-auth-token
  const authTokenKey = Object.keys(cookies).find(key =>
    key.startsWith("sb-") && key.endsWith("-auth-token")
  );

  if (!authTokenKey) {
    return res.status(401).json({ rows: [], error: "Unauthorized" });
  }

  // Parse the auth token JSON (Supabase stores it as a JSON string)
  let accessToken: string;
  try {
    const tokenData = JSON.parse(decodeURIComponent(cookies[authTokenKey]));
    accessToken = tokenData.access_token || tokenData[0];
  } catch {
    // If parsing fails, try using the cookie value directly
    accessToken = cookies[authTokenKey];
  }

  if (!accessToken) {
    return res.status(401).json({ rows: [], error: "Unauthorized" });
  }

  // ✅ Validate user with access token
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser(accessToken);

  if (userError || !user) {
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
    return res
      .status(500)
      .json({ rows: [], error: "Failed to fetch IPOs from KV" });
  }

  // 2️⃣ Fetch watchlist CIKs from Supabase
  const { data: watchlist, error: watchlistError } = await supabase
    .from("watchlist")
    .select("cik")
    .eq("user_id", user.id);

  if (watchlistError) {
    console.error("[WATCHLIST ERROR]", watchlistError.message);
    return res
      .status(500)
      .json({ rows: [], error: "Failed to fetch watchlist" });
  }

  const starredCiks = new Set(watchlist.map((row) => row.cik));

  // 3️⃣ Merge `isStarred`
  const enrichedRows = kvRows.map((row) => ({
    ...row,
    isStarred: starredCiks.has(row.cik),
  }));

  // 4️⃣ Respond
  res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate");
  return res
    .status(200)
    .json({ rows: enrichedRows, source: "kv+supabase" });
}
