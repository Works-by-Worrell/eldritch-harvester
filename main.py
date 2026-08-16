#!/usr/bin/env python
import asyncio
import builtins
import os
import subprocess
from datetime import datetime
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

os.makedirs("logs", exist_ok=True)

_orig_print = builtins.print


def tee_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    try:
        today = datetime.now().strftime("%Y_%m_%d")
        with open(f"logs/eldritch_run_{today}.log", "a", encoding="utf-8") as log_f:
            msg = " ".join(str(a) for a in args)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_f.write(f"[{timestamp}] {msg}\n")
    except Exception:
        pass  # Fallback safely if log writing fails


builtins.print = tee_print

from google import genai
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from src.worksbyworrell.evaluator.llm import evaluate_job
from src.worksbyworrell.evaluator.mcp_client import push_to_youtrack
from src.worksbyworrell.harvester.scraper import fetch_job_links, get_page_text
from src.worksbyworrell.storage import LocalCacheManager

HOPPER_FILE = "hopper.txt"
SEARCH_TERMS_FILE = "search_terms.txt"
TARGET_BOARDS_FILE = "target_boards.txt"
PROCESSED_FILE = "processed_links.txt"
OPERATOR_PROFILE = os.environ.get("OPERATOR_PROFILE", "raworre")


async def main():
    print("\n========================================")
    print("🌌 ELDRITCH HARVESTER AWAKENS")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("========================================\n")

    cache_mgr = LocalCacheManager(db_path="harvester_cache.db")
    processed_links = cache_mgr.download_processed_links()

    if os.path.exists(SEARCH_TERMS_FILE):
        with open(SEARCH_TERMS_FILE, "r") as f:
            search_terms = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        search_terms = []

    if os.path.exists(TARGET_BOARDS_FILE):
        with open(TARGET_BOARDS_FILE, "r") as f:
            target_boards = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    else:
        target_boards = []

    # 1. Harvest Phase
    print("🔎 Commencing Harvest Phase...")
    new_links_found = 0
    for board in target_boards:
        for term in search_terms:
            print(f"🎯 Target Acquired: '{term}'")
            query = quote_plus(term)
            target_url = board.format(term=query)

            links = fetch_job_links(target_url)
            if links:
                novel_links = [l for l in links if l not in processed_links]
                if novel_links:
                    with open(HOPPER_FILE, "a") as f:
                        for link in novel_links:
                            f.write(f"{link}\n")
                    new_links_found += len(novel_links)

    if new_links_found > 0:
        print(f"📥 Added {new_links_found} new jobs to the Hopper.")

    # 2. Setup Hopper
    if not os.path.exists(HOPPER_FILE):
        print(f"Hopper file not found at {HOPPER_FILE}. Creating an empty one.")
        os.makedirs(os.path.dirname(HOPPER_FILE), exist_ok=True)
        with open(HOPPER_FILE, "w") as f:
            f.write("")
        return

    with open(HOPPER_FILE, "r") as f:
        # Preserve order but remove duplicates
        urls = list(dict.fromkeys([line.strip() for line in f if line.strip()]))

    # Re-write the deduplicated list just to keep the file clean
    with open(HOPPER_FILE, "w") as f:
        for u in urls:
            f.write(f"{u}\n")

    if not urls:
        print("Hopper is empty. Go enjoy your night!")
        return

    print(f"Found {len(urls)} jobs in the Hopper.")

    MAX_JOBS = int(os.environ.get("MAX_JOBS_PER_RUN", "5"))
    urls_to_process = urls[:MAX_JOBS]
    urls_to_keep_for_later = urls[MAX_JOBS:]

    print(
        f"Processing up to {MAX_JOBS} jobs this run. {len(urls_to_keep_for_later)} will wait for next time."
    )

    today_str = datetime.now().strftime("%Y_%m_%d")
    reject_log_file = f"logs/clutch_rejects_{today_str}.log"

    with open(reject_log_file, "a") as log:
        log.write(f"\n--- Run Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable is missing!")
        print("Run: export GEMINI_API_KEY='your-key-here'")
        return

    ai_client = genai.Client()

    successful_urls = []
    total_in_tokens = 0
    total_out_tokens = 0

    image_name = "ghcr.io/works-by-worrell/warlock-mcp:latest"
    print(f"🐳 Validating Docker Image: {image_name}")
    print("   (This will pull the image if it's missing or updating. Please wait...)")
    subprocess.run(["docker", "pull", image_name], check=False)

    MAX_RETRIES = 5
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            server_params = StdioServerParameters(
                command="docker",
                args=[
                    "run",
                    "-i",
                    "--rm",
                    "--env-file",
                    ".env",
                    "ghcr.io/works-by-worrell/warlock-mcp:latest",
                    "--transport",
                    "stdio",
                ],
            )
            async with stdio_client(server_params) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    print("✅ Connected to Warlock MCP Server via STDIO.")

                    # Fetch profiles from MCP server
                    print("Fetching profiles from MCP server...")
                    clutch_resource = await session.read_resource("agent://clutch")
                    clutch_system = clutch_resource.contents[0].text

                    profile_resource = await session.read_resource(
                        f"profile://{OPERATOR_PROFILE}/combined"
                    )
                    operator_profile = profile_resource.contents[0].text
                    print("✅ Profiles loaded successfully.")

                    for url in urls_to_process:
                        try:
                            job_text = get_page_text(url)
                            if not job_text:
                                continue

                            eval_data, t_in, t_out = evaluate_job(
                                url, job_text, ai_client, clutch_system, operator_profile
                            )

                            if not eval_data:
                                continue

                            # Handle cases where Gemini wraps the JSON object in an array
                            if isinstance(eval_data, list) and len(eval_data) > 0:
                                eval_data = eval_data[0]

                            if not isinstance(eval_data, dict):
                                print(f"❌ Gemini returned unexpected format: {type(eval_data)}")
                                continue

                            print(f"📊 Verdict: {eval_data.get('verdict')}")

                            if str(eval_data.get("verdict", "")).strip().upper() == "PROCEED":
                                org_name = eval_data.get("organization")
                                if org_name and org_name.lower() != "unknown":
                                    try:
                                        print(f"🔍 Researching company dossier for: {org_name}...")
                                        research_prompt = f"Provide a concise 3-4 sentence summary of the company '{org_name}' including their main product/mission, year founded, and general industry reputation based on your pre-trained knowledge base."
                                        research_response = ai_client.models.generate_content(
                                            model="gemini-3.6-flash",
                                            contents=research_prompt,
                                        )
                                        eval_data["company_research"] = (
                                            research_response.text.strip()
                                        )
                                    except Exception as e:
                                        print(f"⚠️ Failed to research company {org_name}: {e}")
                                        eval_data["company_research"] = (
                                            "Research failed or unavailable."
                                        )

                                success = await push_to_youtrack(session, eval_data, url)
                                if not success:
                                    continue
                            else:
                                print(f"🛑 Job rejected by Clutch: {url}")
                                reason = eval_data.get("rejection_reason", "No reason provided")
                                org = eval_data.get("organization", "Unknown")
                                title = eval_data.get("identifier", "Unknown")
                                cache_mgr.log_rejection_to_db(url, org, title, reason)

                            total_in_tokens += t_in
                            total_out_tokens += t_out
                            successful_urls.append(url)

                            # Mark as permanently processed
                            processed_links.add(url)
                            cache_mgr.upload_processed_links(processed_links)
                            await asyncio.sleep(5.0)
                        except (Exception, BaseExceptionGroup) as url_err:
                            print(f"⚠️ Isolated error on {url}: {url_err}. Retrying next run.")
                            continue
            break
        except (Exception, BaseExceptionGroup) as e:
            if attempt < MAX_RETRIES:
                wait_sec = attempt * 5
                print(
                    f"⚠️ MCP Session interrupted ({e}). Retrying connection in {wait_sec}s (Attempt {attempt}/{MAX_RETRIES})..."
                )
                await asyncio.sleep(wait_sec)
            else:
                print(
                    f"❌ Connection to Warlock MCP Server failed after {MAX_RETRIES} attempts: {e}"
                )

    remaining_urls = [
        u for u in urls_to_process if u not in successful_urls
    ] + urls_to_keep_for_later
    with open(HOPPER_FILE, "w") as f:
        for u in remaining_urls:
            f.write(f"{u}\n")
    print(f"🧹 Run complete. {len(remaining_urls)} jobs left in Hopper due to errors.")
    print(f"📈 Total API Tokens Consumed this run: {total_in_tokens} IN | {total_out_tokens} OUT")


if __name__ == "__main__":
    asyncio.run(main())
