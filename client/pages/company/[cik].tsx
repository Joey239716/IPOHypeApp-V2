import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import Navbar from "@/components/navbar";
import { supabase } from "@/lib/supabase-client";
import { exchangeBadgeClasses, formatCurrency } from "@/lib/ipo-utils";

interface CompanyData {
  cik: string;
  ticker: string;
  company_name: string;
  exchange: string;
  shares_offered: string;
  share_price: string;
  estimated_ipo_date: string;
  latest_filing_type: string;
  latest_filing_date: string;
  latest_filing_url: string;
  mainlink: string;
  market_cap: string;
  logo_url: string | null;
}

export default function CompanyPage() {
  const router = useRouter();
  const { cik } = router.query;
  
  const [company, setCompany] = useState<CompanyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCompanyData = async () => {
      if (!cik || typeof cik !== "string") return;

      try {
        // Always use the worker endpoint since it supports ?cik parameter
        const baseUrl = `https://ipo-api.theipostreet.workers.dev/api/public?cik=${cik}`;

        const res = await fetch(baseUrl, { cache: "no-store" });
        const json = await res.json();

        if (!res.ok) {
          throw new Error(json.error || "Failed to load company data");
        }

        setCompany(json);
      } catch (e: any) {
        console.error("[Company Page ERROR]", e.message || e);
        setError(e.message || "Failed to load company");
      } finally {
        setLoading(false);
      }
    };

    fetchCompanyData();
  }, [cik]);

  if (loading || !cik) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navbar />
        <main className="max-w-5xl mx-auto p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </main>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Navbar />
        <main className="max-w-5xl mx-auto p-6">
          <button
            onClick={() => router.back()}
            className="mb-4 text-blue-600 dark:text-blue-400 hover:underline"
          >
            ← Back to IPOs
          </button>
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-800 dark:text-red-200 mb-2">
              Company Not Found
            </h2>
            <p className="text-red-600 dark:text-red-300">
              {error || "The requested company could not be found."}
            </p>
          </div>
        </main>
      </div>
    );
  }

  const formatSharesOffered = (shares: string | number): string => {
    if (!shares) return "Not available";
    const strShares = typeof shares === "string" ? shares : shares.toString();
    if (strShares.trim() === "") return "Not available";
    const num = parseFloat(strShares.replace(/[^0-9.]/g, ""));
    if (isNaN(num)) return strShares;
    return num.toLocaleString("en-US");
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 relative overflow-hidden">
      {/* Floating background objects for glassmorphism effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-blue-400/10 dark:bg-blue-500/5 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute top-40 right-20 w-96 h-96 bg-purple-400/10 dark:bg-purple-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }}></div>
        <div className="absolute bottom-20 left-1/3 w-80 h-80 bg-pink-400/10 dark:bg-pink-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }}></div>
        <div className="absolute top-1/2 right-1/4 w-64 h-64 bg-cyan-400/10 dark:bg-cyan-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1.5s' }}></div>
      </div>

      <Navbar />
      <main className="max-w-6xl mx-auto px-6 py-3 relative z-10">
        <button
          onClick={() => router.back()}
          className="mb-3 text-blue-600 dark:text-blue-400 hover:underline font-medium text-sm"
        >
          ← Back to IPOs
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Company Header */}
          <div className="lg:col-span-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-blue-50/80 to-purple-50/70 dark:from-gray-800/90 dark:via-gray-800/85 dark:to-gray-800/80 rounded-xl shadow-xl border border-white/20 dark:border-gray-700/50 p-4">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              {company.company_name}
            </h1>

            <div className="flex items-center gap-3 flex-wrap">
              {company.ticker && (
                <span className="text-base font-semibold text-gray-600 dark:text-gray-300">
                  {company.ticker}
                </span>
              )}
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">Exchange:</span>
                <span
                  className={`inline-block px-2 py-1 rounded-full text-xs font-semibold backdrop-blur-sm ${exchangeBadgeClasses(
                    company.exchange
                  )}`}
                >
                  {company.exchange || "Unknown"}
                </span>
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                CIK: {company.cik}
              </span>
            </div>
          </div>

          {/* IPO Details - 6 cards in 3 columns */}
          <div className="border-l-4 border-blue-500 pl-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-blue-50/80 to-transparent dark:from-gray-800/90 dark:via-blue-950/30 dark:to-transparent rounded-r-xl shadow-xl border-t border-r border-b border-white/20 dark:border-gray-700/50 p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Share Price
            </div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {company.share_price || "Not available"}
            </div>
          </div>

          <div className="border-l-4 border-green-500 pl-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-green-50/80 to-transparent dark:from-gray-800/90 dark:via-green-950/30 dark:to-transparent rounded-r-xl shadow-xl border-t border-r border-b border-white/20 dark:border-gray-700/50 p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Shares Offered
            </div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {formatSharesOffered(company.shares_offered)}
            </div>
          </div>

          <div className="border-l-4 border-purple-500 pl-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-purple-50/80 to-transparent dark:from-gray-800/90 dark:via-purple-950/30 dark:to-transparent rounded-r-xl shadow-xl border-t border-r border-b border-white/20 dark:border-gray-700/50 p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Expected Raise
            </div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {company.market_cap ? formatCurrency(company.market_cap) : "Not available"}
            </div>
          </div>

          <div className="border-l-4 border-orange-500 pl-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-orange-50/80 to-transparent dark:from-gray-800/90 dark:via-orange-950/30 dark:to-transparent rounded-r-xl shadow-xl border-t border-r border-b border-white/20 dark:border-gray-700/50 p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Estimated IPO Date
            </div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {company.estimated_ipo_date || "Not available"}
            </div>
          </div>

          <div className="border-l-4 border-red-500 pl-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-red-50/80 to-transparent dark:from-gray-800/90 dark:via-red-950/30 dark:to-transparent rounded-r-xl shadow-xl border-t border-r border-b border-white/20 dark:border-gray-700/50 p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Latest Filing
            </div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {company.latest_filing_type || "Not available"}
            </div>
          </div>

          <div className="border-l-4 border-pink-500 pl-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-pink-50/80 to-transparent dark:from-gray-800/90 dark:via-pink-950/30 dark:to-transparent rounded-r-xl shadow-xl border-t border-r border-b border-white/20 dark:border-gray-700/50 p-3">
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Latest Filing Date
            </div>
            <div className="text-xl font-bold text-gray-900 dark:text-white">
              {company.latest_filing_date || "Not available"}
            </div>
          </div>

          {/* SEC Filing Link */}
          {(company.latest_filing_url || company.mainlink) && (
            <div className="lg:col-span-3 backdrop-blur-xl bg-gradient-to-br from-white/90 via-cyan-50/80 to-blue-50/70 dark:from-gray-800/90 dark:via-gray-800/85 dark:to-gray-800/80 rounded-xl shadow-xl border border-white/20 dark:border-gray-700/50 p-4">
              <a
                href={company.latest_filing_url || company.mainlink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors shadow-lg hover:shadow-xl text-sm"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-4 w-4"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                </svg>
                View Latest SEC Filing
              </a>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}