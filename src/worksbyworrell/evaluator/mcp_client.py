from mcp.client.session import ClientSession


async def push_to_youtrack(session: ClientSession, evaluation: dict, url: str):
    """Uses the Warlock MCP server to create a YouTrack issue."""
    print("🚀 Torque is pushing the evaluation to YouTrack...")

    org = evaluation.get("organization", "Unknown")
    identifier = evaluation.get("identifier", "Unknown Role")

    description = f"**Source URL:** {url}\n\n"
    description += f"**Salary Baseline Met:** {evaluation.get('baseline_requirements_met')}\n\n"
    description += "**Scores:**\n"

    scores = evaluation.get("scores", {})
    description += f"- Autonomy: {scores.get('autonomy_proxy', 0)}/10\n"
    description += f"- Maturity: {scores.get('maturity_proxy', 0)}/10\n"
    description += f"- Stack Match: {scores.get('stack_match', 0)}/10\n\n"

    description += "**Strategic Questions:**\n"
    for q in evaluation.get("strategic_questions", []):
        description += f"- {q}\n"

    if evaluation.get("actionable_next_steps"):
        description += "\n**Action Plan:**\n"
        for step in evaluation.get("actionable_next_steps"):
            description += f"- [ ] {step}\n"

    if evaluation.get("company_research"):
        description += "\n**Company Dossier:**\n"
        description += f"{evaluation.get('company_research')}\n\n"

    custom_fields = [
        {
            "name": "Autonomy",
            "$type": "SimpleIssueCustomField",
            "value": scores.get("autonomy_proxy", 0),
        },
        {
            "name": "Maturity",
            "$type": "SimpleIssueCustomField",
            "value": scores.get("maturity_proxy", 0),
        },
        {
            "name": "StackMatch",
            "$type": "SimpleIssueCustomField",
            "value": scores.get("stack_match", 0),
        },
    ]

    tags = []
    if evaluation.get("golden_ticket"):
        print("🏆 GOLDEN TICKET IDENTIFIED! Preparing high-priority payload for Torque...")
        tags.append("GoldenTicket")
        description = "**🏆 GOLDEN TICKET!** Drop everything and apply yesterday.\n\n" + description

    priority = evaluation.get("priority", "Normal")
    if evaluation.get("golden_ticket"):
        priority = "Show-stopper"

    import asyncio

    MAX_RETRIES = 5
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await session.call_tool(
                "create_youtrack_issue",
                arguments={
                    "summary": f"[ExFil Protocol] {org} - {identifier}",
                    "description": description,
                    "priority": priority,
                    "custom_fields": custom_fields,
                    "tags": tags,
                },
            )

            response_text = result.content[0].text if result.content else ""
            if "429" in response_text or "Too Many Requests" in response_text:
                if attempt < MAX_RETRIES:
                    wait_sec = attempt * 5
                    print(
                        f"⚠️ 429 Rate limit response from YouTrack/MCP. Retrying in {wait_sec}s (Attempt {attempt}/{MAX_RETRIES})..."
                    )
                    await asyncio.sleep(wait_sec)
                    continue
                else:
                    print(
                        f"❌ Failed to create ticket due to repeated 429 rate limits: {response_text}"
                    )
                    return False

            if response_text.startswith("Failed"):
                print(f"❌ Failed to create ticket: {response_text}")
                return False

            print(f"✅ Ticket created successfully: {response_text}")
            return True
        except (Exception, BaseExceptionGroup) as e:
            err_str = str(e)
            if ("429" in err_str or "Too Many Requests" in err_str) and attempt < MAX_RETRIES:
                wait_sec = attempt * 5
                print(
                    f"⚠️ 429 Rate limit exception encountered: {e}. Retrying in {wait_sec}s (Attempt {attempt}/{MAX_RETRIES})..."
                )
                await asyncio.sleep(wait_sec)
            else:
                print(f"❌ Failed to create ticket via MCP: {e}")
                return False

    return False
