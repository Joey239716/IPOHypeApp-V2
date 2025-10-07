// pages/api/upcoming.ts
export const runtime = "edge";

import type { NextApiRequest, NextApiResponse } from "next";
import { createServerClient } from "@supabase/ssr";

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
  const supabase = createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        const cookieHeader = req.headers.cookie ?? "";
        return cookieHeader
          .split("; ")
          .filter(Boolean)
          .map((str) => {
            const [name, ...rest] = str.split("=");
            return { name, value: rest.join("=") };
          });
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          const parts = [`${name}=${value}`];
          if (options.path) parts.push(`Path=${options.path}`);
          if (options.maxAge != null) parts.push(`Max-Age=${options.maxAge}`);
          if (options.expires) parts.push(`Expires=${options.expires.toUTCString()}`);
          if (options.httpOnly) parts.push("HttpOnly");
          if (options.secure) parts.push("Secure");
          if (options.sameSite) parts.push(`SameSite=${options.sameSite}`);
          const prev = res.getHeader("Set-Cookie");
          const prevArr = Array.isArray(prev) ? prev : prev ? [String(prev)] : [];
          res.setHeader("Set-Cookie", prevArr.concat(parts.join("; ")));
        });
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
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
