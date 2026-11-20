from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP
from patchright.async_api import (
    BrowserContext,
    Locator,
    Page,
    Playwright,
    async_playwright,
)
from toon import encode

_REF_ATTR = "data-web4ai-ref"

_PROFILE_DIR = Path(
    os.environ.get("WEB4AI_BROWSER_PROFILE") or Path.home() / ".local/share/web4ai/browser"
)
_SCREENSHOT_DIR = Path(
    os.environ.get("WEB4AI_SCREENSHOT_DIR") or Path.home() / ".local/share/web4ai/screenshots"
)
_HEADLESS = os.environ.get("WEB4AI_HEADLESS", "0").strip().lower() in {"1", "true", "yes", "on"}

_TIMEOUT_MS = 8_000
_NAV_TIMEOUT_MS = 30_000

Action = Callable[[Page], Awaitable[str]]

_PW: Playwright | None = None
_CTX: BrowserContext | None = None
_PAGE: Page | None = None
_DIALOG = None
_LOCK = asyncio.Lock()


# --------------------------------------------------------------------------- #
# session plumbing
# --------------------------------------------------------------------------- #
def _on_dialog(dialog) -> None:
    """Park the dialog; it blocks the page until browser_handle_dialog runs."""
    global _DIALOG
    _DIALOG = dialog


def _adopt(page: Page) -> None:
    page.set_default_timeout(_TIMEOUT_MS)
    page.on("dialog", _on_dialog)


async def _launch() -> None:
    global _PW, _CTX
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _PW = await async_playwright().start()

    # Patchright best practice: persistent context, real Chrome,
    # real window (no_viewport), no custom UA/headers/args.
    options = {
        "user_data_dir": str(_PROFILE_DIR),
        "headless": _HEADLESS,
        "no_viewport": True,
    }
    try:
        _CTX = await _PW.chromium.launch_persistent_context(channel="chrome", **options)
    except Exception:  # chrome not installed -> bundled chromium
        _CTX = await _PW.chromium.launch_persistent_context(**options)


async def _page_or_create() -> Page:
    global _PAGE
    if _CTX is None:
        await _launch()
    assert _CTX is not None
    if _PAGE is None or _PAGE.is_closed():
        open_pages = [p for p in _CTX.pages if not p.is_closed()]
        _PAGE = open_pages[-1] if open_pages else await _CTX.new_page()
        _adopt(_PAGE)
    return _PAGE


async def _act(
    action: Action,
    *,
    include_snapshot: bool = True,
    max_elements: int = 250,
) -> str:
    """Run ``action(page)`` under the session lock, never raise to the model."""
    if _DIALOG is not None:
        return (
            f"Error: a {_DIALOG.type} dialog is blocking the page "
            f"({_DIALOG.message!r}). Call browser_handle_dialog first."
        )
    async with _LOCK:
        try:
            page = await _page_or_create()
            message = await action(page)
            if not include_snapshot:
                return message
            return f"{message}\n\n{await _snapshot(page, max_elements)}"
        except Exception as exc:  # noqa: BLE001 - surfaced as tool text
            return f"Error: {type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------- #
# snapshot: mark elements with refs, emit an ARIA-ish tree
# --------------------------------------------------------------------------- #
_SNAPSHOT_JS = ""
with open("browser-snapshot.js", "r") as f:
    _SNAPSHOT_JS = f.readline()

async def _snapshot(page: Page, max_elements: int = 250) -> str:
    data = await page.evaluate(_SNAPSHOT_JS, {"maxElements": max_elements})
    header = f'Page: {data["title"]!r} - {data["url"]}\nScroll: {data["scroll"]}'
    body = "\n".join(data["lines"]) or "(no interactive elements found)"
    if data["truncated"]:
        body += f"\n... truncated at {data['count']} elements"
    return f"{header}\n\n{body}"


# --------------------------------------------------------------------------- #
# target resolution: "e5" / "[ref=e5]" / CSS / Playwright selector / text
# --------------------------------------------------------------------------- #
def _ref_name(target: str) -> str | None:
    candidate = re.sub(r"^\[?aria-?ref=", "", target.strip()).rstrip("]")
    return candidate if re.fullmatch(r"e\d+", candidate) else None


async def _locator(page: Page, target: str) -> Locator:
    ref = _ref_name(target)
    if ref is not None:
        locator = page.locator(f'[{_REF_ATTR}="{ref}"]')
        if await locator.count() == 0:
            raise LookupError(
                f"ref {ref} is no longer on the page; call browser_snapshot for fresh refs"
            )
        return locator.first

    try:
        locator = page.locator(target)
        if await locator.count() > 0:
            return locator.first
    except Exception:  # noqa: BLE001 - not a valid selector, fall through to text
        pass

    locator = page.get_by_text(target, exact=False)
    if await locator.count() == 0:
        raise LookupError(f"nothing on the page matches {target!r}")
    return locator.first


# --------------------------------------------------------------------------- #
# tools
# --------------------------------------------------------------------------- #
def register_browser_tools(mcp: FastMCP) -> None:
    """Attach the browser_* tools to an existing FastMCP instance."""

    @mcp.tool
    async def browser_navigate(url: str) -> str:
        """Open a URL in the automation browser.
        Args:
        url: Absolute http(s) URL to open.
        """

        async def action(page: Page) -> str:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
            status = f" (HTTP {response.status})" if response else ""
            return f"Navigated to {page.url}{status}."

        return await _act(action)

    @mcp.tool
    async def browser_snapshot(max_elements: int = 400) -> str:
        """Get the current page as an accessibility tree with clickable refs.
        Args:
        max_elements: Maximum number of elements to include.
        """

        async def action(page: Page) -> str:
            return await _snapshot(page, max_elements)

        return await _act(action, include_snapshot=False)

    @mcp.tool
    async def browser_click(target: str, button: Literal["left", "middle", "right"] = "left", click_count: int = 1) -> str:
        """Click an element on the page.
        Args:
        target: Element ref from browser_snapshot (e.g. "e12"), a CSS/Playwright selector, or visible text.
        button: "left", "right" or "middle".
        click_count: Number of clicks (2 = double click).
        """

        async def action(page: Page) -> str:
            locator = await _locator(page, target)
            await locator.click(button=button, click_count=click_count, timeout=_TIMEOUT_MS)
            return f"Clicked {target}."

        return await _act(action)

    @mcp.tool
    async def browser_type(
        target: str,
        text: str,
        submit: bool = False,
        slowly: bool = False,
    ) -> str:
        """Type text into an input, textarea or contenteditable element.
        Args:
        target: Element ref from browser_snapshot, a selector, or visible text.
        text: The text to type.
        submit: Press Enter afterwards.
        slowly: Type key by key instead of filling in one go.
        """

        async def action(page: Page) -> str:
            locator = await _locator(page, target)
            if slowly:
                await locator.click(timeout=_TIMEOUT_MS)
                await locator.press_sequentially(text, delay=50)
            else:
                await locator.fill(text, timeout=_TIMEOUT_MS)
            if submit:
                await locator.press("Enter")
            return f"Typed into {target}."

        return await _act(action)

    @mcp.tool
    async def browser_fill_form(fields: dict[str, str]) -> str:
        """Fill several fields at once.
        Args:
        fields: Mapping of target (ref, selector or label text) to value. Use "true"/"false" for checkboxes and radios, and a visible option label for selects.
        """

        async def action(page: Page) -> str:
            done = []
            for target, value in fields.items():
                locator = await _locator(page, target)
                kind = await locator.evaluate(
                    "el => (el.type || el.tagName).toLowerCase()"
                )
                if kind in {"checkbox", "radio"}:
                    if value.strip().lower() in {"true", "1", "yes", "on", "checked"}:
                        await locator.check(timeout=_TIMEOUT_MS)
                    else:
                        await locator.uncheck(timeout=_TIMEOUT_MS)
                elif kind in {"select", "select-one", "select-multiple"}:
                    await locator.select_option(label=value, timeout=_TIMEOUT_MS)
                else:
                    await locator.fill(value, timeout=_TIMEOUT_MS)
                done.append(target)
            return "Filled: " + ", ".join(done) + "."

        return await _act(action)

    @mcp.tool
    async def browser_select_option(target: str, values: list[str]) -> str:
        """Select one or more options in a <select> element.
        Args:
        target: Element ref from browser_snapshot, a selector, or visible text.
        values: Option labels or values to select.
        """

        async def action(page: Page) -> str:
            locator = await _locator(page, target)
            await locator.select_option(values, timeout=_TIMEOUT_MS)
            return f"Selected {values} in {target}."

        return await _act(action)

    @mcp.tool
    async def browser_hover(target: str) -> str:
        """Hover the mouse over an element.
        Args:
        target: Element ref from browser_snapshot, a selector, or visible text.
        """

        async def action(page: Page) -> str:
            locator = await _locator(page, target)
            await locator.hover(timeout=_TIMEOUT_MS)
            return f"Hovered {target}."

        return await _act(action)

    @mcp.tool
    async def browser_drag(source: str, target: str) -> str:
        """Drag one element onto another (drag and drop).
        Args:
        source: Element ref or selector to drag.
        target: Element ref or selector to drop on.
        """

        async def action(page: Page) -> str:
            origin = await _locator(page, source)
            destination = await _locator(page, target)
            await origin.drag_to(destination, timeout=_TIMEOUT_MS)
            return f"Dragged {source} onto {target}."

        return await _act(action)

    @mcp.tool
    async def browser_press_key(key: str) -> str:
        """Press a keyboard key on the focused element.
        Args:
        key: Playwright key name, e.g. "Enter", "Tab", "Escape", "ArrowDown", "Control+a".
        """

        async def action(page: Page) -> str:
            await page.keyboard.press(key)
            return f"Pressed {key}."

        return await _act(action)

    @mcp.tool
    async def browser_evaluate(function: str) -> str:
        """Run JavaScript in the page and return the result.
        Args:
        function: JS expression or arrow function, e.g. "document.title" or "() => document.querySelectorAll('a').length".
        """

        async def action(page: Page) -> str:
            result = await page.evaluate(function)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, indent=2, default=str)

        return await _act(action, include_snapshot=False)

    @mcp.tool
    async def browser_wait_for(
        time: float | None = None,
        text: str | None = None,
        text_gone: str | None = None,
    ) -> str:
        """Wait for a duration or for text to appear/disappear.
        Args:
        time: Seconds to wait.
        text: Visible text that should appear.
        text_gone: Visible text that should disappear.
        """

        async def action(page: Page) -> str:
            if time is not None:
                await asyncio.sleep(time)
                return f"Waited {time}s."
            if text is not None:
                await page.get_by_text(text, exact=False).first.wait_for(
                    state="visible", timeout=_NAV_TIMEOUT_MS
                )
                return f"Text {text!r} appeared."
            if text_gone is not None:
                await page.get_by_text(text_gone, exact=False).first.wait_for(
                    state="hidden", timeout=_NAV_TIMEOUT_MS
                )
                return f"Text {text_gone!r} disappeared."
            return "Nothing to wait for: pass time, text or text_gone."

        return await _act(action, include_snapshot=False)

    @mcp.tool
    async def browser_take_screenshot(filename: str | None = None, full_page: bool = False) -> str:
        """Save a PNG screenshot of the page and return its path.
        Args:
        filename: Optional file name; defaults to a timestamped file.
        full_page: Capture the whole scrollable page instead of the viewport.
        """

        async def action(page: Page) -> str:
            _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            name = filename or f"screenshot-{datetime.now():%Y%m%d-%H%M%S}.png"
            path = Path(name)
            if not path.is_absolute():
                path = _SCREENSHOT_DIR / path
            path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(path), full_page=full_page)
            return f"Screenshot saved to {path}"

        return await _act(action, include_snapshot=False)

    @mcp.tool
    async def browser_pdf_save(filename: str | None = None) -> str:
        """Save the page as a PDF (headless Chromium only) and return its path.
        Args:
        filename: Optional file name; defaults to a timestamped file.
        """

        async def action(page: Page) -> str:
            _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            name = filename or f"page-{datetime.now():%Y%m%d-%H%M%S}.pdf"
            path = Path(name)
            if not path.is_absolute():
                path = _SCREENSHOT_DIR / path
            path.parent.mkdir(parents=True, exist_ok=True)
            await page.pdf(path=str(path))
            return f"PDF saved to {path}"

        return await _act(action, include_snapshot=False)

    @mcp.tool
    async def browser_navigate_back() -> str:
        """Go back in the browser history."""

        async def action(page: Page) -> str:
            await page.go_back(wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
            return f"Went back to {page.url}."

        return await _act(action)

    @mcp.tool
    async def browser_navigate_forward() -> str:
        """Go forward in the browser history."""

        async def action(page: Page) -> str:
            await page.go_forward(wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
            return f"Went forward to {page.url}."

        return await _act(action)

    @mcp.tool
    async def browser_tab_list() -> str:
        """List the open browser tabs with their index, title and URL."""

        async def action(page: Page) -> str:
            tabs = []
            for index, tab in enumerate(page.context.pages):
                try:
                    title = await tab.title()
                except Exception:  # noqa: BLE001 - tab may be closing
                    title = ""
                tabs.append(
                    {"index": index, "url": tab.url, "title": title, "current": tab is page}
                )
            return encode(tabs)

        return await _act(action, include_snapshot=False)

    @mcp.tool
    async def browser_tab_new(url: str | None = None) -> str:
        """Open a new tab and switch to it.
        Args:
        url: Optional URL to load in the new tab.
        """

        async def action(page: Page) -> str:
            global _PAGE
            tab = await page.context.new_page()
            _adopt(tab)
            _PAGE = tab
            if url:
                await tab.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
            return f"Opened tab {tab.url}."

        return await _act(action)

    @mcp.tool
    async def browser_tab_select(index: int) -> str:
        """Switch to the tab at the given index (see browser_tab_list).
        Args:
        index: Zero-based tab index.
        """

        async def action(page: Page) -> str:
            global _PAGE
            pages = page.context.pages
            if not 0 <= index < len(pages):
                raise IndexError(f"no tab at index {index}; {len(pages)} tab(s) open")
            _PAGE = pages[index]
            await _PAGE.bring_to_front()
            return f"Switched to tab {index}: {_PAGE.url}"

        return await _act(action)

    @mcp.tool
    async def browser_tab_close(index: int | None = None) -> str:
        """Close a tab (the current one if index is omitted).
        Args:
        index: Zero-based tab index, defaults to the active tab.
        """

        async def action(page: Page) -> str:
            global _PAGE
            pages = page.context.pages
            if index is None:
                closing = page
            elif 0 <= index < len(pages):
                closing = pages[index]
            else:
                raise IndexError(f"no tab at index {index}; {len(pages)} tab(s) open")
            url = closing.url
            await closing.close()
            remaining = [p for p in pages if p is not closing and not p.is_closed()]
            _PAGE = remaining[-1] if remaining else None
            return f"Closed tab {url}."

        return await _act(action, include_snapshot=False)

    @mcp.tool
    async def browser_handle_dialog(accept: bool = True, prompt_text: str | None = None) -> str:
        """Accept or dismiss a currently open alert/confirm/prompt dialog.
        Args:
        accept: True to accept, False to dismiss.
        prompt_text: Text to enter when the dialog is a prompt.
        """
        global _DIALOG
        async with _LOCK:
            if _DIALOG is None:
                return "No dialog is open."
            dialog = _DIALOG
            _DIALOG = None
            if accept:
                await dialog.accept(prompt_text)
            else:
                await dialog.dismiss()
            verb = "accepted" if accept else "dismissed"
            return f"{dialog.type} dialog {verb}: {dialog.message!r}"

    @mcp.tool
    async def browser_close() -> str:
        """Close the browser and free the profile (it reopens on next use)."""
        global _PW, _CTX, _PAGE, _DIALOG
        async with _LOCK:
            _DIALOG = None
            try:
                if _CTX is not None:
                    await _CTX.close()
            finally:
                if _PW is not None:
                    await _PW.stop()
                _PW = None
                _CTX = None
                _PAGE = None
        return "Browser closed."
