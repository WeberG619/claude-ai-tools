// Browse Freelancer jobs across multiple categories and extract details
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

// Categories to search - things Claude can actually do
const searches = [
  { name: "Data Entry", url: "https://www.freelancer.com/jobs/data-entry/?status=all&projectUpgradeFilter=guaranteed" },
  { name: "Article Writing", url: "https://www.freelancer.com/jobs/article-writing/?status=all" },
  { name: "Research Writing", url: "https://www.freelancer.com/jobs/research-writing/?status=all" },
  { name: "Excel", url: "https://www.freelancer.com/jobs/excel/?status=all" },
  { name: "Copywriting", url: "https://www.freelancer.com/jobs/copywriting/?status=all" },
  { name: "Transcription", url: "https://www.freelancer.com/jobs/transcription/?status=all" },
  { name: "Data Processing", url: "https://www.freelancer.com/jobs/data-processing/?status=all" },
  { name: "Technical Writing", url: "https://www.freelancer.com/jobs/technical-writing/?status=all" },
  { name: "Proofreading", url: "https://www.freelancer.com/jobs/proofreading/?status=all" },
  { name: "Content Writing", url: "https://www.freelancer.com/jobs/content-writing/?status=all" },
];

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  const allJobs = [];
  const seenTitles = new Set();

  for (const search of searches) {
    console.log(`\n=== ${search.name} ===`);
    await send("Page.navigate", { url: search.url });
    await sleep(3000);

    let r = await eval_(`
      const items = Array.from(document.querySelectorAll('[class*="JobSearchCard"], [class*="project-card"], [class*="ProjectCard"]'));
      if (items.length === 0) {
        // Try generic approach
        const links = Array.from(document.querySelectorAll('a'))
          .filter(a => a.href?.includes('/projects/') && a.href?.includes('/details'))
          .map(a => {
            const card = a.closest('[class*="card" i], [class*="Card" i], [class*="item" i], [class*="result" i], tr, li') || a.parentElement;
            const title = a.textContent.trim().substring(0, 80);
            const budgetEl = card?.querySelector('[class*="budget" i], [class*="Budget" i], [class*="price" i], [class*="Price" i]');
            const bidsEl = card?.querySelector('[class*="bid" i], [class*="Bid" i], [class*="entries" i]');
            const skillEls = card?.querySelectorAll('[class*="skill" i], [class*="Skill" i], [class*="tag" i], [class*="Tag" i]');
            const timeEl = card?.querySelector('[class*="time" i], [class*="Time" i], [class*="date" i], [class*="Date" i]');
            return {
              title,
              href: a.href,
              budget: budgetEl?.textContent?.trim()?.substring(0, 40) || '',
              bids: bidsEl?.textContent?.trim()?.substring(0, 20) || '',
              skills: skillEls ? Array.from(skillEls).map(s => s.textContent.trim()).slice(0, 5).join(', ') : '',
              time: timeEl?.textContent?.trim()?.substring(0, 30) || ''
            };
          })
          .filter(j => j.title.length > 5);

        // Deduplicate
        const unique = [];
        const seen = new Set();
        for (const j of links) {
          if (!seen.has(j.title)) {
            seen.add(j.title);
            unique.push(j);
          }
        }
        return JSON.stringify(unique.slice(0, 15));
      }

      return JSON.stringify(items.slice(0, 15).map(card => {
        const titleEl = card.querySelector('a[class*="title" i], a[href*="/projects/"]');
        const budgetEl = card.querySelector('[class*="budget" i], [class*="Budget" i], [class*="price" i]');
        const bidsEl = card.querySelector('[class*="bid" i], [class*="Bid" i], [class*="entries" i]');
        const descEl = card.querySelector('[class*="desc" i], [class*="Desc" i], p');
        return {
          title: titleEl?.textContent?.trim()?.substring(0, 80) || '',
          href: titleEl?.href || '',
          budget: budgetEl?.textContent?.trim()?.substring(0, 40) || '',
          bids: bidsEl?.textContent?.trim()?.substring(0, 20) || '',
          desc: descEl?.textContent?.trim()?.substring(0, 100) || ''
        };
      }));
    `);

    try {
      const jobs = JSON.parse(r);
      console.log(`Found ${jobs.length} jobs:`);
      for (const job of jobs) {
        if (!seenTitles.has(job.title) && job.title.length > 5) {
          seenTitles.add(job.title);
          allJobs.push({ ...job, category: search.name });
          console.log(`  - ${job.title} | ${job.budget} | ${job.bids}`);
        }
      }
    } catch (e) {
      console.log("  Parse error:", r?.substring(0, 200));
    }
  }

  console.log(`\n\n========================================`);
  console.log(`TOTAL UNIQUE JOBS FOUND: ${allJobs.length}`);
  console.log(`========================================\n`);

  // Output as JSON for parsing
  console.log("JOBS_JSON_START");
  console.log(JSON.stringify(allJobs, null, 2));
  console.log("JOBS_JSON_END");

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
