#!/usr/bin/env python3
"""
Upwork browser scraper - runs on WINDOWS Python via PowerShell.
Connects to the EXISTING Chrome CDP session (logged into Upwork).

Usage from WSL:
    powershell.exe -NoProfile -Command "cd 'D:\\_CLAUDE-TOOLS\\opportunityengine\\scouts'; python upwork_browser.py 'Revit API'"

Returns JSON array of opportunities to stdout.
"""

import asyncio
import json
import re
import sys
from urllib.parse import quote_plus

# CDP ports to try - 9222 first (has logged-in Upwork session)
# Multiple Playwright clients can share a CDP port safely (each opens its own tabs)
CDP_PORTS = [9222, 9224, 9225, 9223, 9229]
CDP_TIMEOUT = 8000


async def connect_cdp():
    """Connect to an existing Chrome CDP session."""
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()

    # Try both localhost (resolves IPv6) and 127.0.0.1 (IPv4 only)
    for port in CDP_PORTS:
        for host in ["localhost", "127.0.0.1", "[::1]"]:
            try:
                browser = await pw.chromium.connect_over_cdp(
                    f"http://{host}:{port}", timeout=CDP_TIMEOUT
                )
                print(f"Connected to CDP on {host}:{port}", file=sys.stderr)
                return pw, browser, port
            except Exception:
                continue

    await pw.stop()
    raise RuntimeError(f"No Chrome CDP found on ports {CDP_PORTS}")


async def scrape_upwork(search_term: str) -> list:
    """Scrape Upwork search results for a given term."""
    pw, browser, port = await connect_cdp()
    results = []

    try:
        # Open a new tab in the existing browser context (preserves login)
        contexts = browser.contexts
        ctx = contexts[0] if contexts else await browser.new_context()
        page = await ctx.new_page()

        url = f"https://www.upwork.com/nx/search/jobs/?q={quote_plus(search_term)}&sort=recency"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for Cloudflare and content to load
        await page.wait_for_timeout(5000)

        # Check if Cloudflare is still blocking
        content = await page.content()
        if "Verifying" in content and "cloudflare" in content.lower():
            await page.wait_for_timeout(8000)  # Wait longer for Cloudflare

        # Check if we need to log in
        current_url = page.url
        if "login" in current_url.lower() or "signup" in current_url.lower():
            results.append({"error": "login_required", "url": current_url})
            await page.close()
            await pw.stop()
            return results

        # Wait for job tiles to appear
        try:
            await page.wait_for_selector(
                'article, section.up-card-section, [data-test="job-tile-list"]',
                timeout=10000
            )
        except Exception:
            pass  # May not find exact selector, continue with what we have

        # Extract using JavaScript for reliability
        jobs = await page.evaluate("""
        () => {
            const results = [];

            // Find all job tile sections - Upwork uses various container patterns
            const sections = document.querySelectorAll(
                'article, [data-test="JobTile"], section.up-card-section'
            );

            // If no sections found, try finding by heading pattern
            const allSections = sections.length > 0 ? sections :
                document.querySelectorAll('[class*="job-tile"], [class*="JobTile"]');

            for (const section of allSections) {
                const job = {};

                // Title - look for main heading link
                const titleLink = section.querySelector(
                    'a[class*="job-title"], h2 a, h3 a, [data-test="job-title-link"] a, a[href*="/jobs/"]'
                );
                if (titleLink) {
                    job.title = titleLink.textContent.trim();
                    job.url = titleLink.href;
                } else {
                    const heading = section.querySelector('h2, h3');
                    if (heading) job.title = heading.textContent.trim();
                }

                if (!job.title) continue;

                // Description
                const descEl = section.querySelector(
                    '[class*="line-clamp"], [data-test*="description"], p'
                );
                if (descEl) job.description = descEl.textContent.trim().slice(0, 2000);

                // Skills/tags - deduplicate
                const skillSet = new Set();
                const skillEls = section.querySelectorAll(
                    '[class*="token"], [class*="skill-badge"], [class*="air3-token"]'
                );
                for (const s of skillEls) {
                    // Get direct text only (avoid nested duplicates)
                    let text = '';
                    for (const node of s.childNodes) {
                        if (node.nodeType === 3) text += node.textContent;
                    }
                    text = text.trim() || s.textContent.trim();
                    if (text && text.length < 50 && text.length > 1) skillSet.add(text);
                }
                job.skills = [...skillSet];

                // Budget - look for dollar amounts
                const fullText = section.textContent;
                const budgetMatch = fullText.match(/\\$(\\d[\\d,]*(?:\\.\\d{2})?)\\s*(?:-\\s*\\$(\\d[\\d,]*(?:\\.\\d{2})?))?/);
                if (budgetMatch) {
                    job.budget_min = parseFloat(budgetMatch[1].replace(/,/g, ''));
                    job.budget_max = budgetMatch[2] ? parseFloat(budgetMatch[2].replace(/,/g, '')) : job.budget_min;
                }

                // Proposals count
                const proposalMatch = fullText.match(/(\\d+)\\s*(?:to\\s*(\\d+)\\s*)?[Pp]roposals?/);
                if (proposalMatch) {
                    job.proposals_count = parseInt(proposalMatch[2] || proposalMatch[1]);
                }

                // Client info
                const verifiedEl = section.querySelector('[class*="payment-verified"], [data-test*="payment"]');
                if (verifiedEl) job.payment_verified = true;

                const ratingEl = section.querySelector('[class*="rating"]');
                if (ratingEl) {
                    const rMatch = ratingEl.textContent.match(/(\\d\\.\\d)/);
                    if (rMatch) job.client_rating = parseFloat(rMatch[1]);
                }

                const spentEl = fullText.match(/(\\$[\\dKkMm.]+)\\s*spent/i);
                if (spentEl) job.client_spent = spentEl[1];

                // Location
                const locMatch = fullText.match(/📍\\s*([\\w\\s]+?)(?:\\s*\\n|$)/);
                if (!locMatch) {
                    const locEl = section.querySelector('[data-test*="location"], [class*="location"]');
                    if (locEl) job.location = locEl.textContent.trim();
                }

                // Posted time
                const timeMatch = fullText.match(/Posted\\s+(.+?)(?:\\n|$)/);
                if (timeMatch) job.posted = timeMatch[1].trim();

                // Applied status
                if (fullText.includes('Applied')) job.already_applied = true;

                results.push(job);
            }

            return results;
        }
        """)

        results = jobs if jobs else []

        await page.close()

    except Exception as e:
        results.append({"error": str(e)})
    finally:
        try:
            await pw.stop()
        except:
            pass

    return results


async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: upwork_browser.py <search_term>"}))
        sys.exit(1)

    search_term = sys.argv[1]
    results = await scrape_upwork(search_term)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
