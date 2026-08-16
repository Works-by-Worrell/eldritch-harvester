import json
from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class Scores(BaseModel):
    autonomy_proxy: int = Field(description="1-10 rating for autonomy")
    maturity_proxy: int = Field(description="1-10 rating for engineering maturity")
    stack_match: int = Field(description="1-10 rating for tech stack alignment")


class ClutchEvaluation(BaseModel):
    organization: str
    identifier: str
    baseline_requirements_met: bool | None
    scores: Scores
    golden_ticket: bool
    priority: Literal["Show-stopper", "Critical", "Major", "Minor", "Normal"]
    verdict: Literal["PROCEED", "REJECT"]
    rejection_reason: str
    strategic_questions: list[str]
    actionable_next_steps: list[str]


def evaluate_job(
    url: str, job_text: str, client: genai.Client, clutch_system: str, operator_profile: str
):
    print(f"🕵️  Clutch is evaluating: {url}...")

    if not job_text:
        return None, 0, 0

    system_instruction = f"""
    You are Clutch.
    Here is your core directive and JSON contract:
    {clutch_system}

    Here is the Operator's Private Profile & Exfiltration Protocol:
    {operator_profile}
    """

    prompt = (
        f"Evaluate the following job posting:\n\nURL: {url}\n\nPOSTING TEXT:\n{job_text[:30000]}"
    )

    print("🧠 Gemini is thinking...")
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ClutchEvaluation,
                temperature=0.0,  # Zero-variance deterministic sampling
            ),
        )

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
            print(
                f"💰 Tokens used: {usage.prompt_token_count} in | {usage.candidates_token_count} out | Total: {usage.total_token_count}"
            )
            return json.loads(response.text), usage.prompt_token_count, usage.candidates_token_count

        return json.loads(response.text), 0, 0
    except Exception as e:
        print(f"❌ Failed to evaluate with Gemini: {e}")
        return None, 0, 0
