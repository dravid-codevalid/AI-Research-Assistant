import asyncio
import logging
from adapters.agent.streaming_agent import StreamingLiteLLMAgent

logging.basicConfig(level=logging.DEBUG)

async def main():
    agent = StreamingLiteLLMAgent(
        model_name="gemini-flash",
        base_url="http://localhost:4000",
        api_key="sk-litellm-dev-master-key"
    )
    result = await agent.run("explain DSPy library on how it should be used")
    print("FINAL RESULT:")
    print("Answer:", repr(result.answer))
    print("Tool calls:", result.tool_calls)

if __name__ == "__main__":
    asyncio.run(main())
