"use client";

import React, { useEffect, useState } from "react";
import Navbar from "@/components/navbar";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase-client";
import {
  Sparkles,
  TrendingUp,
  Calendar,
  DollarSign,
  Building2,
  X,
} from "lucide-react";

interface IPO {
  cik: string;
  companyName: string;
  exchange: string;
  sharesOffered: string;
  sharePrice: string;
  estimatedIpoDate: string;
  latestFilingType: string;
  raiseAmount: string;
  logoUrl: string | null;
}

interface WatchlistRow {
  cik: string;
}

interface IpoRow {
  cik?: string | null;
  company_name?: string | null;
  exchange?: string | null;
  shares_offered?: string | number | null;
  share_price?: string | number | null;
  estimated_ipo_date?: string | null;
  latest_filing_type?: string | null;
  market_cap?: string | number | null;
  logo_url?: string | null;
}

const exchangeBadgeClasses = (ex: string): string => {
  switch (ex) {
    case "NASDAQ":
      return "bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-blue-600 dark:text-blue-400 border border-blue-400/30";
    case "NYSE":
      return "bg-gradient-to-r from-emerald-500/20 to-teal-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-400/30";
    case "CBOE":
      return "bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-400/30";
    case "OTC":
      return "bg-gradient-to-r from-pink-500/20 to-rose-500/20 text-pink-600 dark:text-pink-400 border border-pink-400/30";
    default:
      return "bg-gray-500/20 text-gray-600 dark:text-gray-400 border border-gray-400/30";
  }
};

export default function WatchlistPage() {
  const [ipos, setIpos] = useState<IPO[]>([]);
  const [user, setUser] = useState<{ id: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removingCik, setRemovingCik] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    (async () => {
      const { data } = await supabase.auth.getUser();
      const currentUser = data.user;
      setUser(currentUser ?? null);

      if (!currentUser) {
        router.push("/login");
        return;
      }

      try {
        const { data: watchlistRows, error: watchlistError } = await supabase
          .from("watchlist")
          .select("cik")
          .eq("user_id", currentUser.id)
          .returns<WatchlistRow[]>();

        if (watchlistError) throw new Error(watchlistError.message);
        if (!watchlistRows?.length) {
          setIpos([]);
          setLoading(false);
          return;
        }

        const cikList = watchlistRows.map((row) => row.cik);

        const { data: ipoData, error: ipoError } = await supabase
          .from("ipo")
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
          .in("cik", cikList)
          .returns<IpoRow[]>();

        if (ipoError) throw new Error(ipoError.message);

        const foundCiks = ipoData?.map((r) => r.cik ?? "") ?? [];
        const orphanedCiks = cikList.filter((cik) => !foundCiks.includes(cik));

        if (orphanedCiks.length > 0) {
          const { error: deleteError } = await supabase
            .from("watchlist")
            .delete()
            .eq("user_id", currentUser.id)
            .in("cik", orphanedCiks);

          if (deleteError) {
            console.error("[Watchlist Cleanup Error]", deleteError.message);
          } else {
            console.log(
              `Removed ${orphanedCiks.length} orphaned watchlist entries`
            );
          }
        }

        const mapped: IPO[] =
          ipoData?.map((r) => ({
            cik: r.cik ?? "",
            companyName: r.company_name ?? "",
            exchange: r.exchange ?? "",
            sharesOffered:
              typeof r.shares_offered === "number"
                ? r.shares_offered.toLocaleString()
                : r.shares_offered ?? "",
            sharePrice:
              typeof r.share_price === "number"
                ? r.share_price.toString()
                : r.share_price ?? "",
            estimatedIpoDate: r.estimated_ipo_date ?? "",
            latestFilingType: r.latest_filing_type ?? "",
            raiseAmount:
              typeof r.market_cap === "number"
                ? r.market_cap.toString()
                : r.market_cap ?? "",
            logoUrl: r.logo_url ?? null,
          })) ?? [];

        setIpos(mapped);
      } catch (err: unknown) {
        if (err instanceof Error) {
          console.error("[Watchlist Error]", err.message);
          setError(err.message);
        } else {
          console.error("[Watchlist Error]", err);
          setError("Failed to load watchlist");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const handleRemoveFromWatchlist = async (
    cik: string,
    e: React.MouseEvent
  ): Promise<void> => {
    e.stopPropagation();

    if (!user) return;
    setRemovingCik(cik);

    try {
      const { error: deleteError } = await supabase
        .from("watchlist")
        .delete()
        .eq("user_id", user.id)
        .eq("cik", cik);

      if (deleteError) throw new Error(deleteError.message);
      setIpos((prev) => prev.filter((ipo) => ipo.cik !== cik));
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error("[Remove from Watchlist Error]", err.message);
        setError(err.message);
      } else {
        console.error("[Remove from Watchlist Error]", err);
        setError("Failed to remove from watchlist");
      }
    } finally {
      setRemovingCik(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-gray-50 to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 select-none caret-transparent relative overflow-hidden">
      <Navbar />

      {/* Animated background blurs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-300/30 dark:bg-blue-500/10 rounded-full blur-3xl animate-pulse" />
        <div
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-300/30 dark:bg-gray-600/10 rounded-full blur-3xl animate-pulse"
          style={{ animationDelay: "1s" }}
        />
      </div>

      <main className="relative max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
        {/* Header Section */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-white/60 dark:bg-white/5 backdrop-blur-xl border border-white/60 dark:border-gray-700/50 shadow-xl">
              <Sparkles className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 dark:text-gray-100">
              My Watchlist
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400 ml-14">
            Track your favorite upcoming IPOs
          </p>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="relative group">
                <div className="absolute inset-0 bg-gradient-to-br from-white/30 to-blue-100/30 dark:from-gray-800/50 dark:to-gray-900/50 rounded-2xl blur-xl" />
                <div className="relative animate-pulse bg-white/30 dark:bg-white/5 backdrop-blur-xl border border-white/50 dark:border-gray-700/50 rounded-2xl p-6 h-72 shadow-xl">
                  <div className="flex items-start gap-4 mb-6">
                    <div className="w-14 h-14 bg-gray-300/50 dark:bg-gray-600/50 rounded-xl" />
                    <div className="flex-1 space-y-2">
                      <div className="h-5 bg-gray-300/50 dark:bg-gray-600/50 rounded w-3/4" />
                      <div className="h-6 bg-gray-300/50 dark:bg-gray-600/50 rounded w-20" />
                    </div>
                  </div>
                  <div className="space-y-3">
                    {[...Array(4)].map((_, j) => (
                      <div
                        key={j}
                        className="h-4 bg-gray-300/50 dark:bg-gray-600/50 rounded"
                      />
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-br from-red-200/60 to-pink-200/60 dark:from-red-900/30 dark:to-red-800/30 rounded-2xl blur-xl" />
            <div className="relative bg-red-50/70 dark:bg-red-900/20 backdrop-blur-xl border border-red-300/60 dark:border-red-800/50 rounded-2xl p-6 shadow-xl">
              <p className="text-red-600 dark:text-red-400">{error}</p>
            </div>
          </div>
        ) : ipos.length === 0 ? (
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-br from-white/30 to-blue-100/30 dark:from-gray-800/50 dark:to-gray-900/50 rounded-2xl blur-xl" />
            <div className="relative bg-white/30 dark:bg-white/5 backdrop-blur-xl border border-white/50 dark:border-gray-700/50 rounded-2xl p-12 text-center shadow-xl">
              <Sparkles className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 text-lg mb-4">
                You haven&apos;t added any IPOs to your watchlist yet.
              </p>
              <button
                onClick={() => router.push("/")}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                Explore IPOs
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {ipos.map((ipo) => (
              <div
                key={ipo.cik}
                onClick={() => router.push(`/company/${ipo.cik}`)}
                className="relative group cursor-pointer"
              >
                {/* Glow effect on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-blue-300/40 to-purple-300/40 dark:from-blue-500/20 dark:to-gray-600/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                {/* Glass card */}
                <div className="relative bg-white/30 dark:bg-white/5 backdrop-blur-xl border border-white/50 dark:border-gray-700/50 rounded-2xl p-6 shadow-xl hover:shadow-2xl hover:border-white/70 dark:hover:border-gray-600/60 transition-all duration-300 transform hover:-translate-y-1">
                  {/* Remove button */}
                  <button
                    onClick={(e) => handleRemoveFromWatchlist(ipo.cik, e)}
                    disabled={removingCik === ipo.cik}
                    className="absolute top-3 right-3 p-2 rounded-lg bg-white/40 dark:bg-white/10 backdrop-blur-sm border border-white/50 dark:border-gray-600/50 hover:bg-red-50/60 dark:hover:bg-red-900/30 hover:border-red-300/60 dark:hover:border-red-700/50 transition-all duration-200 group/remove shadow-md z-10"
                    aria-label="Remove from watchlist"
                  >
                    <X
                      className={`w-4 h-4 text-gray-600 dark:text-gray-400 group-hover/remove:text-red-600 dark:group-hover/remove:text-red-400 transition-colors ${
                        removingCik === ipo.cik ? "animate-spin" : ""
                      }`}
                    />
                  </button>

                  {/* Logo and Company Name */}
                  <div className="flex items-start gap-4 mb-6 pr-8">
                    <div className="relative">
                      {ipo.logoUrl ? (
                        <div className="w-14 h-14 rounded-xl overflow-hidden bg-white/40 dark:bg-white/10 backdrop-blur-sm border border-white/50 dark:border-gray-600/50 p-2 shadow-md">
                          <img
                            src={ipo.logoUrl}
                            alt={ipo.companyName}
                            className="w-full h-full object-contain"
                          />
                        </div>
                      ) : (
                        <div className="w-14 h-14 rounded-xl bg-white/40 dark:bg-white/10 backdrop-blur-sm border border-white/50 dark:border-gray-600/50 flex items-center justify-center shadow-md">
                          <Building2 className="w-6 h-6 text-gray-400 dark:text-gray-500" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 truncate mb-2">
                        {ipo.companyName}
                      </h3>
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${exchangeBadgeClasses(
                          ipo.exchange
                        )}`}
                      >
                        {ipo.exchange || "Unknown"}
                      </span>
                    </div>
                  </div>

                  {/* IPO Details */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between py-2 border-b border-gray-200/50 dark:border-gray-700/50">
                      <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 text-sm">
                        <DollarSign className="w-4 h-4" />
                        <span>Price</span>
                      </div>
                      <span className="text-gray-800 dark:text-gray-200 font-medium">
                        {ipo.sharePrice || (
                          <span className="text-gray-400 italic">N/A</span>
                        )}
                      </span>
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-200/50 dark:border-gray-700/50">
                      <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 text-sm">
                        <TrendingUp className="w-4 h-4" />
                        <span>Shares</span>
                      </div>
                      <span className="text-gray-800 dark:text-gray-200 font-medium">
                        {ipo.sharesOffered || (
                          <span className="text-gray-400 italic">N/A</span>
                        )}
                      </span>
                    </div>

                    <div className="flex items-center justify-between py-2 border-b border-gray-200/50 dark:border-gray-700/50">
                      <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 text-sm">
                        <DollarSign className="w-4 h-4" />
                        <span>Raise</span>
                      </div>
                      <span className="text-gray-800 dark:text-gray-200 font-medium">
                        {ipo.raiseAmount ? (
                          `$${parseInt(ipo.raiseAmount).toLocaleString()}`
                        ) : (
                          <span className="text-gray-400 italic">N/A</span>
                        )}
                      </span>
                    </div>

                    <div className="flex items-center justify-between py-2">
                      <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 text-sm">
                        <Calendar className="w-4 h-4" />
                        <span>Est. IPO</span>
                      </div>
                      <span className="text-gray-800 dark:text-gray-200 font-medium">
                        {ipo.estimatedIpoDate || (
                          <span className="text-gray-400 italic">N/A</span>
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
