// components/IPOTableMobile.tsx

import React from "react";
import { StarIcon as StarIconOutline } from "@heroicons/react/24/outline";
import { StarIcon as StarIconSolid } from "@heroicons/react/24/solid";
import { useRouter } from "next/navigation";
import { IPO } from "@/lib/types";
import { exchangeBadgeClasses, formatCurrency, withPlaceholder } from "@/lib/ipo-utils";

interface Props {
  loading: boolean;
  sortedIpos: IPO[];
  starred: Set<string>;
  starLoading: string | null;
  onToggleStar: (cik: string) => void;
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

export const IPOTableMobile: React.FC<Props> = ({
  loading,
  sortedIpos,
  starred,
  starLoading,
  onToggleStar
}) => {
  const router = useRouter();

  const handleCardClick = (cik: string, e: React.MouseEvent) => {
    // Don't navigate if clicking on interactive elements
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
    <div className="sm:hidden space-y-4">
      {loading
        ? Array.from({ length: 5 }).map((_, idx) => (
            <div
              key={idx}
              className="p-5 rounded-2xl backdrop-blur-xl bg-white/70 dark:bg-gray-800/70 shadow-lg border border-white/20 dark:border-gray-700/30 animate-pulse"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-5 h-5 bg-gray-200 dark:bg-gray-700 rounded" />
                <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-lg" />
                <div className="flex-1 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                {["Price", "Shares", "Raise", "Est. IPO", "Exchange"].map(
                  (label, i) => (
                    <React.Fragment key={i}>
                      <div className="font-medium text-gray-600">{label}</div>
                      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded" />
                    </React.Fragment>
                  )
                )}
              </div>
            </div>
          ))
        : sortedIpos.map((ipo, index) => (
            <div
              key={ipo.cik}
              onClick={(e) => handleCardClick(ipo.cik, e)}
              className="relative p-5 rounded-2xl backdrop-blur-xl bg-white/70 dark:bg-gray-800/70 shadow-xl hover:shadow-2xl hover:bg-white/80 dark:hover:bg-gray-800/80 border border-white/20 dark:border-gray-700/30 hover:-translate-y-1 transition-all duration-300 cursor-pointer"
              style={{ 
                animation: `slideIn 0.4s ease-out ${index * 0.05}s both`
              }}
            >
              {/* Rank Badge - Top Left */}
              <div className="absolute top-3 left-3 flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/40 dark:to-blue-800/40 text-blue-700 dark:text-blue-300 font-bold text-xs shadow-sm">
                {ipo.rank}
              </div>
              
              {/* Main Content */}
              <div className="flex items-center gap-3 mb-4 mt-6">
                <button
                  onClick={() => onToggleStar(ipo.cik)}
                  disabled={starLoading === ipo.cik}
                  aria-label="Toggle Watchlist"
                  className="disabled:opacity-40 hover:scale-110 transition-transform duration-200"
                >
                  {starred.has(ipo.cik) ? (
                    <StarIconSolid className="w-6 h-6 text-yellow-400 drop-shadow-sm" />
                  ) : (
                    <StarIconOutline className="w-6 h-6 text-gray-400" />
                  )}
                </button>

                {ipo.logoUrl ? (
                  <img
                    src={ipo.logoUrl}
                    alt={ipo.companyName}
                    className="w-12 h-12 rounded-lg object-contain shadow-sm"
                  />
                ) : (
                  <div className="w-12 h-12 bg-gradient-to-br from-gray-200 to-gray-300 dark:from-gray-600 dark:to-gray-700 rounded-lg" />
                )}
                
                <div
                  className="flex flex-col truncate leading-tight flex-1"
                  title={ipo.companyName}
                >
                  <span className="text-base font-bold text-gray-900 dark:text-white truncate">
                    {ipo.companyName}
                  </span>
                  {ipo.ticker && ipo.ticker.trim() !== "" && (
                    <span className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {ipo.ticker}
                    </span>
                  )}
                </div>
              </div>

              {/* Data Grid */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                <div className="font-semibold text-gray-600 dark:text-gray-400">Price</div>
                <div className="text-right font-medium text-gray-900 dark:text-gray-100">
                  {withPlaceholder(ipo.sharePrice)}
                </div>

                <div className="font-semibold text-gray-600 dark:text-gray-400">Shares</div>
                <div className="text-right font-medium text-gray-900 dark:text-gray-100">
                  {withPlaceholder(ipo.sharesOffered)}
                </div>

                <div className="font-semibold text-gray-600 dark:text-gray-400">Raise</div>
                <div className="text-right font-semibold">
                  {ipo.raiseAmount && ipo.raiseAmount.trim() !== "" ? (
                    <span className="text-gray-900 dark:text-gray-100">
                      {formatCurrency(ipo.raiseAmount)}
                    </span>
                  ) : (
                    <span className="text-gray-400 italic font-normal">
                      Not available
                    </span>
                  )}
                </div>

                <div className="font-semibold text-gray-600 dark:text-gray-400">Est. IPO</div>
                <div className={`text-right ${getDateColorClass(ipo.estimatedIpoDate)}`}>
                  {withPlaceholder(ipo.estimatedIpoDate)}
                </div>

                <div className="font-semibold text-gray-600 dark:text-gray-400">Exchange</div>
                <div className="text-right">
                  <span
                    className={`inline-block px-3 py-1 rounded-lg text-xs font-semibold whitespace-nowrap backdrop-blur-sm ${exchangeBadgeClasses(
                      ipo.exchange
                    )}`}
                  >
                    {ipo.exchange || "Unknown"}
                  </span>
                </div>
              </div>

              {/* Gradient Border Effect on Hover */}
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-500/0 via-purple-500/0 to-pink-500/0 hover:from-blue-500/10 hover:via-purple-500/10 hover:to-pink-500/10 transition-all duration-300 pointer-events-none" />
            </div>
          ))}

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
};