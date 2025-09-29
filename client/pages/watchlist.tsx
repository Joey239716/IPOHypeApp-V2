'use client'

import React, { useEffect, useState } from 'react'
import Navbar from '@/components/navbar'
import { useRouter } from 'next/navigation'
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)

interface IPO {
  cik: string
  companyName: string
  exchange: string
  sharesOffered: string
  sharePrice: string
  estimatedIpoDate: string
  latestFilingType: string
  raiseAmount: string
  logoUrl: string | null
}

export default function WatchlistPage() {
  const [ipos, setIpos] = useState<IPO[]>([])
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    ;(async () => {
      const { data: sessionData } = await supabase.auth.getSession()
      const currentUser = sessionData.session?.user || null
      setUser(currentUser)

      if (!currentUser) {
        router.push('/login')
        return
      }

      try {
        // Step 1: get list of CIKs
        const { data: watchlistRows, error: watchlistError } = await supabase
          .from('watchlist')
          .select('cik')
          .eq('user_id', currentUser.id)

        if (watchlistError) throw new Error(watchlistError.message)
        if (!watchlistRows || watchlistRows.length === 0) {
          setIpos([]) // empty
          setLoading(false)
          return
        }

        const cikList = watchlistRows.map((row) => row.cik)

        // Step 2: get matching IPOs
        const { data: ipoData, error: ipoError } = await supabase
          .from('ipo')
          .select(`
            cik,
            company_name,
            exchange,
            shares_offered,
            share_price,
            estimated_ipo_date,
            latest_filing_type,
            market_cap,
            logo_url
          `)
          .in('cik', cikList)

        if (ipoError) throw new Error(ipoError.message)

        const mapped: IPO[] = (ipoData || []).map((r: any) => ({
          cik: r.cik ?? '',
          companyName: r.company_name ?? '',
          exchange: r.exchange ?? '',
          sharesOffered:
            typeof r.shares_offered === 'number'
              ? r.shares_offered.toLocaleString()
              : typeof r.shares_offered === 'string'
              ? r.shares_offered
              : '',
          sharePrice: typeof r.share_price === 'string' ? r.share_price : r.share_price ?? '',
          estimatedIpoDate: r.estimated_ipo_date ?? '',
          latestFilingType: r.latest_filing_type ?? '',
          raiseAmount:
            typeof r.market_cap === 'number'
              ? r.market_cap.toString()
              : typeof r.market_cap === 'string'
              ? r.market_cap
              : '',
          logoUrl: r.logo_url ?? null
        }))

        setIpos(mapped)
      } catch (err: any) {
        console.error('[Watchlist Error]', err.message)
        setError(err.message || 'Failed to load watchlist')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 select-none caret-transparent">
      <Navbar />
      <main className="max-w-7xl mx-auto p-4">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">My Watchlist</h1>

        {loading ? (
          <p className="text-gray-600 dark:text-gray-300">Loading your watchlist...</p>
        ) : error ? (
          <p className="text-red-500">{error}</p>
        ) : ipos.length === 0 ? (
          <p className="text-gray-500 italic">You haven’t added any IPOs to your watchlist yet.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {ipos.map((ipo) => (
              <div
                key={ipo.cik}
                className="p-4 border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded shadow"
              >
                <div className="flex items-center gap-3 mb-2">
                  {ipo.logoUrl ? (
                    <img src={ipo.logoUrl} alt={ipo.companyName} className="w-8 h-8 object-contain rounded" />
                  ) : (
                    <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded" />
                  )}
                  <div className="text-sm font-semibold text-gray-900 dark:text-white truncate">{ipo.companyName}</div>
                </div>
                <div className="text-sm text-gray-700 dark:text-gray-200">
                  <p><strong>Exchange:</strong> {ipo.exchange || 'Unknown'}</p>
                  <p><strong>Price:</strong> {ipo.sharePrice || '-'}</p>
                  <p><strong>Shares:</strong> {ipo.sharesOffered || '-'}</p>
                  <p><strong>Raise:</strong> {ipo.raiseAmount ? `$${parseInt(ipo.raiseAmount).toLocaleString()}` : '-'}</p>
                  <p><strong>Est. IPO:</strong> {ipo.estimatedIpoDate || '-'}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
