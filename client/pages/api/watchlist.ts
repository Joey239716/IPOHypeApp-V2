import type { NextApiRequest, NextApiResponse } from 'next'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY! // use service key for server-side
)

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const token = req.headers.authorization?.replace('Bearer ', '')

  if (!token) {
    return res.status(401).json({ error: 'Unauthorized' })
  }

  const {
    data: { user },
    error: userError
  } = await supabase.auth.getUser(token)

  if (userError || !user) {
    return res.status(401).json({ error: 'Invalid user token' })
  }

  try {
    const { data, error } = await supabase
      .from('watchlist')
      .select(`
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
      `)
      .eq('user_id', user.id)

    if (error) {
      throw new Error(error.message)
    }

    const result = data.map((row) => ({
      cik: row.cik,
      ...row.ipo
    }))

    res.status(200).json({ watchlist: result })
  } catch (e: any) {
    console.error('[API WATCHLIST ERROR]', e)
    res.status(500).json({ error: e.message })
  }
}
