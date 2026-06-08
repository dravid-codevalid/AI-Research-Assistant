import asyncio
from adapters.agent.streaming_agent import StreamingLiteLLMAgent

async def test():
    agent = StreamingLiteLLMAgent(model_name="gemini-flash")
    print("=" * 60)
    print("Testing Native Function Calling Agent")
    print("=" * 60)

    async for event in agent.run_stream(
        "What is the population of Tokyo? Search the web for the latest data.",
        workspace_id="test-workspace",
    ):
        etype = event.get("event")
        if etype == "thought":
            print(f"  [THOUGHT] {event['text']}")
        elif etype == "tool_call":
            print(f"  [TOOL]    {event['tool']}({event['input'][:80]}...)")
            print(f"            => {event['output'][:120]}...")
        elif etype == "token":
            print(event["text"], end="", flush=True)
        elif etype == "done":
            print(f"\n{'=' * 60}")
            print(f"FINAL ANSWER: {event['answer'][:200]}")
            print(f"TOOLS USED:   {len(event['tool_calls'])}")
            print(f"THOUGHTS:     {len(event['thoughts'])}")
            print(f"MODEL:        {event['model_used']}")
        elif etype == "error":
            print(f"  [ERROR]   {event['text']}")

if __name__ == "__main__":
    asyncio.run(test())
