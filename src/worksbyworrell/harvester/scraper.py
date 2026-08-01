import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def fetch_job_links(board_url: str) -> list[str]:
    print(f"🕸️ Harvesting links from {board_url}...")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(board_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            href_lower = href.lower()

            # Exclude pagination, search queries, and broad hubs
            if "?" in href_lower or "/remote" in href_lower or "/search" in href_lower:
                continue

            # Target explicit job detail pages that have a slug or ID
            # Examples: /job/slug/123, /careers/slug, /jobs/123
            if re.search(r"/(job|jobs|careers|role|position)/.+", href_lower):
                if href.startswith("/"):
                    parsed = urlparse(board_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    href = base_url + href
                links.append(href)

        unique_links = list(set(links))
        print(f"✅ Harvested {len(unique_links)} potential job links.")
        return unique_links
    except Exception as e:
        print(f"❌ Failed to harvest {board_url}: {e}")
        return []


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
