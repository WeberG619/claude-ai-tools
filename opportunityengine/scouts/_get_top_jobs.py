"""Get full details and URLs for top job picks."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Search for each top job by title and get full URL + description
TOP_SEARCHES = [
    "1-Hour Paid Validation Task Python Playwright",
    "Base44 AI Systems Developer RAG",
    "Junior Automation Tools Engineer",
    "Autocad Draftsman ELV Systems Equipment Layout",
    "Voice AI Automation Developer Outbound",
]

for search_term in TOP_SEARCHES:
    print(f"\n{'='*60}")
    print(f"Looking up: {search_term[:50]}")

    encoded = search_term.replace(" ", "+")
    url = f"https://www.upwork.com/nx/search/jobs/?q={encoded}&sort=recency"
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
    time.sleep(2)

    if "Just a moment" in page.title():
        print("  Cloudflare blocked")
        continue

    # Get first job link
    job_info = page.evaluate("""(() => {
        const links = document.querySelectorAll('a[href*="/jobs/~"]');
        if (links.length === 0) return null;

        const link = links[0];
        const href = link.href.split('?')[0];
        const title = link.textContent.trim();

        // Find the card
        let card = link;
        for (let i = 0; i < 10; i++) {
            if (!card.parentElement) break;
            card = card.parentElement;
            if (card.tagName === 'SECTION') break;
        }

        return {title, url: href, cardText: (card.innerText || '').substring(0, 500)};
    })()""")

    if job_info:
        print(f"  Title: {job_info['title'][:70]}")
        print(f"  URL: {job_info['url']}")

        # Now navigate to the actual job page
        page.evaluate(f"window.location.href = '{job_info['url']}'")
        time.sleep(4)
        for i in range(20):
            try:
                if "Just a moment" in page.title():
                    time.sleep(2)
                else:
                    break
            except:
                time.sleep(2)
        time.sleep(2)

        if "Just a moment" not in page.title():
            # Get full description
            full_info = page.evaluate("""(() => {
                const body = document.body.innerText;
                const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

                // Find description section
                let desc = '';
                let inDesc = false;
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i].length > 100 && !desc) {
                        desc = lines.slice(i, i+15).join('\\n');
                        break;
                    }
                }

                // Key info
                const info = {};
                for (const line of lines) {
                    if (line.includes('Est. budget')) info.budget = line;
                    if (line.match(/^Hourly/)) info.hourly = line;
                    if (line.includes('Proposals:')) info.proposals = line;
                    if (line.includes('Connects')) info.connects = line;
                    if (line.includes('Skills and Expertise')) info.skillsHeader = true;
                }

                // Skills
                const skills = [];
                let afterSkills = false;
                for (const line of lines) {
                    if (line === 'Skills and Expertise') { afterSkills = true; continue; }
                    if (afterSkills && line.length > 2 && line.length < 40 && !line.includes('Activity')) {
                        skills.push(line);
                        if (skills.length >= 10) break;
                    }
                    if (afterSkills && (line.includes('Activity') || line.includes('Proposals'))) break;
                }

                // Apply button
                const btn = document.querySelector('#submit-proposal-button');
                const canApply = btn ? !btn.disabled : false;
                const alreadyApplied = body.includes('already submitted');

                return {desc: desc.substring(0, 800), info, skills, canApply, alreadyApplied};
            })()""")

            print(f"\n  Can Apply: {full_info['canApply']}")
            print(f"  Already Applied: {full_info['alreadyApplied']}")
            if full_info['info']:
                for k, v in full_info['info'].items():
                    print(f"  {k}: {v}")
            print(f"  Skills: {', '.join(full_info['skills'][:8])}")
            print(f"\n  Description:\n  {full_info['desc'][:500]}")
        else:
            print("  Job page Cloudflare blocked")
    else:
        print("  No results found")

pw.stop()
