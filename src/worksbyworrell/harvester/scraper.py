import requests
from bs4 import BeautifulSoup


def get_page_text(url: str) -> str:
    print(f"🌐 Scraping {url}...")
    try:
        # Standard User-Agent to avoid basic blocks
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        # Extract just the text from the HTML
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"❌ Failed to scrape {url}: {e}")
        return ""
