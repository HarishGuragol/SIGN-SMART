"""Quick standalone check that the AgenticOrg SDK can actually reach the
hackathon endpoint and run one of our agents, independent of the FastAPI app.
Run: python test_agenticorg.py
"""
import json
import sys

from app import config


def main():
    if not config.AGENTICORG_API_KEY:
        print("AGENTICORG_API_KEY is not set in .env — nothing to test.")
        sys.exit(1)

    print(f"AgenticOrg URL: {config.AGENTICORG_URL}")
    print(f"Agent (extract): {config.env('AGENTICORG_AGENT_EXTRACT', 'agreement_extractor')}")

    from agenticorg import AgenticOrg

    kwargs = {"api_key": config.AGENTICORG_API_KEY}
    if config.AGENTICORG_URL:
        kwargs["base_url"] = config.AGENTICORG_URL
    try:
        client = AgenticOrg(**kwargs)
    except TypeError:
        print("AgenticOrg(...) didn't accept base_url — checking SDK signature:")
        help(AgenticOrg)
        sys.exit(1)

    agent_name = config.env("AGENTICORG_AGENT_EXTRACT", "agreement_extractor")
    print(f"\nCalling agents.run('{agent_name}', ...) with a tiny test input...")
    try:
        result = client.agents.run(
            agent_name,
            inputs={"instructions": "Extract this agreement.", "input": "Monthly rent is Rs 10000."},
        )
        print(f"status: {result.status}")
        print(f"confidence: {getattr(result, 'confidence', None)}")
        print(f"output: {json.dumps(result.output, indent=2) if isinstance(result.output, (dict, list)) else result.output}")
        print("\n✅ AgenticOrg connection works.")
    except Exception as e:
        print(f"\n❌ AgenticOrg call failed: {e}")
        print("(This is fine for the demo — MOCK_LLM=1 in .env bypasses this entirely.)")


if __name__ == "__main__":
    main()
