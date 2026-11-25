# ruff: noqa
from asyncio import TaskGroup, run

from fastmcp import Client

SERVER = "http://127.0.0.1:5353/mcp"

async def call_page(client, id):
    await client.call_tool(
        "go",
        {"url": "https://www.example.com"},
        meta={"page": id}
    )
async def main():
    async with Client(SERVER, timeout=60) as client:
        try:
            async with TaskGroup() as tg:
                for i in range(10):
                    tg.create_task(call_page(client, i))
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}")


run(main())
