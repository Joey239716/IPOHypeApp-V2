"use client";

import React, { useEffect, useState } from "react";
import Navbar from "./navbar";
import { StarIcon as StarIconOutline } from "@heroicons/react/24/outline";
import { StarIcon as StarIconSolid } from "@heroicons/react/24/solid";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase-client";

interface IPO {
  cik: string;
  ticker: string;
  companyName: string;
  exchange: string;
  sharesOffered: string;
  sharePrice: string;
  estimatedIpoDate: string;
  latestFilingType: string;
  raiseAmount: string;
  logoUrl: string | null;
}

const exchangeBadgeClasses = (ex: string) => {
  switch (ex) {
    case "NASDAQ":
      return "bg-[#F0F1FA] text-[#4F5AED] dark:bg-[#2B2D52] dark:text-[#C3C7FF]";
    case "NYSE":
      return "bg-[#E1FCEF] text-[#14804A] dark:bg-[#1B3D30] dark:text-[#A8F0C9]";
    case "CBOE":
      return "bg-[#EAF4FF] text-[#0B64D6] dark:bg-[#1E3A5F] dark:text-[#BBD9FF]";
    case "OTC":
      return "bg-[#FDECF3] text-[#B0005B] dark:bg-[#3D1F2E] dark:text-[#FFC3DC]";
    default:
      return "bg-[#F0F1FA] text-[#5A6376] dark:bg-[#2B2D52] dark:text-[#5A6376]";
  }
};

const formatCurrency = (value: string): string => {
  const num = parseFloat(value.replace(/[^0-9.]/g, ""));
  if (isNaN(num)) return value;
  const rounded = Math.round(num);
  return `$${rounded.toLocaleString("en-US")}`;
};

const withPlaceholder = (
  value: string | null | undefined
): string | React.JSX.Element => {
  return value && value.trim() !== "" ? (
    value
  ) : (
    <span className="text-gray-400 italic">Not available</span>
  );
};

export default function MainPage() {
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
  const [ipos, setIpos] = useState<IPO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starred, setStarred] = useState<Set<string>>(new Set());
  const [user, setUser] = useState<any>(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [starLoading, setStarLoading] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<"supabase" | "kv">("kv");
  const router = useRouter();

  const toggleStar = async (cik: string) => {
    if (!user || dataSource === "kv") {
      setShowLoginModal(true);
      return;
    }

    if (starLoading === cik) return;
    setStarLoading(cik);

    const company = ipos.find((i) => i.cik === cik)?.companyName || "IPO";
    const alreadyStarred = starred.has(cik);

    try {
      if (alreadyStarred) {
        const { error } = await supabase
          .from("watchlist")
          .delete()
          .eq("user_id", user.id)
          .eq("cik", cik);

        if (error) throw error;

        setStarred((prev) => {
          const next = new Set(prev);
          next.delete(cik);
          return next;
        });
        setConfirmMessage(`${company} removed from your Watchlist`);
      } else {
        const { error } = await supabase
          .from("watchlist")
          .insert([{ user_id: user.id, cik }]);

        if (error) throw error;

        setStarred((prev) => new Set(prev).add(cik));
        setConfirmMessage(`${company} added to your Watchlist`);
      }
    } catch (err: any) {
      console.error("Watchlist update failed:", err.message || err);
      setConfirmMessage("Something went wrong while updating your Watchlist.");
    } finally {
      setStarLoading(null);
      setTimeout(() => setConfirmMessage(null), 3000);
    }
  };

  useEffect(() => {
    const fetchEverything = async () => {
      try {
        const { data } = await supabase.auth.getUser();

        setUser(data.user);

        const isGuest = !data.user;
        const baseUrl = isGuest
          ? "https://ipo-api.theipostreet.workers.dev/api/public"
          : "/api/upcoming";

        const res = await fetch(baseUrl, { cache: "no-store" });
        const json = await res.json();

        if (!res.ok || !Array.isArray(json.rows)) {
          throw new Error(json.error || "Unexpected response");
        }

        setDataSource(json.source === "supabase" ? "supabase" : "kv");

        if (data.user && json.source === "supabase") {
          const { data: watchlistData, error: watchlistError } = await supabase
            .from("watchlist")
            .select("cik")
            .eq("user_id", data.user.id);

          if (!watchlistError) {
            setStarred(new Set(watchlistData.map((row) => row.cik)));
          } else {
            console.error("Watchlist fetch error:", watchlistError.message);
          }
        }

        const mapped: IPO[] = json.rows.map((r: any) => ({
          cik: r.cik ?? "",
          ticker: r.ticker ?? "",
          companyName: r.company_name ?? "",
          exchange: r.exchange ?? "",
          sharesOffered:
            typeof r.shares_offered === "number"
              ? r.shares_offered.toLocaleString()
              : typeof r.shares_offered === "string"
              ? r.shares_offered
              : "",
          sharePrice:
            typeof r.share_price === "string"
              ? r.share_price
              : r.share_price ?? "",
          estimatedIpoDate: r.estimated_ipo_date ?? "",
          latestFilingType: r.latest_filing_type ?? "",
          raiseAmount:
            typeof r.market_cap === "number"
              ? r.market_cap.toString()
              : typeof r.market_cap === "string"
              ? r.market_cap
              : "",
          logoUrl: r.logo_url ?? null,
        }));

        setIpos(mapped);
      } catch (e: any) {
        console.error("[MainPage ERROR]", e.message || e);
        setError(e.message || "Failed to load IPOs");
      } finally {
        setLoading(false); // ✅ This guarantees table appears
      }
    };

    fetchEverything();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 select-none caret-transparent">
      <Navbar />
      <main className="max-w-7xl mx-auto p-4">
        <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
          Upcoming IPOs
        </h1>

        {error && (
          <div className="text-sm text-red-500 mb-4">Error: {error}</div>
        )}

        {/* ✅ Desktop Table */}
        <div className="hidden sm:block overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead className="border-b border-gray-300 dark:border-gray-700">
              <tr>
                <th className="px-2 py-3 w-[40px]"></th>
                <th className="px-3 py-3 w-[120px] text-sm font-semibold text-gray-500 dark:text-gray-400 text-left whitespace-nowrap">
                  Name
                </th>
                <th className="px-3 py-3 w-[100px] text-sm font-semibold text-gray-500 dark:text-gray-400 text-right whitespace-nowrap">
                  Exchange
                </th>
                <th className="px-3 py-3 w-[110px] text-sm font-semibold text-gray-500 dark:text-gray-400 text-right whitespace-nowrap">
                  Price
                </th>
                <th className="px-3 py-3 w-[120px] text-sm font-semibold text-gray-500 dark:text-gray-400 text-right whitespace-nowrap">
                  Shares
                </th>
                <th className="px-3 py-3 w-[110px] text-sm font-semibold text-gray-500 dark:text-gray-400 text-right whitespace-nowrap">
                  Raise
                </th>
                <th className="px-3 py-3 w-[110px] text-sm font-semibold text-gray-500 dark:text-gray-400 text-right whitespace-nowrap">
                  Est. IPO
                </th>
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 10 }).map((_, idx) => (
                    <tr
                      key={idx}
                      className="animate-pulse border-t border-gray-200 dark:border-gray-700"
                    >
                      <td className="px-2 py-4 text-center">
                        <div className="w-5 h-5 bg-gray-300 dark:bg-gray-700 rounded" />
                      </td>
                      <td className="px-3 py-4">
                        <div className="w-24 h-4 bg-gray-300 dark:bg-gray-700 rounded" />
                      </td>
                      <td className="px-3 py-4 text-right">
                        <div className="w-16 h-4 bg-gray-300 dark:bg-gray-700 rounded ml-auto" />
                      </td>
                      <td className="px-3 py-4 text-right">
                        <div className="w-12 h-4 bg-gray-300 dark:bg-gray-700 rounded ml-auto" />
                      </td>
                      <td className="px-3 py-4 text-right">
                        <div className="w-14 h-4 bg-gray-300 dark:bg-gray-700 rounded ml-auto" />
                      </td>
                      <td className="px-3 py-4 text-right">
                        <div className="w-16 h-4 bg-gray-300 dark:bg-gray-700 rounded ml-auto" />
                      </td>
                      <td className="px-3 py-4 text-right">
                        <div className="w-16 h-4 bg-gray-300 dark:bg-gray-700 rounded ml-auto" />
                      </td>
                    </tr>
                  ))
                : ipos.map((ipo) => (
                    <tr
                      key={ipo.cik}
                      className="border-t border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                      <td className="px-2 py-4 text-center align-middle">
                        <div className="flex items-center justify-center gap-4">
                          <div className="relative group">
                            <button
                              onClick={() => toggleStar(ipo.cik)}
                              disabled={starLoading === ipo.cik}
                              aria-label="Toggle Watchlist"
                              className="relative z-10 disabled:opacity-40"
                            >
                              {starred.has(ipo.cik) ? (
                                <StarIconSolid className="w-5 h-5 text-yellow-400 transition" />
                              ) : (
                                <StarIconOutline className="w-5 h-5 text-gray-400 hover:text-gray-500 transition" />
                              )}
                            </button>

                            {/* Tooltip bubble */}
                            <div className="absolute left-7 top-1/2 -translate-y-1/2 z-20 group-hover:opacity-100 group-hover:scale-100 opacity-0 scale-95 transition-all duration-150 pointer-events-none">
                              <div className="bg-[#111827] text-white text-xs font-medium px-2 py-0.5 rounded shadow-md whitespace-nowrap relative">
                                {dataSource === "kv"
                                  ? "Sign up to use Watchlist"
                                  : starred.has(ipo.cik)
                                  ? "Remove from Watchlist"
                                  : "Add to Watchlist"}

                                {/* Triangle tip */}
                                <div className="absolute left-[-6px] top-1/2 -translate-y-1/2 w-0 h-0 border-y-4 border-y-transparent border-r-6 border-r-[#111827]" />
                              </div>
                            </div>
                          </div>

                          {ipo.logoUrl ? (
                            <img
                              src={ipo.logoUrl}
                              alt={`${ipo.companyName} logo`}
                              className="w-8 h-8 object-contain rounded"
                            />
                          ) : (
                            <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded" />
                          )}
                        </div>
                      </td>
                      <td
                        className="px-3 py-4 w-[120px] text-sm text-left text-gray-800 dark:text-gray-200 align-middle truncate overflow-hidden whitespace-nowrap select-text"
                        title={ipo.companyName}
                      >
                        <div className="flex flex-col leading-tight">
                          <span className="font-medium">{ipo.companyName}</span>
                          {ipo.ticker && ipo.ticker.trim() !== "" && (
                            <span className="text-xs text-[#5A6376] dark:text-[#C3C7FF]">
                              Ticker: {ipo.ticker}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-3 py-4 text-sm text-right align-middle">
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${exchangeBadgeClasses(
                            ipo.exchange
                          )}`}
                        >
                          {ipo.exchange || "Unknown"}
                        </span>
                      </td>
                      <td className="px-3 py-4 text-sm text-right text-gray-800 dark:text-gray-200 align-middle whitespace-nowrap">
                        {withPlaceholder(ipo.sharePrice)}
                      </td>
                      <td className="px-3 py-4 text-sm text-right text-gray-800 dark:text-gray-200 align-middle">
                        {withPlaceholder(ipo.sharesOffered)}
                      </td>
                      <td className="px-3 py-4 text-sm text-right text-gray-800 dark:text-gray-200 align-middle">
                        {ipo.raiseAmount && ipo.raiseAmount.trim() !== "" ? (
                          formatCurrency(ipo.raiseAmount)
                        ) : (
                          <span className="text-gray-400 italic">
                            Not available
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-4 text-sm text-right text-gray-800 dark:text-gray-200 align-middle">
                        {withPlaceholder(ipo.estimatedIpoDate)}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {/* ✅ Mobile Cards and Modal */}
        {/* ✅ Mobile Cards with Skeletons */}
        <div className="sm:hidden space-y-4">
          {loading
            ? Array.from({ length: 5 }).map((_, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm animate-pulse"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-5 h-5 bg-gray-300 dark:bg-gray-600 rounded" />
                    <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded" />
                    <div className="flex-1 h-4 bg-gray-300 dark:bg-gray-600 rounded" />
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-sm text-gray-700 dark:text-gray-200">
                    {["Price", "Shares", "Raise", "Est. IPO", "Exchange"].map(
                      (label, i) => (
                        <React.Fragment key={i}>
                          <div className="font-medium">{label}</div>
                          <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded" />
                        </React.Fragment>
                      )
                    )}
                  </div>
                </div>
              ))
            : ipos.map((ipo) => (
                <div
                  key={ipo.cik}
                  className="p-4 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <button
                      onClick={() => toggleStar(ipo.cik)}
                      disabled={starLoading === ipo.cik}
                      aria-label="Toggle Watchlist"
                      className="disabled:opacity-40"
                    >
                      {starred.has(ipo.cik) ? (
                        <StarIconSolid className="w-5 h-5 text-yellow-400" />
                      ) : (
                        <StarIconOutline className="w-5 h-5 text-gray-400" />
                      )}
                    </button>

                    {ipo.logoUrl ? (
                      <img
                        src={ipo.logoUrl}
                        alt={ipo.companyName}
                        className="w-8 h-8 rounded object-contain"
                      />
                    ) : (
                      <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded" />
                    )}
                    <div
                      className="flex flex-col truncate leading-tight"
                      title={ipo.companyName}
                    >
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">
                        {ipo.companyName}
                      </span>
                      {ipo.ticker && ipo.ticker.trim() !== "" && (
                        <span className="text-xs text-[#5A6376] dark:text-[#C3C7FF]">
                          Ticker: {ipo.ticker}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm text-gray-700 dark:text-gray-200">
                    <div className="font-medium">Price</div>
                    <div className="text-right">
                      {withPlaceholder(ipo.sharePrice)}
                    </div>
                    <div className="font-medium">Shares</div>
                    <div className="text-right">
                      {withPlaceholder(ipo.sharesOffered)}
                    </div>
                    <div className="font-medium">Raise</div>
                    <div className="text-right">
                      {ipo.raiseAmount && ipo.raiseAmount.trim() !== "" ? (
                        formatCurrency(ipo.raiseAmount)
                      ) : (
                        <span className="text-gray-400 italic">
                          Not available
                        </span>
                      )}
                    </div>
                    <div className="font-medium">Est. IPO</div>
                    <div className="text-right">
                      {withPlaceholder(ipo.estimatedIpoDate)}
                    </div>
                    <div className="font-medium">Exchange</div>
                    <div className="text-right">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${exchangeBadgeClasses(
                          ipo.exchange
                        )}`}
                      >
                        {ipo.exchange || "Unknown"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
        </div>

        {/* ✅ Modal */}
        {showLoginModal && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center
               bg-black bg-opacity-0 animate-backdrop-fade"
            onClick={() => setShowLoginModal(false)}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="relative w-[90%] max-w-md rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-lg
                 bg-white dark:bg-gray-900 text-gray-800 dark:text-white
                 transform transition-all duration-300 ease-out translate-y-8 opacity-0 animate-modal-drop"
            >
              <button
                onClick={() => setShowLoginModal(false)}
                className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-white text-xl"
                aria-label="Close"
              >
                &times;
              </button>

              <h2 className="text-lg font-semibold mb-2">
                To add your first IPO
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                Sign up to unlock Watchlist features and track IPOs you care
                about.
              </p>
              <p className="text-sm text-green-500 font-medium mb-4">
                It’s free.
              </p>

              <div className="flex justify-end">
                <button
                  onClick={() => router.push("/login")}
                  className="px-4 py-2 bg-green-400 hover:bg-green-500 text-black font-semibold text-sm rounded-md transition"
                >
                  Sign Up / Login
                </button>
              </div>
            </div>
          </div>
        )}

        {confirmMessage && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-0 animate-backdrop-fade"
            onClick={() => setConfirmMessage(null)}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="relative w-[90%] max-w-sm rounded-lg border border-gray-100 dark:border-gray-700 p-5 shadow-xl
                 bg-white dark:bg-gray-900 text-gray-800 dark:text-white
                 transform transition-all duration-300 ease-out translate-y-8 opacity-0 animate-modal-drop"
            >
              {/* ⭐ Star icon */}
              <div className="flex items-center mb-3">
                <div className="w-8 h-8 flex items-center justify-center bg-yellow-100 text-yellow-600 rounded-full dark:bg-yellow-900 dark:text-yellow-300">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="w-5 h-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.182 3.637a1 1 0 00.95.69h3.826c.969 0 1.371 1.24.588 1.81l-3.093 2.25a1 1 0 00-.364 1.118l1.182 3.637c.3.921-.755 1.688-1.54 1.118l-3.093-2.25a1 1 0 00-1.176 0l-3.093 2.25c-.784.57-1.838-.197-1.539-1.118l1.182-3.637a1 1 0 00-.364-1.118l-3.093-2.25c-.783-.57-.38-1.81.588-1.81h3.826a1 1 0 00.95-.69l1.182-3.637z" />
                  </svg>
                </div>
                <div className="ml-3 text-sm font-medium max-w-sm leading-snug">
                  {confirmMessage}
                </div>
              </div>

              {/* 📌 View Watchlist button */}
              <div className="flex justify-end mt-6">
                <button
                  onClick={() => {
                    setConfirmMessage(null);
                    router.push("/watchlist");
                  }}
                  className="text-sm font-semibold px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700 transition"
                >
                  View Watchlist
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
