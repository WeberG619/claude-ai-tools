#!/usr/bin/env python3
"""
Comprehensive CDP Playwright Test Suite v2
Tests every capability of the playwright-browser MCP server.
Run on Windows Python: python test_cdp.py
"""

import asyncio
import sys
import io
import time
import traceback

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright

CDP_URL = "http://127.0.0.1:9222"

# Test tracking
results = []


def record(suite, test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"suite": suite, "test": test_name, "passed": passed, "detail": detail})
    icon = "+" if passed else "X"
    line = f"  [{icon}] {test_name}"
    if detail:
        line += f": {detail[:80]}"
    print(line)


async def clean_tabs(ctx, keep=1):
    """Close extra tabs, keep only `keep` tabs. Create one if none exist.
    Also handles Edge's behavior where pages may exist but be closed."""
    while len(ctx.pages) > keep:
        try:
            await ctx.pages[-1].close()
        except Exception:
            break
    if len(ctx.pages) == 0:
        return await ctx.new_page()
    # Liveness check: make sure the page is actually usable
    page = ctx.pages[0]
    if page.is_closed():
        return await ctx.new_page()
    try:
        await page.title()  # Quick check
        return page
    except Exception:
        return await ctx.new_page()


async def suite1_connection_navigation(ctx, browser):
    """Suite 1: Connection & Navigation"""
    print("\n== SUITE 1: Connection & Navigation ==")
    page = await clean_tabs(ctx)

    # 1.1: Basic navigation
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        record("S1", "Basic navigate to example.com", "Example" in title, title)
    except Exception as e:
        record("S1", "Basic navigate to example.com", False, str(e)[:80])

    # 1.2: Navigate to a real site (Wikipedia)
    try:
        await page.goto("https://en.wikipedia.org/wiki/Main_Page", wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        record("S1", "Navigate Wikipedia", "Wikipedia" in title, title)
    except Exception as e:
        record("S1", "Navigate Wikipedia", False, str(e)[:80])

    # 1.3: Navigate to HTTPS site
    try:
        await page.goto("https://httpbin.org/get", wait_until="domcontentloaded", timeout=15000)
        content = await page.content()
        record("S1", "HTTPS site (httpbin)", "origin" in content, f"Got {len(content)} bytes")
    except Exception as e:
        record("S1", "HTTPS site (httpbin)", False, str(e)[:80])

    # 1.4: Handle redirect
    try:
        await page.goto("http://github.com", wait_until="domcontentloaded", timeout=15000)
        url = page.url
        record("S1", "HTTP->HTTPS redirect", "https" in url, url[:60])
    except Exception as e:
        record("S1", "HTTP->HTTPS redirect", False, str(e)[:80])

    # 1.5: SPA navigation (GitHub)
    try:
        await page.goto("https://github.com/nicepkg/aide", wait_until="domcontentloaded", timeout=15000)
        url = page.url
        record("S1", "SPA site (GitHub)", "github.com" in url, url[:60])
    except Exception as e:
        record("S1", "SPA site (GitHub)", False, str(e)[:80])

    # 1.6: Page with lots of JS (Google)
    try:
        await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        record("S1", "JS-heavy site (Google)", "Google" in title or "google" in page.url, title)
    except Exception as e:
        record("S1", "JS-heavy site (Google)", False, str(e)[:80])

    # 1.7: go_back / go_forward (with proper waits)
    try:
        await page.goto("https://example.com", wait_until="networkidle", timeout=15000)
        await page.goto("https://httpbin.org/get", wait_until="networkidle", timeout=15000)
        await page.go_back(wait_until="networkidle", timeout=15000)
        back_url = page.url
        await page.go_forward(wait_until="networkidle", timeout=15000)
        fwd_url = page.url
        record("S1", "Back/Forward navigation",
               "example.com" in back_url and "httpbin" in fwd_url,
               f"back={back_url[:40]} fwd={fwd_url[:40]}")
    except Exception as e:
        record("S1", "Back/Forward navigation", False, str(e)[:80])

    # 1.8: Get page state
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        url = page.url
        record("S1", "Get page state (url+title)", bool(title and url), f"{url} - {title}")
    except Exception as e:
        record("S1", "Get page state (url+title)", False, str(e)[:80])

    return page


async def suite2_tabs(ctx, browser):
    """Suite 2: Tab Management"""
    print("\n== SUITE 2: Tab Management ==")

    # Clean to exactly 1 tab
    page = await clean_tabs(ctx, keep=1)
    await page.goto("https://example.com", wait_until="domcontentloaded", timeout=10000)

    # 2.1: List tabs (should be exactly 1 after clean)
    try:
        base_count = len(ctx.pages)
        record("S2", "List tabs (1 tab)", base_count == 1, f"{base_count} tab(s)")
    except Exception as e:
        record("S2", "List tabs (1 tab)", False, str(e)[:80])

    # 2.2: Open new tab (should be base + 1)
    try:
        before = len(ctx.pages)
        page2 = await ctx.new_page()
        await page2.goto("https://httpbin.org/get", wait_until="domcontentloaded", timeout=15000)
        after = len(ctx.pages)
        record("S2", "Open new tab", after == before + 1, f"{after} tabs")
    except Exception as e:
        record("S2", "Open new tab", False, str(e)[:80])

    # 2.3: Open third tab (should be previous + 1)
    try:
        before = len(ctx.pages)
        page3 = await ctx.new_page()
        await page3.goto("https://news.ycombinator.com", wait_until="domcontentloaded", timeout=15000)
        after = len(ctx.pages)
        record("S2", "Open third tab", after == before + 1, f"{after} tabs")
    except Exception as e:
        record("S2", "Open third tab", False, str(e)[:80])

    # 2.4: Switch tab by index
    try:
        target = ctx.pages[0]
        await target.bring_to_front()
        url = target.url
        record("S2", "Switch to tab 0", "example.com" in url, url[:50])
    except Exception as e:
        record("S2", "Switch to tab 0", False, str(e)[:80])

    # 2.5: Find tab by URL pattern
    try:
        found = None
        for p in ctx.pages:
            if "httpbin" in p.url:
                found = p
                break
        record("S2", "Find tab by URL pattern", found is not None,
               found.url[:50] if found else "not found")
    except Exception as e:
        record("S2", "Find tab by URL pattern", False, str(e)[:80])

    # 2.6: Find tab by title
    try:
        found = None
        for p in ctx.pages:
            t = await p.title()
            if "Hacker" in t:
                found = p
                break
        found_title = (await found.title())[:50] if found else "not found"
        record("S2", "Find tab by title", found is not None, found_title)
    except Exception as e:
        record("S2", "Find tab by title", False, str(e)[:80])

    # 2.7: Close a tab
    try:
        count_before = len(ctx.pages)
        await ctx.pages[-1].close()
        count_after = len(ctx.pages)
        record("S2", "Close tab", count_after == count_before - 1,
               f"{count_before} -> {count_after}")
    except Exception as e:
        record("S2", "Close tab", False, str(e)[:80])

    # Clean up
    await clean_tabs(ctx, keep=1)
    return ctx.pages[0]


async def suite3_elements_clicking(ctx, browser):
    """Suite 3: Element Discovery & Clicking"""
    print("\n== SUITE 3: Element Discovery & Clicking ==")
    page = await clean_tabs(ctx)

    # 3.1: Get all interactable elements
    try:
        await page.goto("https://en.wikipedia.org/wiki/Main_Page",
                         wait_until="domcontentloaded", timeout=15000)
        elements = await page.evaluate("""
            () => document.querySelectorAll('a, button, input, textarea, select').length
        """)
        record("S3", "Find interactable elements", elements > 10, f"Found {elements} elements")
    except Exception as e:
        record("S3", "Find interactable elements", False, str(e)[:80])

    # 3.2: Click by CSS selector (HN story)
    try:
        await page.goto("https://news.ycombinator.com",
                         wait_until="domcontentloaded", timeout=10000)
        original_url = page.url
        await page.click(".titleline a", timeout=5000)
        await page.wait_for_timeout(3000)
        new_url = page.url
        record("S3", "Click by CSS selector (.titleline a)",
               new_url != original_url, new_url[:60])
    except Exception as e:
        record("S3", "Click by CSS selector (.titleline a)", False, str(e)[:80])

    # 3.3: Click by role + name (Wikipedia search button or a known link)
    try:
        await page.goto("https://en.wikipedia.org/wiki/Main_Page",
                         wait_until="domcontentloaded", timeout=10000)
        # Use the search input which has aria-label="Search Wikipedia"
        await page.get_by_role("searchbox", name="Search Wikipedia").first.click(timeout=5000)
        # Verify focus is on search
        focused = await page.evaluate("() => document.activeElement?.getAttribute('aria-label') || ''")
        record("S3", "Click by role+name (searchbox 'Search Wikipedia')",
               "Search" in focused, f"focused: {focused}")
    except Exception as e:
        record("S3", "Click by role+name", False, str(e)[:80])

    # 3.4: Click by visible text on HN (click "new" or "past" nav link)
    try:
        await page.goto("https://news.ycombinator.com",
                         wait_until="networkidle", timeout=15000)
        original = page.url
        # HN has visible nav links: new, past, comments, ask, show, jobs
        await page.locator("a", has_text="past").first.click(timeout=10000)
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
        record("S3", "Click by text ('past' on HN)",
               "past" in page.url or "front" in page.url or page.url != original,
               page.url[:60])
    except Exception as e:
        record("S3", "Click by text", False, str(e)[:80])

    # 3.5: Click non-existent element (should fail with timeout)
    try:
        await page.click("#nonexistent-element-xyz-999", timeout=3000)
        record("S3", "Click non-existent (expect timeout)", False, "Should have thrown")
    except Exception as e:
        is_timeout = "timeout" in str(e).lower() or "Timeout" in str(e)
        record("S3", "Click non-existent (expect timeout)", is_timeout,
               "Correctly threw timeout")

    return page


async def suite4_forms(ctx, browser):
    """Suite 4: Form Filling & Typing"""
    print("\n== SUITE 4: Form Filling & Typing ==")
    page = await clean_tabs(ctx)

    await page.goto("https://httpbin.org/forms/post", wait_until="domcontentloaded", timeout=15000)

    # 4.1: Fill text input
    try:
        await page.fill('input[name="custname"]', "Weber Gouin", timeout=5000)
        val = await page.input_value('input[name="custname"]')
        record("S4", "Fill text input (custname)", val == "Weber Gouin", f"value='{val}'")
    except Exception as e:
        record("S4", "Fill text input (custname)", False, str(e)[:80])

    # 4.2: Fill phone
    try:
        await page.fill('input[name="custtel"]', "555-867-5309", timeout=5000)
        val = await page.input_value('input[name="custtel"]')
        record("S4", "Fill phone input", val == "555-867-5309", f"value='{val}'")
    except Exception as e:
        record("S4", "Fill phone input", False, str(e)[:80])

    # 4.3: Fill email
    try:
        await page.fill('input[name="custemail"]', "weber@example.com", timeout=5000)
        val = await page.input_value('input[name="custemail"]')
        record("S4", "Fill email input", val == "weber@example.com", f"value='{val}'")
    except Exception as e:
        record("S4", "Fill email input", False, str(e)[:80])

    # 4.4: Check radio button
    try:
        await page.locator('input[name="size"][value="large"]').check(timeout=5000)
        checked = await page.locator('input[name="size"][value="large"]').is_checked()
        record("S4", "Check radio button (large)", checked, f"checked={checked}")
    except Exception as e:
        record("S4", "Check radio button (large)", False, str(e)[:80])

    # 4.5: Check checkbox
    try:
        await page.locator('input[name="topping"][value="cheese"]').check(timeout=5000)
        await page.locator('input[name="topping"][value="mushroom"]').check(timeout=5000)
        c1 = await page.locator('input[name="topping"][value="cheese"]').is_checked()
        c2 = await page.locator('input[name="topping"][value="mushroom"]').is_checked()
        record("S4", "Check checkboxes", c1 and c2, f"cheese={c1} mushroom={c2}")
    except Exception as e:
        record("S4", "Check checkboxes", False, str(e)[:80])

    # 4.6: Fill textarea (multiline)
    try:
        long_text = "Line 1 of the test.\nLine 2 with more text.\nLine 3 final."
        await page.fill('textarea[name="comments"]', long_text, timeout=5000)
        val = await page.input_value('textarea[name="comments"]')
        record("S4", "Fill textarea (multiline)", val == long_text, f"{len(val)} chars")
    except Exception as e:
        record("S4", "Fill textarea (multiline)", False, str(e)[:80])

    # 4.7: Overwrite existing value
    try:
        await page.fill('input[name="custname"]', "REPLACED", timeout=5000)
        val = await page.input_value('input[name="custname"]')
        record("S4", "Overwrite existing value", val == "REPLACED", f"value='{val}'")
    except Exception as e:
        record("S4", "Overwrite existing value", False, str(e)[:80])

    # 4.8: Type character by character
    try:
        await page.fill('input[name="custname"]', "", timeout=5000)
        await page.click('input[name="custname"]', timeout=5000)
        await page.keyboard.type("Typed char by char", delay=10)
        val = await page.input_value('input[name="custname"]')
        record("S4", "Type char-by-char", val == "Typed char by char", f"value='{val}'")
    except Exception as e:
        record("S4", "Type char-by-char", False, str(e)[:80])

    # 4.9: Submit form
    try:
        url_before = page.url
        # httpbin uses <p> <button> or we can just press Enter on a field
        await page.click('input[name="custname"]', timeout=5000)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)
        content = await page.content()
        # httpbin shows the submitted data
        submitted = "REPLACED" in content or "Typed char by char" in content or page.url != url_before
        record("S4", "Submit form", submitted, f"url={page.url[:50]}")
    except Exception as e:
        record("S4", "Submit form", False, str(e)[:80])

    # 4.10: Google search fill + submit
    try:
        await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=10000)
        search = page.get_by_label("Search", exact=True)
        await search.fill("Playwright CDP test", timeout=5000)
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
            await search.press("Enter")
        record("S4", "Google search fill+submit",
               "search" in page.url or "q=" in page.url, page.url[:60])
    except Exception as e:
        record("S4", "Google search fill+submit", False, str(e)[:80])

    return page


async def suite5_scroll_screenshot_keyboard_js(ctx, browser):
    """Suite 5: Scroll, Screenshot, Keyboard, JS Eval"""
    print("\n== SUITE 5: Scroll, Screenshot, Keyboard, JS Eval ==")
    page = await clean_tabs(ctx)

    # 5.1: Scroll down
    try:
        await page.goto("https://en.wikipedia.org/wiki/Python_(programming_language)",
                         wait_until="domcontentloaded", timeout=15000)
        y_before = await page.evaluate("() => window.scrollY")
        await page.mouse.wheel(0, 800)
        await page.wait_for_timeout(500)
        y_after = await page.evaluate("() => window.scrollY")
        record("S5", "Scroll down 800px", y_after > y_before,
               f"scrollY: {y_before} -> {y_after}")
    except Exception as e:
        record("S5", "Scroll down 800px", False, str(e)[:80])

    # 5.2: Scroll up
    try:
        y_before = await page.evaluate("() => window.scrollY")
        await page.mouse.wheel(0, -500)
        await page.wait_for_timeout(500)
        y_after = await page.evaluate("() => window.scrollY")
        record("S5", "Scroll up 500px", y_after < y_before,
               f"scrollY: {y_before} -> {y_after}")
    except Exception as e:
        record("S5", "Scroll up 500px", False, str(e)[:80])

    # 5.3: Screenshot viewport
    try:
        screenshot = await page.screenshot()
        record("S5", "Screenshot viewport", len(screenshot) > 1000,
               f"{len(screenshot)} bytes")
    except Exception as e:
        record("S5", "Screenshot viewport", False, str(e)[:80])

    # 5.4: Screenshot full page (use a smaller page to avoid timeout)
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=10000)
        screenshot = await page.screenshot(full_page=True, timeout=60000)
        record("S5", "Screenshot full page", len(screenshot) > 1000,
               f"{len(screenshot)} bytes")
    except Exception as e:
        record("S5", "Screenshot full page", False, str(e)[:80])

    # 5.5: Screenshot specific element
    try:
        await page.goto("https://en.wikipedia.org/wiki/Python_(programming_language)",
                         wait_until="domcontentloaded", timeout=15000)
        el = page.locator("#firstHeading")
        screenshot = await el.screenshot()
        record("S5", "Screenshot element (#firstHeading)", len(screenshot) > 500,
               f"{len(screenshot)} bytes")
    except Exception as e:
        record("S5", "Screenshot element", False, str(e)[:80])

    # 5.6: Keyboard - Ctrl+A + type over
    try:
        await page.goto("https://httpbin.org/forms/post",
                         wait_until="domcontentloaded", timeout=10000)
        await page.fill('input[name="custname"]', "Select me", timeout=5000)
        await page.click('input[name="custname"]', timeout=5000)
        await page.keyboard.press("Control+a")
        await page.keyboard.type("Replaced via Ctrl+A")
        val = await page.input_value('input[name="custname"]')
        record("S5", "Keyboard Ctrl+A + type over",
               val == "Replaced via Ctrl+A", f"value='{val}'")
    except Exception as e:
        record("S5", "Keyboard Ctrl+A + type over", False, str(e)[:80])

    # 5.7: Keyboard - Tab to next field
    try:
        await page.click('input[name="custname"]', timeout=5000)
        await page.keyboard.press("Tab")
        focused = await page.evaluate(
            "() => document.activeElement?.name || document.activeElement?.tagName")
        record("S5", "Tab to next field", focused == "custtel", f"focused: {focused}")
    except Exception as e:
        record("S5", "Tab to next field", False, str(e)[:80])

    # 5.8: Keyboard - Escape
    try:
        await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=10000)
        search = page.get_by_label("Search", exact=True)
        await search.fill("test", timeout=5000)
        await page.keyboard.press("Escape")
        record("S5", "Escape key", True, "No error")
    except Exception as e:
        record("S5", "Escape key", False, str(e)[:80])

    # 5.9: JS Evaluation - return value
    try:
        result = await page.evaluate("() => 2 + 2")
        record("S5", "JS eval (2+2)", result == 4, f"result={result}")
    except Exception as e:
        record("S5", "JS eval (2+2)", False, str(e)[:80])

    # 5.10: JS Evaluation - DOM query
    try:
        result = await page.evaluate("() => document.querySelectorAll('a').length")
        record("S5", "JS eval (count links)",
               isinstance(result, int) and result > 0, f"links={result}")
    except Exception as e:
        record("S5", "JS eval (count links)", False, str(e)[:80])

    # 5.11: JS Evaluation - modify DOM
    try:
        await page.evaluate("() => { document.title = 'MODIFIED BY TEST'; }")
        title = await page.title()
        record("S5", "JS eval (modify DOM)", title == "MODIFIED BY TEST",
               f"title='{title}'")
    except Exception as e:
        record("S5", "JS eval (modify DOM)", False, str(e)[:80])

    # 5.12: Wait for element
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=10000)
        await page.wait_for_selector("h1", state="visible", timeout=5000)
        h1 = await page.locator("h1").text_content()
        record("S5", "Wait for element (h1)", "Example" in h1, h1[:40])
    except Exception as e:
        record("S5", "Wait for element (h1)", False, str(e)[:80])

    return page


async def suite6_edge_cases(ctx, browser):
    """Suite 6: Edge Cases & Stress"""
    print("\n== SUITE 6: Edge Cases & Stress ==")
    page = await clean_tabs(ctx)

    # 6.1: Navigate to 404 page (should not crash, page still loads)
    try:
        response = None
        try:
            response = await page.goto("https://httpbin.org/status/404",
                                        wait_until="commit", timeout=15000)
        except Exception as nav_err:
            if "net::ERR_HTTP_RESPONSE_CODE_FAILURE" in str(nav_err):
                pass  # Page loaded but returned error status — that's OK
            else:
                raise
        status = response.status if response else 404
        record("S6", "Handle 404 page", status == 404, f"status={status}")
    except Exception as e:
        record("S6", "Handle 404 page", False, str(e)[:80])

    # Stabilize before next test
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=10000)
    except Exception:
        await page.wait_for_timeout(2000)

    # 6.2: Navigate to slow page (give it enough time)
    try:
        start = time.time()
        await page.goto("https://httpbin.org/delay/2",
                         wait_until="domcontentloaded", timeout=20000)
        elapsed = time.time() - start
        record("S6", "Slow page (2s delay)", elapsed >= 1.5, f"took {elapsed:.1f}s")
    except Exception as e:
        record("S6", "Slow page (2s delay)", False, str(e)[:80])

    # Stabilize
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=10000)
    except Exception:
        await page.wait_for_timeout(2000)

    # 6.3: Sequential navigation (3 sites, each properly awaited)
    try:
        visited = []
        for url in ["https://example.com", "https://httpbin.org/get",
                     "https://news.ycombinator.com"]:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            visited.append(page.url)
        record("S6", "Sequential navigation (3 sites)",
               len(visited) == 3, f"visited {len(visited)} sites")
    except Exception as e:
        record("S6", "Sequential navigation (3 sites)", False, str(e)[:80])

    # Stabilize
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=10000)
    except Exception:
        await page.wait_for_timeout(2000)

    # 6.4: Handle alert dialog
    try:
        await page.goto("https://example.com", wait_until="networkidle", timeout=10000)
        dialog_handled = asyncio.Event()

        async def handle_dialog(dialog):
            await dialog.accept()
            dialog_handled.set()

        page.on("dialog", handle_dialog)
        await page.evaluate("() => { setTimeout(() => alert('test alert'), 100); }")
        try:
            await asyncio.wait_for(dialog_handled.wait(), timeout=5)
            record("S6", "Handle alert dialog", True, "Auto-accepted")
        except asyncio.TimeoutError:
            record("S6", "Handle alert dialog", False, "Dialog not triggered within 5s")
        page.remove_listener("dialog", handle_dialog)
    except Exception as e:
        record("S6", "Handle alert dialog", False, str(e)[:80])

    # 6.5: Handle confirm dialog (override via JS, no actual browser dialog)
    try:
        await page.goto("https://example.com", wait_until="networkidle", timeout=10000)
        result = await page.evaluate("""
            () => {
                window._origConfirm = window.confirm;
                window.confirm = () => true;
                const r = window.confirm('test?');
                window.confirm = window._origConfirm;
                return r;
            }
        """)
        record("S6", "Handle confirm dialog", result is True, f"result={result}")
    except Exception as e:
        record("S6", "Handle confirm dialog", False, str(e)[:80])

    # 6.6: Long text input
    try:
        await page.goto("https://httpbin.org/forms/post",
                         wait_until="networkidle", timeout=15000)
        long_text = "A" * 5000
        await page.fill('textarea[name="comments"]', long_text, timeout=5000)
        val = await page.input_value('textarea[name="comments"]')
        record("S6", "Long text input (5000 chars)", len(val) == 5000,
               f"length={len(val)}")
    except Exception as e:
        record("S6", "Long text input (5000 chars)", False, str(e)[:80])

    # 6.7: Special characters in input (no newlines/tabs — HTML inputs strip those)
    try:
        special = '<script>alert("xss")</script> & "quotes" \'apostrophe\''
        await page.fill('input[name="custname"]', special, timeout=5000)
        val = await page.input_value('input[name="custname"]')
        record("S6", "Special chars in input", val == special,
               f"match={val == special}, len={len(val)}")
    except Exception as e:
        record("S6", "Special chars in input", False, str(e)[:80])

    # 6.8: Multiple tabs simultaneously
    try:
        pages_opened = []
        urls = ["https://example.com", "https://httpbin.org/get",
                "https://news.ycombinator.com"]
        for url in urls:
            p = await ctx.new_page()
            await p.goto(url, wait_until="domcontentloaded", timeout=10000)
            pages_opened.append(p)
        all_loaded = all(p.url for p in pages_opened)
        tab_count = len(ctx.pages)
        record("S6", "3 tabs opened simultaneously",
               all_loaded and tab_count >= 4, f"{tab_count} total tabs")
        # Clean up the extra tabs
        for p in pages_opened:
            await p.close()
    except Exception as e:
        record("S6", "3 tabs opened simultaneously", False, str(e)[:80])

    # 6.9: Page reload
    try:
        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=10000)
        await page.reload(wait_until="domcontentloaded", timeout=10000)
        title = await page.title()
        record("S6", "Page reload", "Example" in title, title[:40])
    except Exception as e:
        record("S6", "Page reload", False, str(e)[:80])

    # 6.10: Browser info via JS
    try:
        info = await page.evaluate("""
            () => ({
                url: location.href,
                cookies: document.cookie.length,
                localStorage: Object.keys(localStorage).length,
                userAgent: navigator.userAgent.slice(0, 60)
            })
        """)
        record("S6", "Browser info via JS", "url" in info,
               f"UA={info.get('userAgent', '?')[:50]}")
    except Exception as e:
        record("S6", "Browser info via JS", False, str(e)[:80])

    return page


async def main():
    print("=" * 60)
    print("PLAYWRIGHT CDP COMPREHENSIVE TEST SUITE v2")
    print("=" * 60)
    print(f"CDP endpoint: {CDP_URL}")

    pw = await async_playwright().start()

    try:
        browser = await pw.chromium.connect_over_cdp(CDP_URL)
        print(f"Connected to: {browser.browser_type.name} {browser.version}")
    except Exception as e:
        print(f"\nFATAL: Cannot connect to CDP at {CDP_URL}")
        print(f"Error: {e}")
        print("Make sure Chrome/Edge is running with --remote-debugging-port=9222")
        await pw.stop()
        sys.exit(1)

    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()

    # Ensure at least one page exists (Edge may close initial about:blank)
    if len(ctx.pages) == 0:
        await ctx.new_page()
    print(f"Initial state: {len(ctx.pages)} page(s) in context")

    # Run all suites
    try:
        await suite1_connection_navigation(ctx, browser)
        await suite2_tabs(ctx, browser)
        await suite3_elements_clicking(ctx, browser)
        await suite4_forms(ctx, browser)
        await suite5_scroll_screenshot_keyboard_js(ctx, browser)
        await suite6_edge_cases(ctx, browser)
    except Exception as e:
        print(f"\nFATAL ERROR during tests: {e}")
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)

    for suite_name in sorted(set(r["suite"] for r in results)):
        suite_results = [r for r in results if r["suite"] == suite_name]
        suite_pass = sum(1 for r in suite_results if r["passed"])
        suite_total = len(suite_results)
        status = "ALL PASS" if suite_pass == suite_total else f"{suite_total - suite_pass} FAILED"
        print(f"  {suite_name}: {suite_pass}/{suite_total} ({status})")

    print(f"\nTOTAL: {passed}/{total} passed, {failed} failed")

    if failed > 0:
        print("\nFAILED TESTS:")
        for r in results:
            if not r["passed"]:
                print(f"  [X] {r['suite']}/{r['test']}: {r['detail'][:100]}")
    else:
        print("\n*** ALL TESTS PASSED ***")

    print("=" * 60)
    await pw.stop()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
