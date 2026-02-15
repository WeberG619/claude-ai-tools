// Get budget details from Freelancer.com job listings
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function scrapeFullPage(urlMatch, label) {
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

  // Get the full page text with better parsing
  const result = await eval_(`
    // Get all text, looking for price patterns
    const text = document.body.innerText;
    const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

    // Find job blocks - look for patterns like title + budget + bids
    let jobs = [];
    let current = null;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Detect budget lines
      if (line.match(/\\$\\d+/) || line.match(/USD/) || line.match(/\\d+\\s*-\\s*\\d+/) && line.length < 30) {
        if (current) current.budget = line;
      }
      // Detect "X days left"
      else if (line.includes('days left') || line.includes('day left')) {
        if (current) current.deadline = line;
      }
      // Detect bid count
      else if (line.match(/^\\d+ bids?$/)) {
        if (current) {
          current.bids = line;
          jobs.push(current);
          current = null;
        }
      }
      // Detect descriptions (longer text after a title)
      else if (line.length > 80 && current && !current.desc) {
        current.desc = line.substring(0, 200);
      }
      // Detect titles (shorter, capitalized lines that are not navigation)
      else if (line.length > 15 && line.length < 100 &&
               !line.includes('Dashboard') && !line.includes('Browse') &&
               !line.includes('How It Works') && !line.includes('Sign') &&
               !['Verified', 'FEATURED', 'SEALED', 'URGENT', 'NDA'].includes(line) &&
               !current) {
        current = { title: line };
      }
    }
    if (current && current.title) jobs.push(current);

    return JSON.stringify(jobs.slice(0, 15), null, 2);
  `);

  console.log(result);
  ws.close();
}

async function main() {
  await scrapeFullPage("freelancer.com/jobs/writing", "WRITING JOBS");
  await scrapeFullPage("freelancer.com/jobs/data-entry", "DATA ENTRY JOBS");
  await scrapeFullPage("freelancer.com/jobs/research", "RESEARCH JOBS");
}

main().catch(e => console.error("Error:", e.message));
