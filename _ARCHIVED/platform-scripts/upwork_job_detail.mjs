const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
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
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");

  // Search for the script writer job
  await eval_(`window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=' + encodeURIComponent('script writer youtube geography') + '&sort=recency&payment_verified=1'`);
  await sleep(6000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Find and click the job title link
  let r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    const jobLink = links.find(a => a.textContent.includes('Script Writer') && a.href.includes('/jobs/'));
    if (jobLink) {
      return JSON.stringify({ text: jobLink.textContent.trim(), href: jobLink.href });
    }
    // Try h3 links
    const h3Links = Array.from(document.querySelectorAll('h3 a, h2 a'));
    const found = h3Links.find(a => a.textContent.toLowerCase().includes('script'));
    if (found) return JSON.stringify({ text: found.textContent.trim(), href: found.href });
    return 'not found';
  `);
  console.log("Job link:", r);

  if (r !== 'not found') {
    const job = JSON.parse(r);
    // Navigate to the job detail page
    await eval_(`window.location.href = '${job.href}'`);
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    // Get full job details
    r = await eval_(`
      const main = document.querySelector('main') || document.body;
      return main.innerText.substring(0, 10000);
    `);
    console.log("\\n========== FULL JOB DETAILS ==========");
    console.log(r);

    // Also get the URL
    r = await eval_(`return window.location.href`);
    console.log("\\nURL:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
