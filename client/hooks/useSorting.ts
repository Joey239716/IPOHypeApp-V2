// hooks/useSorting.ts

import { useState, useEffect } from "react";
import { IPO, SortColumn, SortDirection } from "@/lib/types";

export const useSorting = (ipos: IPO[]) => {
  const [sortColumn, setSortColumn] = useState<SortColumn | null>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [sortedIpos, setSortedIpos] = useState<IPO[]>([]);

  // Helper function to parse values that might be ranges
  const parseNumericValue = (value: string | undefined | null): number => {
    if (!value) return 0;
    
    const cleaned = value.trim();
    
    // Check if it's a range (contains "-" between numbers)
    if (cleaned.includes('-')) {
      const parts = cleaned.split('-').map(p => {
        const num = parseFloat(p.replace(/[^0-9.]/g, ''));
        return isNaN(num) ? 0 : num;
      });
      // Take the higher (upper) value
      return Math.max(...parts);
    }
    
    // Single value
    const num = parseFloat(cleaned.replace(/[^0-9.]/g, ''));
    return isNaN(num) ? 0 : num;
  };

  const sortIPOs = (data: IPO[], column: SortColumn | null, direction: SortDirection) => {
    if (!column || !direction) {
      // Default sort: date ascending, then market cap descending
      return [...data].sort((a, b) => {
        const dateA = a.estimatedIpoDate || "";
        const dateB = b.estimatedIpoDate || "";
        
        // Nulls to bottom
        if (!dateA && dateB) return 1;
        if (dateA && !dateB) return -1;
        if (!dateA && !dateB) {
          // Both null, sort by market cap
          const capA = parseNumericValue(a.raiseAmount);
          const capB = parseNumericValue(b.raiseAmount);
          return capB - capA;
        }
        
        // Compare dates
        if (dateA !== dateB) return dateA.localeCompare(dateB);
        
        // Same date, sort by market cap descending
        const capA = parseNumericValue(a.raiseAmount);
        const capB = parseNumericValue(b.raiseAmount);
        return capB - capA;
      });
    }

    const sorted = [...data].sort((a, b) => {
      let valA: any;
      let valB: any;

      switch (column) {
        case "name":
          valA = a.companyName.toLowerCase();
          valB = b.companyName.toLowerCase();
          break;
        case "exchange":
          valA = a.exchange.toLowerCase();
          valB = b.exchange.toLowerCase();
          break;
        case "price":
          valA = parseNumericValue(a.sharePrice);
          valB = parseNumericValue(b.sharePrice);
          // Push zeros (empty values) to the end
          if (valA === 0 && valB !== 0) return 1;
          if (valA !== 0 && valB === 0) return -1;
          break;
        case "shares":
          valA = parseNumericValue(a.sharesOffered);
          valB = parseNumericValue(b.sharesOffered);
          // Push zeros (empty values) to the end
          if (valA === 0 && valB !== 0) return 1;
          if (valA !== 0 && valB === 0) return -1;
          break;
        case "raise":
          valA = parseNumericValue(a.raiseAmount);
          valB = parseNumericValue(b.raiseAmount);
          // Push zeros (empty values) to the end
          if (valA === 0 && valB !== 0) return 1;
          if (valA !== 0 && valB === 0) return -1;
          break;
        case "date":
          valA = a.estimatedIpoDate || "";
          valB = b.estimatedIpoDate || "";
          // Nulls to bottom
          if (!valA && valB) return 1;
          if (valA && !valB) return -1;
          break;
      }

      if (valA < valB) return direction === "asc" ? -1 : 1;
      if (valA > valB) return direction === "asc" ? 1 : -1;
      return 0;
    });

    return sorted;
  };

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      // Cycle through: asc -> desc -> default
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else if (sortDirection === "desc") {
        setSortColumn(null);
        setSortDirection(null);
      }
    } else {
      // New column, start with ascending
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  // Apply sorting whenever sort state or ipos change
  useEffect(() => {
    const sorted = sortIPOs(ipos, sortColumn, sortDirection);
    const ranked = sorted.map((ipo, index) => ({
      ...ipo,
      rank: index + 1
    }));
    setSortedIpos(ranked);
  }, [ipos, sortColumn, sortDirection]);

  return {
    sortedIpos,
    sortColumn,
    sortDirection,
    handleSort
  };
};