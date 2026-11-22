import argparse
from asyncio import run

from fastmcp import FastMCP

from web4ai import act, data, read

mcp = FastMCP("web4ai search/fetch web content on steroids")

def register_tools(tools):
    if "act" in tools:
        act.register_tools(mcp)
    if "read" in tools:
        read.register_tools(mcp)

async def print_tools():
    tools = await mcp.list_tools()
    for tool in tools:
        print(tool.name)

def main() -> None:
    parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help')
    parser.add_argument('-p', "--port", default="8000")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-t", "--tools", default="act,read")
    args = parser.parse_args()
    data.init_db()
    register_tools(args.tools)
    run(print_tools())
    mcp.run(transport="http", host=args.host, port=int(args.port))
