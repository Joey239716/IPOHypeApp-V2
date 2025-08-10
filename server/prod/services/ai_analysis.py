 # === services/ai_analysis.py ===
# Purpose: Analyze SEC IPO filings with GPT and upsert results

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from supabase import Client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AnalyzeIPO:
    def __init__(self, supabase_client: Client, openai_client: OpenAI):
        self.supabase = supabase_client
        self.openai = openai_client
        self.headers = {"User-Agent": "joeydaspam@gmail.com"}

    def null_if_unknown(self, val):
        return None if isinstance(val, str) and val.strip().lower() == "unknown" else val

    def null_if_unknown_numeric(self, val):
        if isinstance(val, str):
            if val.strip().lower() == "unknown":
                return None
            val = val.replace(",", "").replace("$", "").strip()
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return None

    def _is_placeholder(self, val):
        """Return True if the value is a known placeholder pattern."""
        if not isinstance(val, str):
            return False
        patterns = [
            r"^\[.*\]$",        # anything in brackets like [•], [__], []
            r"^XX$", r"^TBD$", r"^N/A$", r"^-$", r"^–$", r"^—$",  # dash variants
            r"^\s*$"            # empty/whitespace
        ]
        return any(re.match(p, val.strip(), flags=re.IGNORECASE) for p in patterns)

    def analyze_one(self, cik: str, filing_url: str, company_name: str):
        """Analyze a single filing and update the database."""
        try:
            # Fetch the filing text
            r = requests.get(filing_url, headers=self.headers)
            r.raise_for_status()
            try:
                soup = BeautifulSoup(r.text, "lxml")
            except Exception:
                soup = BeautifulSoup(r.text, "html.parser")

            for tag in soup(["script", "style", "head", "title", "meta", "[document]"]):
                tag.decompose()
            text = re.sub(r"\s+", " ", soup.get_text()).strip()
            snippet = " ".join(text.split()[:1000])

            # Build the GPT prompt
            prompt = (
                f"You extract IPO metadata from SEC filing text.\n\n"
                f"INPUT:\n{snippet}\nCOMPANY: {company_name}\n\n"
                "Operate in two phases: (A) reason privately; (B) OUTPUT JSON ONLY (no markdown, no notes).\n\n"
                "------------------------------------------------------------\n"
                "IPO CLASSIFICATION\n"
                "------------------------------------------------------------\n"
                "\"IPO\" = \"yes\" if:\n"
                "- Issuer is registering NEW securities for cash proceeds AND seeking FIRST-TIME listing on a national exchange (see normalized list below), including SPAC IPOs selling UNITS.\n\n"
                "\"IPO\" = \"no\" if ANY of these apply:\n"
                "- Pure resale/secondary (no primary proceeds to issuer)\n"
                "- General shelf (Rule 415) not tied to IPO\n"
                "- Business combination / de-SPAC (e.g., S-4/DEFM14A)\n"
                "- Exchange offer or follow-on offering\n"
                "- Rule 462(b) / S-1MEF / F-1MEF / RW\n"
                "- Warrant-only / rights-only / preferred-only sale\n"
                "- OTC-only listing (OTCQX / OTCQB / OTCBB / Over-the-Counter) without national exchange\n\n"
                "------------------------------------------------------------\n"
                "EXTRACTION RULES\n"
                "------------------------------------------------------------\n"
                "1) Shares Offered:\n"
                "- If UNITS are sold:\n"
                "  • Identify unit composition (e.g., “each unit consists of…”).\n"
                "  • If a unit includes ≥1 share or ADS, Shares Offered = number_of_units × shares_per_unit (ignore warrants/rights).\n"
                "  • If a unit includes NO share/ADS → IPO=\"no\".\n"
                "- If ADS are sold: count ADS (do NOT convert to underlying shares).\n"
                "- If common/ordinary/Class A shares are sold: use that share count.\n"
                "- Ignore over-allotment (greenshoe) and selling shareholder blocks.\n"
                "- Placeholders ([•], [*], [__], [], [ . ], XX, TBD, N/A, em/en dash, underscores) → \"unknown\".\n"
                "- Output digits only; no commas or text.\n\n"
                "2) share_price:\n"
                "- Use the price for the sold security (per UNIT if units; else per share/ADS).\n"
                "- Format exactly:\n"
                "  \"<number>$\"  OR  \"<number>$ - <number>$\"\n"
                "- No commas. If placeholder/ambiguous → \"unknown\".\n\n"
                "3) exchange (normalize to exactly one of):\n"
                "- \"NASDAQ\", \"Nasdaq Capital Market\", \"Nasdaq Global Market\", \"Nasdaq Global Select Market\",\n"
                "  \"NYSE\", \"NYSE American\", \"NYSE Arca\", \"Cboe\"\n"
                "- Normalize examples:\n"
                "  • \"The Nasdaq Stock Market LLC\", \"NASDAQ Stock Exchange\" → \"NASDAQ\"\n"
                "  • \"Nasdaq CM\", \"Nasdaq Capital\" → \"Nasdaq Capital Market\"\n"
                "  • \"Nasdaq Global\" → \"Nasdaq Global Market\"\n"
                "  • \"Nasdaq Global Select\" → \"Nasdaq Global Select Market\"\n"
                "  • \"New York Stock Exchange\", \"The NYSE\" → \"NYSE\"\n"
                "  • \"NYSE American LLC\" → \"NYSE American\"\n"
                "  • \"NYSE Arca LLC\" → \"NYSE Arca\"\n"
                "  • \"Cboe BZX/EDGX/EDGA Exchange, Inc.\" → \"Cboe\"\n"
                "- If OTC-only or unclear → \"unknown\".\n"
                "- Must not be a placeholder.\n\n"
                "4) market_cap:\n"
                "- Compute ONLY if BOTH post-IPO total shares outstanding AND a price (or range) exist.\n"
                "- For price ranges, use midpoint. Multiply shares × price. Digits only; else \"unknown\".\n\n"
                "------------------------------------------------------------\n"
                "HARD VALIDATION (apply before output)\n"
                "------------------------------------------------------------\n"
                "- Placeholders for Shares Offered, share_price, or exchange → \"unknown\".\n"
                "- \"Shares Offered\": ^[0-9]+$ or \"unknown\".\n"
                "- \"share_price\": ^[0-9]+(\\.[0-9]+)?\\$$  OR  ^[0-9]+(\\.[0-9]+)?\\$ - [0-9]+(\\.[0-9]+)?\\$$  OR \"unknown\".\n"
                "- \"market_cap\": ^[0-9]+$ or \"unknown\".\n"
                "- \"exchange\": must be in normalized list or \"unknown\".\n"
                "- If per-unit and per-share prices both appear for a unit deal, prefer per-unit.\n"
                "- If only secondary shares are offered → IPO = \"no\".\n\n"
                "------------------------------------------------------------\n"
                "OUTPUT JSON ONLY:\n"
                "------------------------------------------------------------\n"
                "{{\n"
                "  \"IPO\": \"yes\" or \"no\",\n"
                "  \"Shares Offered\": \"...\",\n"
                "  \"share_price\": \"...\",\n"
                "  \"exchange\": \"...\",\n"
                "  \"market_cap\": \"...\"\n"
                "}}\n"
            )


            # Call GPT
            ai_resp = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = ai_resp.choices[0].message.content.strip()
            if content.startswith("json"):
                content = content.removeprefix("json").removesuffix("")
            parsed = json.loads(content)

            # Sanitize placeholders
            for field in ["Shares Offered", "share_price", "exchange", "market_cap"]:
                if self._is_placeholder(parsed.get(field)):
                    parsed[field] = "unknown"

            # Upsert results into DB & set analyzed=True
            self.supabase.table("ipo").update({
                "is_ipo": parsed.get("IPO", "").lower() == "yes",
                "shares_offered": self.null_if_unknown_numeric(parsed.get("Shares Offered")),
                "share_price": self.null_if_unknown(parsed.get("share_price")),
                "exchange": self.null_if_unknown(parsed.get("exchange")),
                "market_cap": self.null_if_unknown_numeric(parsed.get("market_cap")),
                "analyzed": True
            }).eq("cik", cik).execute()

        except Exception as e:
            print(f"Analysis failed for {cik}: {e}")