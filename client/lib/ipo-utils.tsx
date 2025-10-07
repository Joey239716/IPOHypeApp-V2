// lib/ipo-utils.tsx

import React from "react";

export const exchangeBadgeClasses = (ex: string) => {
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
      return "bg-gray-200/50 text-gray-600 dark:bg-gray-600/50 dark:text-gray-300";
  }
};

export const formatCurrency = (value: string | number): string => {
  // Convert to string if it's a number
  const strValue = typeof value === "number" ? value.toString() : value;
  
  const num = parseFloat(strValue.replace(/[^0-9.]/g, ""));
  if (isNaN(num)) return strValue;
  const rounded = Math.round(num);
  
  // Check if it's a whole number (no cents)
  if (num === rounded) {
    return `$${rounded.toLocaleString("en-US")}`;
  }
  
  // Has decimal places, show up to 2 decimals but remove trailing zeros
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
};

export const formatPrice = (value: string | null | undefined): string | React.JSX.Element => {
  if (!value || value.trim() === "") {
    return <span className="text-gray-400 italic">Not available</span>;
  }
  
  // Handle ranges like "10.00$ - 15.00$"
  if (value.includes('-')) {
    const parts = value.split('-').map(part => {
      const num = parseFloat(part.replace(/[^0-9.]/g, ''));
      if (isNaN(num)) return part.trim();
      // Remove .00 if whole number
      return num % 1 === 0 ? num.toString() : num.toFixed(2);
    });
    return `$${parts[0]} - $${parts[1]}`;
  }
  
  // Single value
  const num = parseFloat(value.replace(/[^0-9.]/g, ''));
  if (isNaN(num)) return value;
  
  // Remove .00 if whole number
  return num % 1 === 0 ? `$${num.toLocaleString("en-US")}` : `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const withPlaceholder = (
  value: string | null | undefined
): string | React.JSX.Element => {
  if (value && typeof value === "string" && value.trim() !== "") {
    return value;
  }
  return (
    <span className="text-gray-400 italic">Not available</span>
  );
};