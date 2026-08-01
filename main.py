import asyncio
import os
import subprocess
from datetime import datetime

from google import genai
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

from src.worksbyworrell.evaluator.llm import evaluate_job
from src.worksbyworrell.evaluator.mcp_client import push_to_youtrack
from src.worksbyworrell.harvester.scraper import get_page_text

HOPPER_FILE = "hopper.txt"
REJECT_LOG_FILE = "clutch_rejects.log"
MCP_URL = os.environ.get("WARLOCK_MCP_URL", "https://warlock-nprd.worksbyworrell.com/sse")
CLUTCH_PROMPT_FILE = "../wbw-config-private/agents/clutch.md"
PROFILE_FILE = "../wbw-config-private/profiles/raworre.md"

async def main():
    if not os.path.exists(HOPPER_FILE):
        print(f"Hopper file not found at {HOPPER_FILE}. Creating an empty one.")
        os.makedirs(os.path.dirname(HOPPER_FILE), exist_ok=True)
        with open(HOPPER_FILE, "w") as f:
            f.write("")
        return

    with open(HOPPER_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("Hopper is empty. Go enjoy your night!")
        return

    print(f"Found {len(urls)} jobs in the Hopper. Starting pipeline...")
    
    with open(REJECT_LOG_FILE, "a") as log:
        log.write(f"\n--- Run Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")

    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY environment variable is missing!")
        print("Run: export GEMINI_API_KEY='your-key-here'")
        return
        
    ai_client = genai.Client()

    try:
        token = subprocess.check_output(["gcloud", "auth", "print-identity-token"]).decode().strip()
    except subprocess.CalledProcessError:
        print("❌ Failed to get gcloud token. Run 'gcloud auth login'.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    successful_urls = []
    
    # Load prompts once per run
    with open(CLUTCH_PROMPT_FILE, "r") as f:
        clutch_system = f.read()
    with open(PROFILE_FILE, "r") as f:
        operator_profile = f.read()
    
    async with sse_client(MCP_URL, headers=headers) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("✅ Connected to Warlock MCP Server.")
            
            total_in_tokens = 0
            total_out_tokens = 0
            
            for url in urls:
                job_text = get_page_text(url)
                if not job_text:
                    continue
                    
                eval_data, t_in, t_out = evaluate_job(
                    url, job_text, ai_client, clutch_system, operator_profile
                )
                
                if not eval_data:
                    continue
                    
                print(f"📊 Verdict: {eval_data.get('verdict')}")
                
                if eval_data.get("verdict") == "PROCEED":
                    success = await push_to_youtrack(session, eval_data, url)
                    if not success:
                        continue
                else:
                    print(f"🛑 Job rejected by Clutch: {url}")
                    reason = eval_data.get('rejection_reason', 'No reason provided')
                    with open(REJECT_LOG_FILE, "a") as log:
                        log.write(f"REJECTED: {url} | Org: {eval_data.get('organization')} | Title: {eval_data.get('identifier')} | Reason: {reason}\n")
                
                total_in_tokens += t_in
                total_out_tokens += t_out
                successful_urls.append(url)
            
    remaining_urls = [u for u in urls if u not in successful_urls]
    with open(HOPPER_FILE, "w") as f:
        for u in remaining_urls:
            f.write(f"{u}\n")
    print(f"🧹 Run complete. {len(remaining_urls)} jobs left in Hopper due to errors.")
    print(f"📈 Total API Tokens Consumed this run: {total_in_tokens} IN | {total_out_tokens} OUT")

if __name__ == "__main__":
    asyncio.run(main())
