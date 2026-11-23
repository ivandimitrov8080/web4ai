import asyncio

from fastmcp import Client

SERVER = "http://127.0.0.1:5353/mcp"
URL = "https://raw.githubusercontent.com/NixOS/nixpkgs/master/nixos/modules/services/matrix/matrix-appservice-irc.nix"


async def main():
    async with Client(SERVER, timeout=60) as client:
        try:
            result = await client.call_tool(
                "fetch",
                {"url": URL},
            )
            print(result)
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}")


asyncio.run(main())
