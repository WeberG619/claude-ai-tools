"""Check top 2 jobs in detail and see if we can apply."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Get full URLs from search page
urls = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/jobs/"]');
    const results = {};
    for (const link of links) {
        const text = link.textContent.trim();
        if (text.includes('Playwright')) results.playwright = link.href.split('?')[0];
        if (text.includes('Junior Automation')) results.automation = link.href.split('?')[0];
        if (text.includes('Base44') || text.includes('RAG')) results.rag = link.href.split('?')[0];
        if (text.includes('Autocad') && text.includes('ELV')) results.autocad = link.href.split('?')[0];
        if (text.includes('Voice AI')) results.voice = link.href.split('?')[0];
    }
    return results;
})()""")
print(f"Found URLs: {urls}")

# Check each job
for name, url in urls.items():
    print(f"\n{'='*60}")
    print(f"JOB: {name}")
    print(f"URL: {url}")

    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(4)
    for i in range(20):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            else:
                break
        except:
            time.sleep(2)
    time.sleep(3)

    if "Just a moment" in page.title():
        print("  Cloudflare blocked")
        continue

    print(f"  Title: {page.title()[:70]}")

    details = page.evaluate("""(() => {
        const body = document.body.innerText;
        const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

        // Get the full description
        let descLines = [];
        let capturing = false;
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].length > 100 && !capturing) {
                capturing = true;
            }
            if (capturing) {
                descLines.push(lines[i]);
                if (descLines.join(' ').length > 1500 || lines[i] === 'Skills and Expertise') {
                    break;
                }
            }
        }

        // Key info
        const info = {};
        for (const line of lines) {
            if (line.includes('Est. budget')) info.budget = line;
            if (line.match(/^Hourly/)) info.hourly = line;
            if (line.includes('Fixed price')) info.type = 'Fixed';
            if (line.includes('Proposals:')) info.proposals = line;
            if (line.match(/Send a proposal for:/)) info.connectsCost = line;
            if (line.includes('Available Connects')) info.connectsAvail = line;
            if (line.includes('already submitted')) info.alreadyApplied = true;
        }

        // Apply button
        const btn = document.querySelector('#submit-proposal-button');
        info.canApply = btn ? !btn.disabled : false;
        info.btnFound = !!btn;

        return {desc: descLines.join('\\n').substring(0, 1500), info};
    })()""")

    print(f"\n  Can Apply: {details['info'].get('canApply', 'N/A')}")
    print(f"  Already Applied: {details['info'].get('alreadyApplied', False)}")
    for k, v in details['info'].items():
        if k not in ('canApply', 'btnFound', 'alreadyApplied'):
            print(f"  {k}: {v}")
    print(f"\n  Description:")
    print(f"  {details['desc'][:1000]}")

pw.stop()
