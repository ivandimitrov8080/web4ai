# ruff: noqa
from asyncio import TaskGroup, run

from fastmcp import Client

SERVER = "http://127.0.0.1:5353/mcp"

async def call_page(client, id):
    print((await client.call_tool("go", {"url": "https://demo.automationtesting.in/Register.html"}, meta={"page": id})).content[0].text)
    print((await client.call_tool("see", {"type": "all"}, meta={"page": id})).content[0].text)
    print((await client.call_tool("attach", {"selector": "#imagesrc", "file": "/home/ivand/pic/carb.jpg"}, meta={"page": id})).content[0].text)

    #print((await client.call_tool("click", {"selector": "#job-1137387 > td:nth-of-type(5) > a"}, meta={"page": id})).content[0].text)
async def main():
    async with Client(SERVER, timeout=60) as client:
        try:
            await call_page(client, 0)
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}")


run(main())
