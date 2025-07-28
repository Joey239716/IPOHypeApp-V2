# === File 2: analyze_with_gpt.py ===
# Purpose: Parse SEC docs from DB and extract IPO metadata using GPT-4o-mini

import os
import time
import re
import json
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from supabase import create_client, Client
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
headers = {"User-Agent": "joeydaspam@gmail.com"}

def null_if_unknown(val):
    return None if isinstance(val, str) and val.lower() == "unknown" else val

def null_if_unknown_numeric(val):
    if isinstance(val, str):
        if val.lower() == "unknown": return None
        val = val.replace(",", "").replace("$", "").strip()
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None

def analyze():
    rows = supabase.table('ipo').select('cik', 'mainlink', 'company_name').execute().data or []
    for row in rows:
        time.sleep(2)
        cik, url = row['cik'], row['mainlink']
        companyName = row['company_name']
        try:
            r = requests.get(url, headers=headers); r.raise_for_status()
            try: soup = BeautifulSoup(r.text, 'lxml')
            except: soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup(['script', 'style', 'head', 'title', 'meta', '[document]']): tag.decompose()
            text = re.sub(r'\s+', ' ', soup.get_text()).strip()
            snippet = ' '.join(text.split()[:1000])

            prompt = (
                f"Given this provided text: {snippet}\n\n"
                "Classify the document and extract IPO metadata.\n\n"
                "1. Determine if the filing represents an **initial public offering (IPO)**.\n"
                "    - If the company is registering new securities to raise capital for itself and going public for the first time, it's an IPO.\n"
                "    - If it's a resale of shares by existing shareholders, a shelf registration (Rule 415), a SPAC merger, or a follow-on offering, it's NOT an IPO.\n\n"
                "2. If it IS an IPO, extract the following details:\n"
                "    - 'Shares Offered': Number of shares being offered by the company, If the number is a placeholder like [●], [__], or missing, return 'unknown'\n"
                "    - 'share_price': Price or range (format as '10$ - 12$', or '10$'), if you can't find the actual price, return 'unknown'\n"
                "    - 'estimated_ipo_date': If IPO date or estimated date/week is mentioned, extract it; otherwise return 'unknown'\n"
                "    - 'ticker': The proposed trading symbol, if known\n"
                "    - 'exchange': The exchange name (e.g., NASDAQ, NYSE), if available\n"
                "    - 'market_cap': Multiply total shares outstanding by price (use midpoint if price is a range), or return 'unknown'\n"
                f"    - 'logo_url': If there is a homepage link to the company's website, include it. Use this company name: {companyName} to try and find the homepage link. Otherwise return 'unknown'\n\n"
                "3. Respond with a valid JSON object using the following structure:\n"
                "{\n"
                "  \"IPO\": \"yes\" or \"no\",\n"
                "  \"Shares Offered\": \"...\",\n"
                "  \"share_price\": \"...\",\n"
                "  \"estimated_ipo_date\": \"...\",\n"
                "  \"ticker\": \"...\",\n"
                "  \"exchange\": \"...\",\n"
                "  \"market_cap\": \"...\",\n"
                "  \"logo_url\": \"...\"\n"
                "}\n"
                "Only return the JSON object, without any explanation."
            )
                

            ai_resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = ai_resp.choices[0].message.content.strip()
            print(f"AI response for {cik}: {content}")
            if content.startswith("```json"): content = content.removeprefix("```json").removesuffix("```")
            parsed = json.loads(content.strip())

            supabase.table('ipo').update({
                'is_ipo': parsed.get('IPO', '').lower() == 'yes',
                'shares_offered': null_if_unknown_numeric(parsed.get('Shares Offered')),
                'share_price': parsed.get('share_price', 'unknown'),
                'estimated_ipo_date': null_if_unknown(parsed.get('estimated_ipo_date')),
                'ticker': parsed.get('ticker', 'unknown'),
                'exchange': parsed.get('exchange', 'unknown'),
                'market_cap': null_if_unknown_numeric(parsed.get('market_cap')),
                'logo_url': parsed.get('logo_url', 'unknown')
            }).eq('cik', cik).execute()

        except Exception as e:
            print(f"Analysis failed for {cik}: {e}")

if __name__ == '__main__':
    analyze()
