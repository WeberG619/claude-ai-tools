"""Download a floor plan image using Playwright connected to Chrome via CDP."""
import asyncio
import os
import sys

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # Connect to existing Chrome via CDP
        print("Connecting to Chrome via CDP...")
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        print(f"Connected! {len(browser.contexts)} contexts")

        # Create a new context and page
        context = await browser.new_context()
        page = await context.new_page()

        # Search Google Images for floor plans
        print("Searching Google Images for floor plans with dimensions...")
        await page.goto(
            "https://www.google.com/search?q=simple+house+floor+plan+with+dimensions+architectural+drawing&tbm=isch",
            wait_until="networkidle",
            timeout=15000,
        )

        # Wait for images to load
        await page.wait_for_timeout(2000)

        # Click on a good floor plan result (skip tiny thumbnails, find real results)
        # Google Images wraps results in <a> tags with data-lpage attribute containing the source URL
        image_links = await page.evaluate("""
            () => {
                const results = [];
                // Google Images result items
                const items = document.querySelectorAll('[data-lpage]');
                for (const item of items) {
                    const img = item.querySelector('img');
                    if (img && img.naturalWidth > 50) {
                        results.push({
                            url: item.getAttribute('data-lpage'),
                            alt: (img.alt || '').substring(0, 100),
                            w: img.naturalWidth,
                            h: img.naturalHeight,
                        });
                    }
                }
                return results.slice(0, 10);
            }
        """)

        print(f"Found {len(image_links)} image results:")
        for i, item in enumerate(image_links):
            print(f"  [{i}] {item['alt'][:60]}")
            print(f"       {item['url'][:100]}")

        if not image_links:
            # Fallback - try a different selector
            print("Trying alternate selectors...")
            image_links = await page.evaluate("""
                () => {
                    const results = [];
                    const imgs = document.querySelectorAll('img[data-src]');
                    for (const img of imgs) {
                        if (img.naturalWidth > 100) {
                            results.push({
                                url: img.getAttribute('data-src') || img.src,
                                alt: (img.alt || '').substring(0, 100),
                                w: img.naturalWidth,
                                h: img.naturalHeight,
                            });
                        }
                    }
                    return results.slice(0, 10);
                }
            """)
            print(f"Alternate: found {len(image_links)} images")

        # Pick the first floor plan image
        target = None
        for item in image_links:
            alt = item.get("alt", "").lower()
            if any(kw in alt for kw in ["floor", "plan", "house", "room", "bedroom"]):
                target = item
                break

        if not target and image_links:
            target = image_links[0]

        if target:
            print(f"\nSelected: {target['alt']}")
            img_url = target["url"]

            # Navigate to the source page and find the full image
            print(f"Navigating to source: {img_url[:100]}")
            try:
                await page.goto(img_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Navigation warning: {e}")

            # Try to find and download the main image on the page
            # Use page screenshot as fallback
            page_images = await page.evaluate("""
                () => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs
                        .filter(i => i.naturalWidth > 300 && i.naturalHeight > 300)
                        .map(i => ({src: i.src, w: i.naturalWidth, h: i.naturalHeight}))
                        .sort((a, b) => (b.w * b.h) - (a.w * a.h))
                        .slice(0, 3);
                }
            """)

            if page_images:
                best = page_images[0]
                print(f"Found large image: {best['w']}x{best['h']}")
                print(f"Downloading: {best['src'][:100]}")

                # Download via fetch in browser context
                img_data = await page.evaluate("""
                    async (src) => {
                        try {
                            const resp = await fetch(src);
                            const blob = await resp.blob();
                            return new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            });
                        } catch(e) {
                            return "ERROR:" + e.message;
                        }
                    }
                """, best["src"])

                if img_data and img_data.startswith("data:"):
                    import base64
                    header, b64 = img_data.split(",", 1)
                    raw = base64.b64decode(b64)
                    ext = "jpg"
                    if "png" in header:
                        ext = "png"
                    elif "webp" in header:
                        ext = "webp"
                    save_path = os.path.join(SAVE_DIR, f"downloaded_floorplan.{ext}")
                    with open(save_path, "wb") as f:
                        f.write(raw)
                    print(f"Image saved: {save_path} ({len(raw):,} bytes)")
                else:
                    print(f"Fetch failed: {str(img_data)[:200]}")
                    # Fallback to screenshot
                    save_path = os.path.join(SAVE_DIR, "downloaded_floorplan.png")
                    await page.screenshot(path=save_path, full_page=True)
                    print(f"Screenshot saved instead: {save_path}")
            else:
                # No large images found, screenshot the page
                save_path = os.path.join(SAVE_DIR, "downloaded_floorplan.png")
                await page.screenshot(path=save_path, full_page=True)
                print(f"No large images. Screenshot saved: {save_path}")
        else:
            print("No floor plan images found!")
            # Screenshot the search results at least
            save_path = os.path.join(SAVE_DIR, "google_results.png")
            await page.screenshot(path=save_path, full_page=False)
            print(f"Search results screenshot: {save_path}")

        await context.close()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
