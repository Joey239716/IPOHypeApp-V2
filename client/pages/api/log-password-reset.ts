// pages/api/log-password-reset.ts

import type { NextApiRequest, NextApiResponse } from "next"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

// Utility to get IP from headers
function getClientIp(req: NextApiRequest): string {
  const xfwd = req.headers["x-forwarded-for"]
  if (typeof xfwd === "string") {
    return xfwd.split(",")[0].trim()
  }
  return req.socket?.remoteAddress ?? "unknown"
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method Not Allowed" })
  }

  const { email } = req.body
  const ipAddress = getClientIp(req)

  if (!email || typeof email !== "string") {
    return res.status(400).json({ error: "Missing or invalid email" })
  }

  const now = new Date()
  const oneMinuteAgo = new Date(now.getTime() - 60_000).toISOString()

  try {
    // 🔒 Rate limit by IP (1 per minute)
    const { data: recent, error: fetchError } = await supabase
      .from("reset_logs")
      .select("id")
      .eq("ip_address", ipAddress)
      .gt("requested_at", oneMinuteAgo)
      .limit(1)

    if (fetchError) {
      console.warn("Rate-limit fetch error:", fetchError.message)
    }

    if (recent && recent.length > 0) {
      return res
        .status(429)
        .json({ error: "Too many requests from your IP. Try again in 1 minute." })
    }

    // ✅ Insert new reset log
    const { error: insertError } = await supabase.from("reset_logs").insert([
      {
        email,
        requested_at: now.toISOString(),
        ip_address: ipAddress,
        source: "web",
      },
    ])

    if (insertError) {
      console.warn("Insert failed:", insertError.message)
    }

    console.log(`[Reset Link] ${email} from IP ${ipAddress} at ${now.toISOString()}`)

    return res.status(200).json({ ok: true })
  } catch (err) {
    console.error("Unexpected error in log-password-reset:", err)
    return res.status(500).json({ error: "Unexpected error" })
  }
}
