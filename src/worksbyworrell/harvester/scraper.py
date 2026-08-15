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

            # Strip query string for path checking
            clean_href = href_lower.split("?")[0].rstrip("/")

            # Exclude pagination, search queries, hubs, region, and category pages
            if "?" in href_lower or "/remote" in clean_href or "/search" in clean_href:
                continue

            # Exclude known category/region index paths
            if re.search(
                r"/jobs/(mena|na|sa|eu|apac|operations|sales|marketing|engineering|product)/",
                clean_href,
            ):
                continue

            # Target explicit job detail pages that end with a numeric ID or UUID
            # Examples: /job/slug/10170358, /jobs/company/12345, /careers/role/a1b2c3d4-e5f6-7890
            is_job_detail = re.search(
                r"/(job|jobs|careers|role|position)/.+/\d+$", clean_href
            ) or re.search(
                r"/(job|jobs|careers|role|position)/.+/[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
                clean_href,
            )

            if is_job_detail:
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
