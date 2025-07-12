import requests
import datetime

def get_quarter(month):
    return (month - 1) // 3 + 1

def is_weekend(check_date):
    return check_date.weekday() >= 5  

def fetch_s1_filings(start_date: str, end_date: str):
    user_agent = "joeydaspam@gmail.com"
    headers = {"User-Agent": user_agent}

    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    missed_dates = []
    PrelimIpoInfo = {}

    date = start
    while date <= end:
        year = date.year
        quarter = get_quarter(date.month)
        date_str = date.strftime("%Y%m%d")
        url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/master.{date_str}.idx"


        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                lines = response.text.splitlines()
                for line in lines:
                    if "|S-1|" in line:
                        parts = line.strip().split("|")
                        if len(parts) == 5:
                            cik, company, form_type, date_filed, file_name = parts
                            link = f"https://www.sec.gov/Archives/{file_name}"
                            PrelimIpoInfo[cik] = {"companyName": company, "form_type": form_type, "date_filed": date_filed, "link": link}
            else:
                if not is_weekend(date):
                    missed_dates.append(date_str)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            if not is_weekend(date):
                missed_dates.append(date_str)

        date += datetime.timedelta(days=1)

    if missed_dates:
        print("\nMissed Dates (Weekdays only):")
        print(missed_dates)
    
    print(PrelimIpoInfo)

fetch_s1_filings("2025-07-2", "2025-07-11")