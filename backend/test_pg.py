import asyncio
import asyncpg

async def test():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@127.0.0.1:15432/postgres')
        print('Connected successfully')
        await conn.close()
    except Exception as e:
        print(f"Failed to connect: {e}")

asyncio.run(test())
