// Get detailed job listings from Freelancer.com tabs already open
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function scrapeTab(urlMatch, label) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
  if (!tab) { console.log(`${label}: tab not found`); return; }

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
    if (r.exceptionDetails) return null;
    return r.result?.value;
  };

  console.log(`\n=== ${label} ===`);
  console.log(`URL: ${tab.url}\n`);

  const result = await eval_(`
    // Get full page text and parse job listings
    const text = document.body.innerText;

    // Try to find structured job data
    const cards = Array.from(document.querySelectorAll('.JobSearchCard-primary-heading, .JobSearchCard-item, [class*="SearchResult"]'));
    if (cards.length > 0) {
      return "CARDS: " + cards.slice(0, 15).map(c => c.textContent.trim().substring(0, 200)).join('\\n---\\n');
    }

    // Fallback: get meaningful text sections
    const lines = text.split('\\n').filter(l => l.trim().length > 10);
    // Find job-related content
    const jobLines = lines.filter(l =>
      l.includes('$') || l.includes('USD') || l.includes('budget') ||
      l.includes('day') || l.includes('bid') || l.includes('hour') ||
      l.includes('left') || l.includes('writer') || l.includes('data') ||
      l.includes('content') || l.includes('entry') || l.includes('project')
    );
    return jobLines.slice(0, 50).join('\\n');
  `);

  console.log(result?.substring(0, 3000) || "No data");
  ws.close();
}

async function main() {
  // Scrape Freelancer writing jobs
  await scrapeTab("freelancer.com/jobs/writing", "Freelancer.com - WRITING JOBS");

  // Scrape Freelancer data entry jobs
  await scrapeTab("freelancer.com/jobs/data-entry", "Freelancer.com - DATA ENTRY JOBS");

  // Scrape PeoplePerHour
  await scrapeTab("peopleperhour.com", "PeoplePerHour - WRITING JOBS");

  // Also search Freelancer for research jobs
  console.log("\n--- Opening Freelancer Research Jobs ---");
  await fetch(`${CDP_HTTP}/json/new?https://www.freelancer.com/jobs/research-writing/?status=all`, { method: "PUT" });
  await sleep(5000);
  await scrapeTab("freelancer.com/jobs/research", "Freelancer.com - RESEARCH JOBS");
}

main().catch(e => console.error("Error:", e.message));
