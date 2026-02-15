"""Get details on the most promising fresh Upwork jobs."""
from playwright.sync_api import sync_playwright
import time
import json

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

JOBS = [
    {
        "name": "AutoCAD ELV Systems Layout",
        "url": "https://www.upwork.com/jobs/Autocad-Draftsman-for-ELV-Systems-Equipment-Layout_~022021798561068707841",
    },
    {
        "name": "Redraft plans in CAD",
        "url": "https://www.upwork.com/jobs/Redraft-plans-CAD_~022021820293586285264",
    },
    {
        "name": "Product Data Aggregation 50K",
        "url": "https://www.upwork.com/jobs/Product-Data-Aggregation-Expert-50K-Products-via-Official-APIs-Affiliate-Programs_~022021546461523050788",
    },
    {
        "name": "Part-Time Revit Modeller Retainer",
        "url": "https://www.upwork.com/jobs/Part-Time-Revit-Modeller-Retainer-Basis-Hoc-BIM-Modelling-Work_~022021597424006225920",
    },
]

results = []

for job in JOBS:
    print(f"\n{'='*60}")
    print(f"Checking: {job['name']}")

    page.evaluate(f"window.location.href = '{job['url']}'")
    time.sleep(3)

    for i in range(20):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            else:
                break
        except:
            time.sleep(2)
    time.sleep(2)

    title = page.title()
    if "Just a moment" in title:
        print("  Cloudflare blocked")
        continue

    # Get job details
    details = page.evaluate("""(() => {
        const body = document.body.innerText;
        const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

        // Find description (usually after title, before skills)
        let description = '';
        let inDesc = false;
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.includes('Posted') && lines[i+1] && lines[i+1].length > 50) {
                description = lines.slice(i+1, i+10).join(' ');
                break;
            }
        }

        // Find key info
        const info = {};
        for (const line of lines) {
            if (line.includes('Est. budget')) info.budget = line;
            if (line.includes('Fixed price') || line.includes('Hourly')) info.type = line;
            if (line.includes('Proposals:')) info.proposals = line;
            if (line.match(/^\\d+ to \\d+$/)) info.proposalCount = line;
            if (line.includes('Connects')) info.connects = line;
            if (line.includes('Payment verified')) info.paymentVerified = true;
            if (line.includes('Rating is')) info.rating = line;
            if (line.match(/^\\$\\d/)) info.amount = line;
            if (line.includes('Less than') || line.includes('1 to 3') || line.includes('3 to 6') || line.includes('More than')) {
                if (line.includes('month')) info.duration = line;
            }
            if (line.includes('Entry Level') || line.includes('Intermediate') || line.includes('Expert')) {
                if (line.length < 30) info.level = line;
            }
        }

        // Check apply button
        const btn = document.querySelector('#submit-proposal-button, button[aria-label="Apply now"]');
        info.applyEnabled = btn ? !btn.disabled : false;
        info.applyFound = !!btn;

        // Already applied?
        info.alreadyApplied = body.includes('already submitted a proposal') || body.includes('Applied');

        // Get connects cost
        const connectsLines = lines.filter(l => l.includes('Send a proposal'));
        if (connectsLines.length > 0) info.connectsCost = connectsLines[0];

        return {description: description.substring(0, 500), info};
    })()""")

    print(f"  Title: {title[:70]}")
    print(f"  Description: {details['description'][:200]}...")
    for k, v in details['info'].items():
        print(f"  {k}: {v}")

    results.append({
        'name': job['name'],
        'url': job['url'],
        'title': title,
        'details': details,
    })

# Summary
print(f"\n{'='*60}")
print(f"SUMMARY - Best targets:")
print(f"{'='*60}")
for r in results:
    info = r['details']['info']
    applied = info.get('alreadyApplied', False)
    enabled = info.get('applyEnabled', False)
    status = "ALREADY APPLIED" if applied else ("CAN APPLY" if enabled else "CANNOT APPLY")
    print(f"\n  {r['name']}")
    print(f"    Status: {status}")
    print(f"    Budget: {info.get('budget', info.get('amount', 'N/A'))}")
    print(f"    Level: {info.get('level', 'N/A')}")
    print(f"    Proposals: {info.get('proposalCount', info.get('proposals', 'N/A'))}")
    print(f"    Connects: {info.get('connectsCost', 'N/A')}")

pw.stop()
