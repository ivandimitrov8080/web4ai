import argparse
from asyncio import run

from fastmcp import FastMCP

from web4ai import act, read
from web4ai.lifespan import web_lifespan

mcp = FastMCP("web4ai search/fetch web content on steroids", lifespan=web_lifespan)

def register_tools(tools):
    if "act" in tools:
        act.register_tools(mcp)
    if "read" in tools:
        read.register_tools(mcp)

async def print_tools():
    tools = await mcp.list_tools()
    for tool in tools:
        print(tool.name)

def main() -> str | None:
    parser = argparse.ArgumentParser(
                    prog='web4ai',
                    description='An web MCP server that helps the AI browse the web not just read it.',
                    epilog='Have fun!')
    parser.add_argument('-p', "--port", default="8000")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("-t", "--tools", default="act,read")
    parser.add_argument("-s", "--stateless", action="store_true")
    args = parser.parse_args()
    register_tools(args.tools)
    run(print_tools())
    run(mcp.run_http_async(transport="http", host=args.host, port=int(args.port), stateless=args.stateless))
