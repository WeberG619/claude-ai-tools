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
  let { ws, send, eval_ } = await connectToPage("freelancer.com");

  // First dismiss the phone verify banner if possible
  let r = await eval_(`
    // Look for close/dismiss button on the verify banner
    const dismissBtns = Array.from(document.querySelectorAll('button, a, [role="button"]'))
      .filter(el => {
        const t = el.textContent.toLowerCase().trim();
        return (t.includes('close') || t.includes('dismiss') || t.includes('later') || t === 'x' || t === '×')
          && el.offsetParent !== null;
      });
    if (dismissBtns.length > 0) {
      dismissBtns[0].click();
      return 'dismissed: ' + dismissBtns[0].textContent.trim();
    }
    return 'no dismiss button found';
  `);
  console.log("Dismiss:", r);
  await sleep(1000);

  // Navigate to the PDF Data Scrape job
  await eval_(`window.location.href = 'https://www.freelancer.com/jobs/data-entry/?w=f&ngsw-bypass='`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("freelancer.com"));

  // Find the PDF Data Scrape job link
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    const pdfJob = links.find(a => a.textContent.includes('PDF Data Scrape'));
    if (pdfJob) return JSON.stringify({ text: pdfJob.textContent.trim(), href: pdfJob.href });

    // Also find other good jobs
    const jobs = links
      .filter(a => a.href && a.href.includes('/projects/') && a.offsetParent !== null)
      .map(a => ({ text: a.textContent.trim().substring(0, 80), href: a.href }))
      .filter(j => j.text.length > 10);
    return JSON.stringify(jobs.slice(0, 15));
  `);
  console.log("\\nJob links found:");
  console.log(r);

  // Click on the PDF Data Scrape job
  const jobs = JSON.parse(r);
  const pdfJob = Array.isArray(jobs) ? jobs.find(j => j.text.includes('PDF Data Scrape')) : jobs;

  if (pdfJob && pdfJob.href) {
    await eval_(`window.location.href = '${pdfJob.href}'`);
    await sleep(5000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("freelancer.com"));

    r = await eval_(`
      const body = document.body.innerText;
      return body.substring(0, 6000);
    `);
    console.log("\\n========== PDF DATA SCRAPE JOB DETAILS ==========");
    console.log(r);

    // Check for bid/proposal button
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button, a'))
        .filter(el => el.offsetParent !== null)
        .filter(el => {
          const t = el.textContent.toLowerCase();
          return t.includes('bid') || t.includes('place') || t.includes('proposal');
        })
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 60),
          href: el.href || ''
        }));
      return JSON.stringify(btns);
    `);
    console.log("\\nBid buttons:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
