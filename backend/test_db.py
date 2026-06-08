import asyncio
from sqlalchemy import select
from infrastructure.database import async_session_factory
from infrastructure.models import ResearchTaskModel

async def main():
    async with async_session_factory() as s:
        res = await s.execute(select(ResearchTaskModel))
        tasks = res.scalars().all()
        for t in tasks:
            print(f"ID: {t.id}")
            print(f"Status: {t.status}")
            print(f"Answer: {repr(t.answer)}")
            print(f"Tool calls: {t.tool_calls}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
