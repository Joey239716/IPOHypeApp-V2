import requests
from bs4 import BeautifulSoup
import re

def extract_first_1000_words(url: str, user_agent: str = "your-email@example.com") -> str:
    headers = {"User-Agent": user_agent}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove non-visible elements
    for tag in soup(["script", "style", "head", "title", "meta", "[document]"]):
        tag.decompose()

    # Extract visible text
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()

    # Limit to first 1000 words
    words = text.split()
    return ' '.join(words[:1000])

# Example usage
url = "https://www.sec.gov/Archives/edgar/data/1579878/000162828025035381/figma-sx1a.htm"
first_1000_words = extract_first_1000_words(url)
print(first_1000_words)
