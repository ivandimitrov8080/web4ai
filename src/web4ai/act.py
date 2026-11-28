from enum import Enum

from fastmcp import Context, FastMCP

from web4ai.lifespan import BrowserCtx
from web4ai.util import get_project_root

class SeeMode(Enum):
    ARIA = "aria"
    ACTIONABLE = "actionable"

class SeeType(Enum):
    ALL = "all"
    CLICKABLE = "click"
    SELECTABLE = "select"
    FILLABLE = "fill"
    TOGGLEABLE = "toggle"
    NAGIVATABLE = "navigate"
    FILE = "files"

with open(f"{get_project_root()}/src/see.js", "r") as f:
    SEE = f.read()

def get_page(ctx: Context) -> int:
    req = ctx.request_context
    if req:
        meta = req.meta or {}
        return meta.get("page", 0)
    else:
        return 0

async def page(browser: BrowserCtx, ctx: Context):
    pages = [p for p in browser.pages if not p.is_closed()]
    idx = get_page(ctx)
    if idx < len(pages):
        return pages[idx]
    else:
        return await browser.new_page()

async def see(browser: BrowserCtx, ctx: Context, mode: SeeMode = SeeMode.ACTIONABLE, type: SeeType = SeeType.ALL) -> str:
    """
    Get the page contents depending on the mode.
    Args:
      mode:
        ACTIONABLE: return a structure representing all actionable elements with their css selectors.
        ARIA: return an aria snapshot of the page.
    """
    with open(f"{get_project_root()}/src/see.js", "r") as f:
        SEE = f.read()
    p = await page(browser, ctx)
    match mode:
        case SeeMode.ARIA:
            return await p.aria_snapshot()
        case SeeMode.ACTIONABLE:
            return await p.evaluate(SEE, type.value)


async def go(url: str, browser: BrowserCtx, ctx: Context) -> str:
    """
    Visit a page in the browser.
    """
    p = await page(browser, ctx);
    await p.goto(url);
    return p.url


async def click(selector: str, browser: BrowserCtx, ctx: Context) -> str:
    """
    Click an element.
    Args:
      selector: The selector found in see
    """
    p = await page(browser, ctx)
    el = await p.query_selector(selector)
    if el:
        type = el.get_attribute("type") or ""
        if type != "file":
            await el.click()
        else:
            return "File input should not be clicked. Use attach tool instead."
    else:
        return "Element not found on page."
    return "ok"

async def attach(selector: str, file: str, browser: BrowserCtx, ctx: Context) -> str:
    """
    Attach a file.
    Args:
      selector: The selector found in see
      file: Absolute path to file to attach
    """
    p = await page(browser, ctx)
    el = await p.query_selector(selector)
    if el:
        type = el.get_attribute("type") or ""
        if type == "file":
            await el.set_input_files(file)
        else:
            return "Element is not of type file so files can't be attached."
    else:
        return "Element not found on page."
    return "ok"

async def type_text(selector: str, text: str, browser: BrowserCtx, ctx: Context) -> str:
    """
    Type text into an element.
    Args:
      selector: The selector found in aria_snapshot
    """
    p = await page(browser, ctx)
    el = await p.query_selector(selector)
    if el:
        await el.fill(text)
    else:
        return "Element not found on page."
    return "ok"

    
def register_tools(mcp: FastMCP):
    mcp.tool(see)
    mcp.tool(go)
    mcp.tool(click)
    mcp.tool(type_text)
    mcp.tool(attach)

