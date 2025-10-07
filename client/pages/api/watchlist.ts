import type { NextApiRequest, NextApiResponse } from "next";
import { createClient, type User } from "@supabase/supabase-js";

// ✅ Create Supabase client with service role key for server-side access
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// ✅ Type for a row in the joined query result
interface WatchlistRow {
  cik: string;
  ipo: {
    company_name?: string;
    exchange?: string;
    shares_offered?: number | string | null;
    share_price?: number | string | null;
    estimated_ipo_date?: string | null;
    latest_filing_type?: string | null;
    market_cap?: number | string | null;
    logo_url?: string | null;
  } | null;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const token = req.headers.authorization?.replace("Bearer ", "");

  if (!token) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  // ✅ Validate Supabase user
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser(token);

  if (userError || !user) {
    return res.status(401).json({ error: "Invalid user token" });
  }

  try {
    // ✅ Properly type Supabase response
    const { data, error } = await supabase
      .from("watchlist")
      .select(
        `
        cik,
        ipo:cik (
          company_name,
          exchange,
          shares_offered,
          share_price,
          estimated_ipo_date,
          latest_filing_type,
          market_cap,
          logo_url
        )
      `
      )
      .eq("user_id", (user as User).id)
      .returns<WatchlistRow[]>(); // ✅ Explicitly type returned rows

    if (error) {
      throw new Error(error.message);
    }

    const result =
      data?.map((row) => ({
        cik: row.cik,
        ...row.ipo,
      })) ?? [];

    res.status(200).json({ watchlist: result });
  } catch (e: unknown) {
    // ✅ Type-safe error handling (no `any`)
    if (e instanceof Error) {
      console.error("[API WATCHLIST ERROR]", e.message);
      return res.status(500).json({ error: e.message });
    }
    console.error("[API WATCHLIST ERROR]", e);
    return res.status(500).json({ error: "Unexpected server error" });
  }
}
