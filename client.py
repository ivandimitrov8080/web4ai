# ruff: noqa
import asyncio

from fastmcp import Client

SERVER = "http://127.0.0.1:5354/mcp"



async def main():
    async with Client(SERVER, timeout=60) as client:
        try:
            await client.call_tool(
                "go",
                {"url": "https://www.httpbin.org/forms/post"},
            )
            see = await client.call_tool(
                "see",
            )
            print(see)
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}")


asyncio.run(main())
