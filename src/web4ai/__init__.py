import argparse
from asyncio import run
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from web4ai import act, read

@asynccontextmanager
async def lifespan(_):
    await read.crawler.start()
    try:
        yield {}
    finally:
        await read.crawler.close()

mcp = FastMCP("web4ai search/fetch web content on steroids", lifespan=lifespan)

async def register_tools(tools):
    if "act" in tools:
        act.register_tools(mcp)
    if "read" in tools:
        await read.register_tools(mcp)

async def print_tools():
    tools = await mcp.list_tools()
    for tool in tools:
        print(tool.name)


async def call_tool(tool: str, args: list[str]):
    match tool:
        case "fetch":
            return await read.fetch(args[0], pattern=args[1] if len(args) > 1 else ".*")
        case "search":
            return read.search(args[0])


def main() -> str | None:
    parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help')
    parser.add_argument("--call")
    parser.add_argument('-p', "--port", default="8000")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-t", "--tools", default="act,read")
    args, extra = parser.parse_known_args()
    if args.call:
        return run(call_tool(args.call, extra))
    run(register_tools(args.tools))
    run(print_tools())
    mcp.run(transport="http", host=args.host, port=int(args.port))
