import asyncio

q = asyncio.Queue()

async def run():
    await q.put(1)
    print("done", q.qsize())

asyncio.run(run())
