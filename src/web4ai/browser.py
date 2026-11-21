from fastmcp import FastMCP
from patchright.async_api import async_playwright

_pw = _ctx = _page = None

async def page():
    global _pw, _ctx, _page
    if _page is None or _page.is_closed():
        _pw = _pw or await async_playwright().start()
        _ctx = _ctx or await _pw.chromium.launch_persistent_context(
            "/tmp/prof", channel="chrome", headless=False, no_viewport=True)
        _page = _ctx.pages[-1] if _ctx.pages else await _ctx.new_page()
    return _page

def register_tools(mcp: FastMCP):
    @mcp.tool
    async def see() -> str:
        return await (await page()).locator("body").aria_snapshot()
    
    @mcp.tool
    async def go(url: str) -> str:
        p = await page(); await p.goto(url); return p.url
    
    @mcp.tool
    async def click(selector: str) -> str:
        await (await page()).click(selector); return "ok"
    
    @mcp.tool
    async def type_text(selector: str, text: str) -> str:
        await (await page()).fill(selector, text); return "ok"
    
    @mcp.tool
    async def html() -> str:
        return await (await page()).content()
    
