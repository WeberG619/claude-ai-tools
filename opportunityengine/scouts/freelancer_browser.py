#!/usr/bin/env python3
"""
Freelancer.com browser scraper - runs on WINDOWS Python via PowerShell.
Connects to the EXISTING Chrome CDP session (logged into Freelancer).

Usage from WSL:
    powershell.exe -NoProfile -Command "cd 'D:\\_CLAUDE-TOOLS\\opportunityengine\\scouts'; python freelancer_browser.py 'Revit API'"

Returns JSON array of opportunities to stdout.
"""

import asyncio
import json
import sys
from urllib.parse import quote_plus

CDP_PORTS = [9222, 9224, 9225, 9223, 9229]
CDP_TIMEOUT = 8000


async def connect_cdp():
    """Connect to an existing Chrome CDP session."""
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()

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


async def scrape_freelancer(search_term: str) -> list:
    """Scrape Freelancer.com search results for a given term."""
    pw, browser, port = await connect_cdp()
    results = []

    try:
        contexts = browser.contexts
        ctx = contexts[0] if contexts else await browser.new_context()
        page = await ctx.new_page()

        url = f"https://www.freelancer.com/jobs/?keywords={quote_plus(search_term)}&sort=latest"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Freelancer uses Angular - needs time to render
        await page.wait_for_timeout(5000)

        # Check for login redirect
        current_url = page.url
        if "login" in current_url.lower() or "signup" in current_url.lower():
            results.append({"error": "login_required", "url": current_url})
            await page.close()
            await pw.stop()
            return results

        # Extract jobs using JavaScript
        jobs = await page.evaluate("""
        () => {
            const results = [];
            const seen = new Set();

            // Find all project links - Freelancer uses /projects/ URLs
            const links = Array.from(document.querySelectorAll('a'))
                .filter(a => {
                    const h = a.href || '';
                    return h.includes('/projects/') &&
                           !h.includes('/proposals') &&
                           !h.includes('/payments') &&
                           !h.includes('/reviews') &&
                           a.textContent.trim().length > 10 &&
                           a.textContent.trim().length < 200;
                });

            for (const link of links) {
                const title = link.textContent.trim();
                if (seen.has(title) || title.length < 10) continue;
                seen.add(title);

                // Walk up the DOM to find the job card container
                let container = link;
                for (let i = 0; i < 8; i++) {
                    container = container.parentElement;
                    if (!container) break;
                    const rect = container.getBoundingClientRect();
                    if (rect.height > 80 && rect.height < 500 && rect.width > 400) break;
                }

                if (!container) continue;
                const cardText = container.innerText || '';

                const job = {
                    title: title,
                    url: link.href
                };

                // Description - get paragraph text that isn't the title
                const lines = cardText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                const descLines = lines.filter(l =>
                    l !== title &&
                    l.length > 30 &&
                    l.length < 500 &&
                    !l.match(/^[\\$₹€£\\d]/) &&
                    !l.match(/^\\d+\\s*bids?/i) &&
                    !l.match(/days? left/i)
                );
                job.description = descLines.slice(0, 2).join(' ').substring(0, 2000) || '';

                // Budget - look for currency patterns
                const budgetMatch = cardText.match(
                    /([\\$₹€£])\\s*([\\d,]+(?:\\.\\d+)?)\\s*(?:[-–]\\s*[\\$₹€£]?\\s*([\\d,]+(?:\\.\\d+)?))?/
                );
                if (budgetMatch) {
                    const currency = budgetMatch[1];
                    job.budget_min = parseFloat(budgetMatch[2].replace(/,/g, ''));
                    job.budget_max = budgetMatch[3] ?
                        parseFloat(budgetMatch[3].replace(/,/g, '')) : job.budget_min;
                    job.currency = currency === '$' ? 'USD' :
                                   currency === '€' ? 'EUR' :
                                   currency === '£' ? 'GBP' :
                                   currency === '₹' ? 'INR' : 'USD';
                }

                // Hourly vs fixed
                const lowerCard = cardText.toLowerCase();
                if (lowerCard.includes('/hr') || lowerCard.includes('per hour') || lowerCard.includes('hourly')) {
                    job.is_hourly = true;
                } else if (lowerCard.includes('fixed') || lowerCard.includes('budget')) {
                    job.is_hourly = false;
                }

                // Bids count
                const bidMatch = cardText.match(/(\\d+)\\s*(?:bids?|entries|proposals)/i);
                if (bidMatch) job.bids_count = parseInt(bidMatch[1]);

                // Time left or posted
                const timeMatch = cardText.match(/(\\d+\\s+(?:days?|hours?|minutes?)\\s+left)/i);
                if (timeMatch) job.time_left = timeMatch[1];
                const postedMatch = cardText.match(/(\\d+\\s+(?:days?|hours?|minutes?)\\s+ago)/i);
                if (postedMatch) job.posted = postedMatch[1];

                // Skills/tags
                const skillEls = container.querySelectorAll(
                    '[class*="tag" i], [class*="skill" i], [class*="Tag" i], [class*="Skill" i]'
                );
                const skillSet = new Set();
                for (const s of skillEls) {
                    const text = s.textContent.trim();
                    if (text && text.length > 1 && text.length < 40) skillSet.add(text);
                }
                job.skills = [...skillSet];

                // If no skills from elements, try to extract from specific links
                if (job.skills.length === 0) {
                    const skillLinks = container.querySelectorAll('a[href*="/jobs/"]');
                    for (const sl of skillLinks) {
                        const t = sl.textContent.trim();
                        if (t && t.length > 1 && t.length < 40 && t !== title) {
                            skillSet.add(t);
                        }
                    }
                    job.skills = [...skillSet];
                }

                // Verified/sealed status
                if (lowerCard.includes('verified') || lowerCard.includes('payment verified')) {
                    job.payment_verified = true;
                }
                if (lowerCard.includes('sealed')) {
                    job.sealed = true;
                }

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
        print(json.dumps({"error": "Usage: freelancer_browser.py <search_term>"}))
        sys.exit(1)

    search_term = sys.argv[1]
    results = await scrape_freelancer(search_term)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
