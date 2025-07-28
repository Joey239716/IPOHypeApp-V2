import requests
import datetime

class S1Fetcher:
    """
    Fetches S-1 filings from the SEC EDGAR daily index and returns preliminary IPO info.
    """
    def __init__(self, user_agent: str = "joeydaspam@gmail.com"):
        self.headers = {"User-Agent": user_agent}

    @staticmethod
    def get_quarter(month: int) -> int:
        """Return the fiscal quarter for a given month (1-12)."""
        return (month - 1) // 3 + 1

    @staticmethod
    def is_weekend(date: datetime.datetime) -> bool:
        """Check if the given datetime falls on a weekend."""
        return date.weekday() >= 5  # 5 = Saturday, 6 = Sunday

    def fetch(self, start_date: str, end_date: str) -> dict:
        """
        Fetch S-1 filings between start_date and end_date (inclusive).

        Args:
            start_date (str): "YYYY-MM-DD"
            end_date (str): "YYYY-MM-DD"

        Returns:
            dict: Mapping CIK -> {companyName, form_type, date_filed, link}
        """
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        
        prelim_ipo_info = {}
        missed_dates = []
        
        date = start
        while date <= end:
            year = date.year
            quarter = self.get_quarter(date.month)
            date_str = date.strftime("%Y%m%d")
            url = (
                f"https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/"
                f"master.{date_str}.idx"
            )
            try:
                resp = requests.get(url, headers=self.headers)
                if resp.status_code == 200:
                    for line in resp.text.splitlines():
                        if "|S-1|" in line or "|F-1|" in line:
                            parts = line.strip().split("|")
                            if len(parts) == 5:
                                cik, company, form_type, date_filed, file_name = parts
                                link = f"https://www.sec.gov/Archives/{file_name}"
                                prelim_ipo_info[cik] = {
                                    "companyName": company,
                                    "form_type": form_type,
                                    "date_filed": date_filed,
                                    "link": link
                                }
                else:
                    if not self.is_weekend(date):
                        missed_dates.append(date_str)
            except Exception:
                if not self.is_weekend(date):
                    missed_dates.append(date_str)
            date += datetime.timedelta(days=1)

        # Optionally handle missed_dates
        # e.g. log or retry
        print(prelim_ipo_info)
        return prelim_ipo_info

# Example usage:
# fetcher = S1Fetcher()\#
# ipo_data = fetcher.fetch("2025-07-02", "2025-07-11")
# print(ipo_data)
if __name__ == "__main__":
    fetcher = S1Fetcher()
    # Example usage
    ipo_data = fetcher.fetch("2025-07-02", "2025-07-11")
    print(ipo_data)
