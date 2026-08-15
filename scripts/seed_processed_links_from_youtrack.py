#!/usr/bin/env python3
"""
Seed processed_links.txt by querying all YouTrack tickets (open and closed) in the EXFIL project,
extracting Source URLs from issue descriptions, and appending novel links to processed_links.txt.

Issue #11
"""

import asyncio
import os
import re
from typing import List, Set

import httpx
from dotenv import load_dotenv

load_dotenv()

PROCESSED_FILE = "processed_links.txt"
DEFAULT_YOUTRACK_URL = "https://youtrack.worksbyworrell.com"


def extract_source_url(description: str) -> List[str]:
    """Extract Source URLs from a YouTrack issue description."""
    if not description:
        return []

    urls = []
    # Pattern 1: **Source URL:** <url>
    matches = re.findall(r"Source URL:\s*(https?://[^\s\*\)\>]+)", description, re.IGNORECASE)
    if matches:
        urls.extend(matches)

    # Pattern 2: Any raw URL if no explicit Source URL prefix was found
    if not urls:
        raw_urls = re.findall(r"(https?://[^\s\*\)\>]+)", description)
        urls.extend(raw_urls)

    return [u.strip() for u in urls if u.strip()]


async def fetch_youtrack_issues(
    base_url: str, token: str, query: str = "project: EXFIL"
) -> List[dict]:
    """Fetch issues from YouTrack REST API."""
    url = f"{base_url.rstrip('/')}/api/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    params = {
        "query": query,
        "$top": 500,
        "fields": "idReadable,summary,description",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


def load_existing_processed_links(filepath: str) -> Set[str]:
    """Load existing processed links from disk."""
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_processed_links(filepath: str, links: Set[str]) -> None:
    """Save processed links set to disk."""
    sorted_links = sorted(list(links))
    with open(filepath, "w", encoding="utf-8") as f:
        for link in sorted_links:
            f.write(f"{link}\n")


async def main():
    print("========================================")
    print("🌱 SEEDING PROCESSED LINKS FROM YOUTRACK")
    print("========================================\n")

    base_url = os.getenv("YOUTRACK_URL", DEFAULT_YOUTRACK_URL)
    token = os.getenv("YOUTRACK_TOKEN")

    if not token:
        print("⚠️ Warning: YOUTRACK_TOKEN environment variable not set.")
        print("Set YOUTRACK_TOKEN to query YouTrack directly.")
        return

    existing_links = load_existing_processed_links(PROCESSED_FILE)
    print(f"Loaded {len(existing_links)} existing links from {PROCESSED_FILE}.")

    print(f"Querying YouTrack API at {base_url}...")
    try:
        issues = await fetch_youtrack_issues(base_url, token)
        print(f"Retrieved {len(issues)} issues from YouTrack.")
    except Exception as e:
        print(f"❌ Failed to fetch issues from YouTrack: {e}")
        return

    new_links: Set[str] = set()
    for issue in issues:
        desc = issue.get("description", "")
        extracted = extract_source_url(desc)
        for link in extracted:
            if link not in existing_links:
                new_links.add(link)

    total_combined = existing_links.union(new_links)
    save_processed_links(PROCESSED_FILE, total_combined)

    print(
        f"✅ Seeding complete. Added {len(new_links)} new links. Total in {PROCESSED_FILE}: {len(total_combined)}."
    )


if __name__ == "__main__":
    asyncio.run(main())
