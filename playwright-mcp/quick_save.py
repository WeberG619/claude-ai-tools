import asyncio
from playwright.async_api import async_playwright

async def go():
    pw = await async_playwright().start()
    b = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = b.contexts[0]
    page = ctx.pages[0]
    js = """() => {
        const overlays = document.querySelectorAll('.cdk-overlay-pane');
        for (const ov of overlays) {
            const btns = ov.querySelectorAll('button');
            for (const btn of btns) {
                if (btn.textContent.includes('Save')) {
                    btn.click();
                    return 'saved';
                }
            }
        }
        return 'no save found';
    }"""
    r = await page.evaluate(js)
    print(r)
    await asyncio.sleep(2)
    # Close extra tabs
    for p in list(ctx.pages):
        if any(k in p.url for k in ["approval", "developers.google.com", "newtab", "new-tab"]):
            await p.close()
            print(f"closed {p.url[:40]}")
    print(f"tabs: {len(ctx.pages)}")
    await pw.stop()

asyncio.run(go())
