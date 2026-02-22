// Search for quick-turnaround jobs on Freelancer.com via CDP
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function openAndScrape(url, label) {
  // Open new tab
  const createRes = await fetch(`${CDP_HTTP}/json/new?${url}`, { method: "PUT" });
  const tab = await createRes.json();
  console.log(`Opened: ${label}`);

  // Wait for page to load
  await sleep(5000);

  // Get fresh tab info
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const target = tabs.find(t => t.url.includes(url.replace('https://', '').split('/')[0]) && t.id === tab.id);
  if (!target) {
    console.log(`  Could not find tab for ${label}`);
    return null;
  }

  // Connect to tab
  const ws = new WebSocket(target.webSocketDebuggerUrl);
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

  return { ws, eval_ };
}

async function main() {
  console.log("=== Searching for Quick Jobs ===\n");

  // Search 1: Freelancer.com - writing jobs
  console.log("--- Freelancer.com: Writing/Content Jobs ---");
  const fl = await openAndScrape(
    "https://www.freelancer.com/jobs/writing/?status=all",
    "Freelancer.com - Writing Jobs"
  );

  if (fl) {
    await sleep(3000);
    let r = await fl.eval_(`
      // Try to get job listings
      const jobs = Array.from(document.querySelectorAll('[class*="JobSearchCard"], [class*="project-card"], .project-details, tr[class*="project"]'));
      if (jobs.length === 0) {
        // Fallback: get page text
        return "NO CARDS FOUND. Page text: " + document.body.innerText.substring(0, 2000);
      }
      return JSON.stringify(jobs.slice(0, 10).map(j => ({
        text: j.textContent.trim().substring(0, 300)
      })));
    `);
    console.log(r?.substring(0, 2000));
    fl.ws.close();
  }

  console.log("\n--- Freelancer.com: Data Entry Jobs ---");
  const fl2 = await openAndScrape(
    "https://www.freelancer.com/jobs/data-entry/?status=all",
    "Freelancer.com - Data Entry Jobs"
  );

  if (fl2) {
    await sleep(3000);
    let r = await fl2.eval_(`
      const jobs = Array.from(document.querySelectorAll('[class*="JobSearchCard"], [class*="project-card"], .project-details'));
      if (jobs.length === 0) {
        return "Page text: " + document.body.innerText.substring(0, 2000);
      }
      return JSON.stringify(jobs.slice(0, 10).map(j => ({
        text: j.textContent.trim().substring(0, 300)
      })));
    `);
    console.log(r?.substring(0, 2000));
    fl2.ws.close();
  }

  // Search 2: PeoplePerHour - writing jobs
  console.log("\n--- PeoplePerHour: Writing Jobs ---");
  const pph = await openAndScrape(
    "https://www.peopleperhour.com/freelance-jobs?keyword=writing",
    "PeoplePerHour - Writing Jobs"
  );

  if (pph) {
    await sleep(3000);
    let r = await pph.eval_(`
      const jobs = Array.from(document.querySelectorAll('[class*="job-card"], [class*="listing"], .job-item, article'));
      if (jobs.length === 0) {
        return "Page text: " + document.body.innerText.substring(0, 2000);
      }
      return JSON.stringify(jobs.slice(0, 10).map(j => ({
        text: j.textContent.trim().substring(0, 300)
      })));
    `);
    console.log(r?.substring(0, 2000));
    pph.ws.close();
  }

  console.log("\n=== Done ===");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
