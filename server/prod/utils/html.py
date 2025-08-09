from bs4 import BeautifulSoup

__all__ = ["clean_html"]

def clean_html(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "head", "meta", "title"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())