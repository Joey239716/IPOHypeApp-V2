// components/IPOTableDesktop.tsx

import React from "react";
import { StarIcon as StarIconOutline } from "@heroicons/react/24/outline";
import { StarIcon as StarIconSolid } from "@heroicons/react/24/solid";
import { useRouter } from "next/navigation";
import { IPO, SortColumn, SortDirection } from "@/lib/types";
import { exchangeBadgeClasses, formatCurrency, formatPrice, withPlaceholder } from "@/lib/ipo-utils";

interface Props {
  loading: boolean;
  sortedIpos: IPO[];
  starred: Set<string>;
  starLoading: string | null;
  dataSource: "supabase" | "kv";
  sortColumn: SortColumn | null;
  sortDirection: SortDirection;
  onToggleStar: (cik: string) => void;
  onSort: (column: SortColumn) => void;
}

const getDateColorClass = (date: string): string => {
  if (!date) return "";
  
  const ipoDate = new Date(date);
  const today = new Date();
  const diffDays = Math.ceil((ipoDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays <= 7) return "text-green-600 dark:text-green-400 font-semibold";
  if (diffDays <= 30) return "text-blue-600 dark:text-blue-400 font-medium";
  if (diffDays <= 90) return "text-gray-700 dark:text-gray-300";
  return "text-gray-500 dark:text-gray-400";
};

export const IPOTableDesktop: React.FC<Props> = ({
  loading,
  sortedIpos,
  starred,
  starLoading,
  dataSource,
  sortColumn,
  sortDirection,
  onToggleStar,
  onSort
}) => {
  const router = useRouter();

  const handleRowClick = (cik: string, e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (
      target.closest('button') || 
      target.closest('a') ||
      target.closest('[role="button"]')
    ) {
      return;
    }
    router.push(`/company/${cik}`);
  };

  return (
    <div className="hidden sm:block rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead className="border-b-2 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-3 py-4 w-[80px]"></th>
              <th className="px-2 py-4 w-[50px] text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-200 text-center whitespace-nowrap">
                Rank
              </th>
              <th 
                className="px-4 py-4 w-[180px] text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-200 text-left whitespace-nowrap cursor-pointer hover:text-gray-900 dark:hover:text-white transition-colors group"
                onClick={() => onSort("name")}
              >
                <div className="flex items-center gap-2">
                  <span>Company</span>
                  {sortColumn === "name" && (
                    <span className="text-blue-600 dark:text-blue-400 text-sm">
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                  {sortColumn !== "name" && (
                    <span className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity text-sm">↕</span>
                  )}
                </div>
              </th>
              <th className="px-4 py-4 w-[110px] text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-200 text-right whitespace-nowrap">
                <div className="flex items-center justify-end gap-2">
                  <span>Exchange</span>
                </div>
              </th>
              <th 
                className="px-4 py-4 w-[110px] text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-200 text-right whitespace-nowrap cursor-pointer hover:text-gray-900 dark:hover:text-white transition-colors group"
                onClick={() => onSort("price")}
              >
                <div className="flex items-center justify-end gap-2">
                  <span>Price</span>
                  {sortColumn === "price" && (
                    <span className="text-blue-600 dark:text-blue-400 text-sm">
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                  {sortColumn !== "price" && (
                    <span className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity text-sm">↕</span>
                  )}
                </div>
              </th>
              <th 
                className="px-4 py-4 w-[120px] text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-200 text-right whitespace-nowrap cursor-pointer hover:text-gray-900 dark:hover:text-white transition-colors group"
                onClick={() => onSort("shares")}
              >
                <div className="flex items-center justify-end gap-2">
                  <span>Shares</span>
                  {sortColumn === "shares" && (
                    <span className="text-blue-600 dark:text-blue-400 text-sm">
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                  {sortColumn !== "shares" && (
                    <span className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity text-sm">↕</span>
                  )}
                </div>
              </th>
              <th 
                className="px-4 py-4 w-[130px] text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-200 text-right whitespace-nowrap cursor-pointer hover:text-gray-900 dark:hover:text-white transition-colors group"
                onClick={() => onSort("raise")}
              >
                <div className="flex items-center justify-end gap-2">
                  <span>Raise</span>
                  {sortColumn === "raise" && (
                    <span className="text-blue-600 dark:text-blue-400 text-sm">
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                  {sortColumn !== "raise" && (
                    <span className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity text-sm">↕</span>
                  )}
                </div>
              </th>
              <th 
                className="px-4 py-4 w-[120px] text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-200 text-right whitespace-nowrap cursor-pointer hover:text-gray-900 dark:hover:text-white transition-colors group"
                onClick={() => onSort("date")}
              >
                <div className="flex items-center justify-end gap-2">
                  <span>Est. IPO</span>
                  {sortColumn === "date" && (
                    <span className="text-blue-600 dark:text-blue-400 text-sm">
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                  {sortColumn !== "date" && (
                    <span className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity text-sm">↕</span>
                  )}
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {loading
              ? Array.from({ length: 10 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="px-3 py-5 text-center">
                      <div className="flex items-center justify-center gap-3">
                        <div className="w-5 h-5 bg-gray-200 dark:bg-gray-700 rounded" />
                        <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full" />
                      </div>
                    </td>
                    <td className="px-2 py-5 text-center">
                      <div className="w-8 h-4 bg-gray-200 dark:bg-gray-700 rounded mx-auto" />
                    </td>
                    <td className="px-4 py-5">
                      <div className="w-32 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
                    </td>
                    <td className="px-4 py-5 text-right">
                      <div className="w-20 h-6 bg-gray-200 dark:bg-gray-700 rounded ml-auto" />
                    </td>
                    <td className="px-4 py-5 text-right">
                      <div className="w-16 h-4 bg-gray-200 dark:bg-gray-700 rounded ml-auto" />
                    </td>
                    <td className="px-4 py-5 text-right">
                      <div className="w-20 h-4 bg-gray-200 dark:bg-gray-700 rounded ml-auto" />
                    </td>
                    <td className="px-4 py-5 text-right">
                      <div className="w-24 h-4 bg-gray-200 dark:bg-gray-700 rounded ml-auto" />
                    </td>
                    <td className="px-4 py-5 text-right">
                      <div className="w-20 h-4 bg-gray-200 dark:bg-gray-700 rounded ml-auto" />
                    </td>
                  </tr>
                ))
              : sortedIpos.map((ipo) => (
                  <tr
                    key={ipo.cik}
                    onClick={(e) => handleRowClick(ipo.cik, e)}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150 cursor-pointer"
                  >
                    <td className="px-3 py-5 text-center align-middle">
                      <div className="flex items-center justify-center gap-3">
                        <div className="relative group/star">
                          <button
                            onClick={() => onToggleStar(ipo.cik)}
                            disabled={starLoading === ipo.cik}
                            aria-label="Toggle Watchlist"
                            className="relative z-10 disabled:opacity-40 transition-transform duration-200"
                          >
                            {starred.has(ipo.cik) ? (
                              <StarIconSolid className="w-5 h-5 text-yellow-400 drop-shadow-sm" />
                            ) : (
                              <StarIconOutline className="w-5 h-5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" />
                            )}
                          </button>
                          <div className="absolute left-7 top-1/2 -translate-y-1/2 z-20 opacity-0 group-hover/star:opacity-100 scale-95 group-hover/star:scale-100 transition-all duration-150 pointer-events-none">
                            <div className="bg-gray-900 dark:bg-gray-700 text-white text-xs font-medium px-2.5 py-1 rounded-md shadow-lg whitespace-nowrap relative">
                              {dataSource === "kv"
                                ? "Sign up to use Watchlist"
                                : starred.has(ipo.cik)
                                ? "Remove from Watchlist"
                                : "Add to Watchlist"}
                              <div className="absolute left-[-4px] top-1/2 -translate-y-1/2 w-0 h-0 border-y-4 border-y-transparent border-r-4 border-r-gray-900 dark:border-r-gray-700" />
                            </div>
                          </div>
                        </div>
                        {ipo.logoUrl ? (
                          <img
                            src={ipo.logoUrl}
                            alt={`${ipo.companyName} logo`}
                            className="w-10 h-10 object-cover rounded-full"
                          />
                        ) : (
                          <div className="w-10 h-10 bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-600 dark:to-gray-700 rounded-full" />
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-5 text-sm text-center text-gray-800 dark:text-gray-100 align-middle font-medium">
                      {ipo.rank}
                    </td>
                    <td className="px-4 py-5 text-sm text-left align-middle" title={ipo.companyName}>
                      <div className="flex flex-col leading-tight">
                        <span className="font-semibold text-gray-900 dark:text-white">
                          {ipo.companyName}
                        </span>
                        {ipo.ticker && ipo.ticker.trim() !== "" && (
                          <span className="text-xs text-gray-600 dark:text-gray-300 mt-0.5">
                            {ipo.ticker}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-5 text-sm text-right align-middle">
                      <span className={`inline-block px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap ${exchangeBadgeClasses(ipo.exchange)}`}>
                        {ipo.exchange || "Unknown"}
                      </span>
                    </td>
                    <td className="px-4 py-5 text-sm text-right text-gray-800 dark:text-gray-100 align-middle whitespace-nowrap font-medium">
                      {formatPrice(ipo.sharePrice)}
                    </td>
                    <td className="px-4 py-5 text-sm text-right text-gray-800 dark:text-gray-100 align-middle font-medium">
                      {withPlaceholder(ipo.sharesOffered)}
                    </td>
                    <td className="px-4 py-5 text-sm text-right align-middle font-semibold">
                      {ipo.raiseAmount && ipo.raiseAmount.trim() !== "" ? (
                        <span className="text-gray-900 dark:text-white">
                          {formatCurrency(ipo.raiseAmount)}
                        </span>
                      ) : (
                        <span className="text-gray-400 dark:text-gray-500 italic font-normal">
                          Not available
                        </span>
                      )}
                    </td>
                    <td className={`px-4 py-5 text-sm text-right align-middle ${getDateColorClass(ipo.estimatedIpoDate)}`}>
                      {withPlaceholder(ipo.estimatedIpoDate)}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};