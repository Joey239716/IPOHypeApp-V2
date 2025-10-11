"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase-client";
import Navbar from "./navbar";
import { IPOTableDesktop } from "./IPOTableDesktop";
import { IPOTableMobile } from "./IPOTableMobile";
import { Pagination } from "./Pagination";
import { IPOStats } from "./IPOStats";
import { useSorting } from "@/hooks/useSorting";
import { usePagination } from "@/hooks/usePagination";
import { IPO } from "@/lib/types";
import type { User } from "@supabase/supabase-js"; // ✅ Supabase user type

// Define response shape for rows coming from Supabase / KV
interface IPOResponseRow {
  cik?: string | number;
  ticker?: string;
  company_name?: string;
  exchange?: string;
  shares_offered?: string | number;
  share_price?: string | number;
  estimated_ipo_date?: string;
  latest_filing_type?: string;
  market_cap?: string | number;
  logo_url?: string | null;
  isStarred?: boolean;
  source?: "supabase" | "kv";
}

export default function MainPage() {
  const [confirmMessage, setConfirmMessage] = useState<string | null>(null);
  const [ipos, setIpos] = useState<IPO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starred, setStarred] = useState<Set<string>>(new Set());
  const [user, setUser] = useState<User | null>(null); // ✅ typed user
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [starLoading, setStarLoading] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<"supabase" | "kv">("kv");
  const router = useRouter();

  const { sortedIpos, sortColumn, sortDirection, handleSort } = useSorting(ipos);

  // Reset pagination when sort changes
  const sortTrigger = `${sortColumn}-${sortDirection}`;
  const {
    paginatedItems,
    currentPage,
    totalPages,
    itemsPerPage,
    startIndex,
    endIndex,
    totalItems,
    goToPage,
    nextPage,
    prevPage,
    changeItemsPerPage,
  } = usePagination(sortedIpos, sortTrigger);

  // ⭐ Toggle watchlist
  const toggleStar = async (cik: string) => {
    if (!user) {
      setShowLoginModal(true);
      return;
    }

    if (starLoading === cik) return;
    setStarLoading(cik);

    const company = sortedIpos.find((i) => i.cik === cik)?.companyName || "IPO";
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
    } catch (err: unknown) {
      // ✅ safer error handling
      if (err instanceof Error) {
        console.error("Watchlist update failed:", err.message);
      } else {
        console.error("Watchlist update failed:", err);
      }
      setConfirmMessage("Something went wrong while updating your Watchlist.");
    } finally {
      setStarLoading(null);
      setTimeout(() => setConfirmMessage(null), 3000);
    }
  };

  // 📦 Fetch all IPOs and user info
  useEffect(() => {
    const fetchEverything = async () => {
      try {
        const { data } = await supabase.auth.getUser();
        const currentUser = data.user;
        setUser(currentUser);

        const isGuest = !currentUser;
        const baseUrl = isGuest
          ? "https://ipo-api.theipostreet.workers.dev/api/public?all=true"
          : "/api/upcoming?all=true";

        // Get session token for authenticated requests
        const headers: HeadersInit = {};
        if (currentUser) {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.access_token) {
            headers.Authorization = `Bearer ${session.access_token}`;
          }
        }

        const res = await fetch(baseUrl, {
          cache: "no-store",
          headers
        });
        const json = await res.json();

        if (!res.ok || !Array.isArray(json.rows)) {
          throw new Error(json.error || "Unexpected response");
        }

        setDataSource(json.source === "supabase" ? "supabase" : "kv");

        // ✅ type-safe starred mapping
        if (currentUser && Array.isArray(json.rows)) {
          const starredRows = (json.rows as IPOResponseRow[])
            .filter((row) => row.isStarred)
            .map((row) => String(row.cik));
          setStarred(new Set(starredRows));
        }

        // ✅ map to internal IPO type
        const mapped: IPO[] = (json.rows as IPOResponseRow[]).map((r) => ({
          cik: String(r.cik ?? ""),
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
              : typeof r.share_price === "number"
              ? r.share_price.toString()
              : "",
          estimatedIpoDate: r.estimated_ipo_date ?? "",
          latestFilingType: r.latest_filing_type ?? "",
          raiseAmount:
            typeof r.market_cap === "number"
              ? r.market_cap.toString()
              : typeof r.market_cap === "string"
              ? r.market_cap
              : "",
          logoUrl: r.logo_url ?? null,
          rank: 0,
        }));

        setIpos(mapped);
      } catch (e: unknown) {
        // ✅ safe handling for unknown error types
        if (e instanceof Error) {
          console.error("[MainPage ERROR]", e.message);
          setError(e.message);
        } else {
          console.error("[MainPage ERROR]", e);
          setError("Failed to load IPOs");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchEverything();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 select-none caret-transparent">
      <Navbar />
      <main className="max-w-7xl mx-auto p-4">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Upcoming IPOs
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            Discover the latest companies going public
          </p>
        </div>

        {error && (
          <div className="text-sm text-red-500 mb-4">Error: {error}</div>
        )}

        {/* 📊 Top Stats Section */}
        <IPOStats ipos={ipos} loading={loading} />

        {/* 🖥️ Desktop Table */}
        <IPOTableDesktop
          loading={loading}
          sortedIpos={paginatedItems}
          starred={starred}
          starLoading={starLoading}
          dataSource={dataSource}
          sortColumn={sortColumn}
          sortDirection={sortDirection}
          onToggleStar={toggleStar}
          onSort={handleSort}
        />

        {/* 📱 Mobile Table */}
        <IPOTableMobile
          loading={loading}
          sortedIpos={paginatedItems}
          starred={starred}
          starLoading={starLoading}
          onToggleStar={toggleStar}
        />

        {!loading && (
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            itemsPerPage={itemsPerPage}
            startIndex={startIndex}
            endIndex={endIndex}
            totalItems={totalItems}
            onPageChange={goToPage}
            onNextPage={nextPage}
            onPrevPage={prevPage}
            onItemsPerPageChange={changeItemsPerPage}
          />
        )}

        {/* 🔐 Login Modal */}
        {showLoginModal && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-0 animate-backdrop-fade"
            onClick={() => setShowLoginModal(false)}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="relative w-[90%] max-w-md rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-lg bg-white dark:bg-gray-900 text-gray-800 dark:text-white transform transition-all duration-300 ease-out translate-y-8 opacity-0 animate-modal-drop"
            >
              <button
                onClick={() => setShowLoginModal(false)}
                className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-white text-xl"
                aria-label="Close"
              >
                &times;
              </button>

              <h2 className="text-lg font-semibold mb-2">To add your first IPO</h2>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                Sign up to unlock Watchlist features and track IPOs you care about.
              </p>
              <p className="text-sm text-green-500 font-medium mb-4">It&apos;s free.</p>

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

        {/* 🌟 Confirmation Modal */}
        {confirmMessage && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-0 animate-backdrop-fade"
            onClick={() => setConfirmMessage(null)}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="relative w-[90%] max-w-sm rounded-lg border border-gray-100 dark:border-gray-700 p-5 shadow-xl bg-white dark:bg-gray-900 text-gray-800 dark:text-white transform transition-all duration-300 ease-out translate-y-8 opacity-0 animate-modal-drop"
            >
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
