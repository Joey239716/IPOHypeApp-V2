// types.ts

export interface IPO {
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
  rank: number;
}

export type SortColumn = "name" | "exchange" | "price" | "shares" | "raise" | "date";
export type SortDirection = "asc" | "desc" | null;