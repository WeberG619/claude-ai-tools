// Browse and collect actionable Freelancer jobs for writing, data entry, research
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

async function scrapeJobs(send, eval_, searchUrl, category) {
  // Navigate to the search URL
  await send("Page.navigate", { url: searchUrl });
  await sleep(4000);

  const r = await eval_(`
    // Get all project cards
    const projects = Array.from(document.querySelectorAll('[class*="project"], [class*="ProjectItem"], [class*="JobSearchCard"], [class*="search-result"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 50);

    if (projects.length === 0) {
      // Fallback: look for links that look like project listings
      const links = Array.from(document.querySelectorAll('a'))
        .filter(a => a.href?.includes('/projects/') && a.offsetParent !== null)
        .map(a => ({
          title: a.textContent.trim().substring(0, 100),
          url: a.href
        }))
        .filter(l => l.title.length > 10);
      return JSON.stringify({ fallback: true, count: links.length, items: links.slice(0, 10) });
    }

    const items = projects.slice(0, 15).map(p => {
      const title = p.querySelector('a[class*="title"], a[href*="/projects/"], h3, h2');
      const budget = p.textContent.match(/\\$[\\d,]+(?:\\s*-\\s*\\$[\\d,]+)?(?:\\s*USD)?/);
      const bids = p.textContent.match(/(\\d+)\\s*bids?/i);
      const timeLeft = p.textContent.match(/(\\d+[dhm])\\s*left/i);
      const desc = p.querySelector('[class*="desc"], [class*="summary"], p');

      return {
        title: title?.textContent?.trim()?.substring(0, 100) || 'untitled',
        url: title?.href || '',
        budget: budget?.[0] || 'not listed',
        bids: bids?.[1] || '0',
        timeLeft: timeLeft?.[1] || 'unknown',
        desc: desc?.textContent?.trim()?.substring(0, 200) || ''
      };
    });

    return JSON.stringify({ count: items.length, items });
  `);

  return { category, data: JSON.parse(r) };
}

async function main() {
  // Open the Freelancer dashboard tab for navigation
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("freelancer.com"));
  if (!tab) throw new Error("No Freelancer tab found");

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

  console.log("Connected - browsing jobs...\n");

  // Search for different job categories
  const searches = [
    { url: "https://www.freelancer.com/jobs/article-writing/?status=all&ngsw-bypass=", cat: "Article Writing" },
    { url: "https://www.freelancer.com/jobs/data-entry/?status=all&ngsw-bypass=", cat: "Data Entry" },
    { url: "https://www.freelancer.com/jobs/research/?status=all&ngsw-bypass=", cat: "Research" },
    { url: "https://www.freelancer.com/jobs/excel/?status=all&ngsw-bypass=", cat: "Excel" },
  ];

  const allJobs = [];

  for (const search of searches) {
    console.log(`\n=== ${search.cat} ===`);
    await send("Page.navigate", { url: search.url });
    await sleep(5000);

    const r = await eval_(`
      // Parse the Freelancer job listing page
      const body = document.body.innerText;

      // Get project titles and details from the page
      const projectLinks = Array.from(document.querySelectorAll('a'))
        .filter(a => a.href?.includes('/projects/') && a.offsetParent !== null)
        .map(a => {
          const card = a.closest('[class*="Card"], [class*="Item"], [class*="result"], tr, li') || a.parentElement?.parentElement;
          const budgetMatch = card?.textContent?.match(/\\$([\\d,]+)(?:\\s*-\\s*\\$([\\d,]+))?\\s*(USD)?/);
          const bidsMatch = card?.textContent?.match(/(\\d+)\\s*bids?/i);
          return {
            title: a.textContent.trim().substring(0, 100),
            url: a.href,
            budget: budgetMatch ? budgetMatch[0] : '',
            bids: bidsMatch ? bidsMatch[1] : '',
            context: card?.textContent?.trim()?.substring(0, 300) || ''
          };
        })
        .filter(p => p.title.length > 10 && !p.title.includes('Browse') && !p.title.includes('Post'));

      // Dedupe by URL
      const seen = new Set();
      const unique = projectLinks.filter(p => {
        if (seen.has(p.url)) return false;
        seen.add(p.url);
        return true;
      });

      return JSON.stringify(unique.slice(0, 8));
    `);

    const jobs = JSON.parse(r);
    console.log(`Found ${jobs.length} jobs:`);
    for (const job of jobs) {
      console.log(`  - ${job.title}`);
      if (job.budget) console.log(`    Budget: ${job.budget} | Bids: ${job.bids}`);
      allJobs.push({ ...job, category: search.cat });
    }
  }

  // Summary
  console.log(`\n\n========== JOB SUMMARY ==========`);
  console.log(`Total jobs found: ${allJobs.length}`);
  console.log(`\nBest opportunities (by potential):`);

  // Sort by those with fewer bids (less competition)
  const sorted = allJobs
    .filter(j => j.budget)
    .sort((a, b) => (parseInt(a.bids) || 999) - (parseInt(b.bids) || 999));

  for (const job of sorted.slice(0, 10)) {
    console.log(`\n  ${job.title}`);
    console.log(`  Category: ${job.category} | Budget: ${job.budget} | Bids: ${job.bids || 'few'}`);
    console.log(`  URL: ${job.url}`);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
