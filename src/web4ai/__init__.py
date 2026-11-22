from asyncio import run
from sys import argv

from fastmcp import FastMCP

from web4ai import act, data, read

mcp = FastMCP("web4ai search/fetch web content on steroids")

async def print_tools():
    tools = await mcp.list_tools()
    for tool in tools:
        print(f"{tool.name} === {tool.description}\n---")

def main() -> None:
    data.init_db()
    if "act" in argv:
        act.register_tools(mcp)
    if "read" in argv:
        read.register_tools(mcp)
    run(print_tools())
    run(mcp.run_http_async())

