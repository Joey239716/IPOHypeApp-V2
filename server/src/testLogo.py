import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from io import BytesIO
from PIL import Image

USER_AGENT = "joeydaspam@gmail.com"
HEADERS    = {"User-Agent": USER_AGENT}

def fetch_first_img_src(page_url: str) -> str | None:
    resp = requests.get(page_url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    img = soup.find("img")
    return img["src"] if img and img.has_attr("src") else None

def download_image(img_url: str) -> bytes:
    resp = requests.get(img_url, headers=HEADERS, stream=True)
    resp.raise_for_status()
    return resp.content

def save_100x100(page_url: str, output_path: str, quality: int = 80):
    # 1) find first image src on the page
    src = fetch_first_img_src(page_url)
    if not src:
        raise RuntimeError("No <img> found on page")
    img_url = urljoin(page_url, src)

    # 2) download it
    img_bytes = download_image(img_url)

    # 3) open & thumbnail to 100×100
    img = Image.open(BytesIO(img_bytes))
    img.thumbnail((100, 100))

    # 4) save as JPEG (or PNG if you prefer)
    fmt = "JPEG" if img.format != "PNG" else "PNG"
    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs.update({"quality": quality, "optimize": True})
    else:
        save_kwargs.update({"optimize": True})

    img.save(output_path, **save_kwargs)
    print(f"Saved 100×100 image to {output_path}")

# Example usage:
if __name__ == "__main__":
    page = "https://www.sec.gov/Archives/edgar/data/1795586/000162828025028733/chimefinancialinc-sx1a.htm"
    save_100x100(page, "logo_100x100.jpg")
