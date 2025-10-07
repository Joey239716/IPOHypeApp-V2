import React, { useMemo } from 'react';
import { TrendingUp, Calendar, DollarSign } from 'lucide-react';
import { IPO } from '@/lib/types';

interface IPOStatsProps {
  ipos: IPO[];
  loading: boolean;
}

export function IPOStats({ ipos, loading }: IPOStatsProps) {
  const stats = useMemo(() => {
    if (loading || ipos.length === 0) {
      return {
        totalIPOs: 0,
        filingsThisMonth: 0,
        largestIPO: null as { name: string; amount: string } | null,
      };
    }

    // Get current month and year
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    // Count filings from this month
    const filingsThisMonth = ipos.filter((ipo) => {
      if (!ipo.estimatedIpoDate) return false;
      const ipoDate = new Date(ipo.estimatedIpoDate);
      return (
        ipoDate.getMonth() === currentMonth &&
        ipoDate.getFullYear() === currentYear
      );
    }).length;

    // Find largest IPO by raise amount
    let largestIPO: { name: string; amount: string } | null = null;
    let maxRaise = 0;

    ipos.forEach((ipo) => {
      if (ipo.raiseAmount) {
        const raiseValue = parseInt(ipo.raiseAmount.replace(/,/g, ''));
        if (!isNaN(raiseValue) && raiseValue > maxRaise) {
          maxRaise = raiseValue;
          largestIPO = {
            name: ipo.companyName,
            amount: `$${raiseValue.toLocaleString()}`,
          };
        }
      }
    });

    return {
      totalIPOs: ipos.length,
      filingsThisMonth,
      largestIPO,
    };
  }, [ipos, loading]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm animate-pulse"
          >
            <div className="flex items-center justify-between">
              <div className="space-y-2 flex-1">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24" />
                <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-16" />
              </div>
              <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Total IPOs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              Total IPOs
            </p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats.totalIPOs}
            </p>
          </div>
          <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
            <TrendingUp className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </div>

      {/* Filings This Month */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              IPOs Scheduled This Month
            </p>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">
              {stats.filingsThisMonth}
            </p>
          </div>
          <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
            <Calendar className="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
        </div>
      </div>

      {/* Largest IPO */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
              Largest IPO
            </p>
            {stats.largestIPO ? (
              <>
                <p className="text-2xl font-bold text-gray-900 dark:text-white truncate">
                  {stats.largestIPO.amount}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-1">
                  {stats.largestIPO.name}
                </p>
              </>
            ) : (
              <p className="text-2xl font-bold text-gray-400 dark:text-gray-600">
                N/A
              </p>
            )}
          </div>
          <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
            <DollarSign className="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
        </div>
      </div>
    </div>
  );
}
