// Robust job scraper - examine page structure first, then extract jobs
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

const categories = [
  "data-entry", "article-writing", "excel", "copywriting",
  "transcription", "research-writing", "content-writing",
  "data-processing", "technical-writing", "proofreading"
];

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // First, inspect the page structure on a known category
  console.log("=== Inspecting page structure ===");
  await send("Page.navigate", { url: "https://www.freelancer.com/jobs/data-entry/" });
  await sleep(4000);

  let r = await eval_(`
    // Get the raw text to understand the structure
    const text = document.body.innerText.substring(0, 3000);

    // Find all links to project pages
    const projectLinks = Array.from(document.querySelectorAll('a[href*="/projects/"]'))
      .filter(a => !a.href.includes('/proposals') && !a.href.includes('/payments'))
      .slice(0, 3)
      .map(a => ({
        text: a.textContent.trim().substring(0, 60),
        href: a.href.substring(0, 100),
        parentTag: a.parentElement?.tagName,
        parentClass: a.parentElement?.className?.toString()?.substring(0, 60),
        grandparentClass: a.parentElement?.parentElement?.className?.toString()?.substring(0, 60)
      }));

    return JSON.stringify({ projectLinks, textPreview: text });
  `);
  console.log("Structure:", r?.substring(0, 1000));

  // Now try a text-based extraction approach
  const allJobs = [];
  const seenTitles = new Set();

  for (const cat of categories) {
    console.log(`\n=== ${cat} ===`);
    await send("Page.navigate", { url: `https://www.freelancer.com/jobs/${cat}/` });
    await sleep(4000);

    r = await eval_(`
      // Extract jobs from the page text - Freelancer uses Angular with dynamic classes
      // Parse the visible text structure
      const pageText = document.body.innerText;

      // Find all project links
      const links = Array.from(document.querySelectorAll('a'))
        .filter(a => {
          const h = a.href || '';
          return h.includes('/projects/') && !h.includes('/proposals') &&
                 !h.includes('/payments') && !h.includes('/reviews') &&
                 a.textContent.trim().length > 10 && a.textContent.trim().length < 150;
        });

      // For each project link, extract context from its card/row
      const jobs = [];
      const seen = new Set();

      for (const link of links) {
        const title = link.textContent.trim();
        if (seen.has(title) || title.length < 10) continue;
        seen.add(title);

        // Walk up to find the card container
        let container = link;
        for (let i = 0; i < 8; i++) {
          container = container.parentElement;
          if (!container) break;
          const rect = container.getBoundingClientRect();
          if (rect.height > 80 && rect.height < 500 && rect.width > 400) break;
        }

        if (!container) continue;
        const cardText = container.innerText || '';
        const lines = cardText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

        // Extract budget - look for currency patterns
        const budgetMatch = cardText.match(/([\$₹€£][\d,]+(?:\.\d+)?(?:\s*[-–]\s*[\$₹€£]?[\d,]+(?:\.\d+)?)?(?:\s*(?:USD|INR|EUR|GBP))?)/);
        const budget = budgetMatch ? budgetMatch[1] : '';

        // Extract bid count
        const bidMatch = cardText.match(/(\d+)\s*(?:bids?|entries|proposals)/i);
        const bids = bidMatch ? bidMatch[1] + ' bids' : '';

        // Extract description (first paragraph-like text that isn't the title)
        const desc = lines
          .filter(l => l !== title && l.length > 30 && l.length < 300 && !l.match(/^[\$₹€£\d]/))
          .slice(0, 1)
          .join(' ')
          .substring(0, 150);

        // Extract skills
        const skillEls = container.querySelectorAll('[class*="tag" i], [class*="skill" i], [class*="Tag" i], [class*="Skill" i]');
        const skills = Array.from(skillEls).map(s => s.textContent.trim()).filter(s => s.length > 1 && s.length < 30).slice(0, 8).join(', ');

        jobs.push({
          title,
          href: link.href,
          budget,
          bids,
          desc,
          skills
        });
      }

      return JSON.stringify(jobs.slice(0, 15));
    `);

    try {
      const jobs = JSON.parse(r);
      console.log(`Found ${jobs.length} jobs:`);
      for (const job of jobs) {
        if (!seenTitles.has(job.title)) {
          seenTitles.add(job.title);
          allJobs.push({ ...job, category: cat });
          console.log(`  - ${job.title.substring(0, 60)} | ${job.budget} | ${job.bids}`);
        }
      }
    } catch (e) {
      console.log("  Error parsing:", e.message);
    }
  }

  console.log(`\n========================================`);
  console.log(`TOTAL UNIQUE JOBS: ${allJobs.length}`);
  console.log(`========================================`);

  console.log("\nJOBS_JSON_START");
  console.log(JSON.stringify(allJobs, null, 2));
  console.log("JOBS_JSON_END");

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
