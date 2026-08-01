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

    try:
        result = await session.call_tool(
            "create_youtrack_issue",
            arguments={"summary": f"Target: {org} - {identifier}", "description": description},
        )
        print(f"✅ Ticket created successfully: {result}")
        return True
    except Exception as e:
        print(f"❌ Failed to create ticket: {e}")
        return False
