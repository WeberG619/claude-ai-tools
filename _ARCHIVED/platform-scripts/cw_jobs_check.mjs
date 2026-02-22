const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("clickworker") || t.url.includes("unipark")));
  if (!tab) tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  // Check current page
  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Navigate to jobs page
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("Jobs URL:", r);

  // Check for 2FA
  if (r.includes("two_fa")) {
    console.log("BLOCKED BY 2FA");
    ws.close();
    return;
  }

  // Get balance
  r = await eval_(`
    const text = document.body.innerText;
    const match = text.match(/Account balance \\$ ([\\d.]+)/);
    return match ? match[1] : 'unknown';
  `);
  console.log("Balance: $" + r);

  // Get all available jobs
  r = await eval_(`
    const rows = document.querySelectorAll('tr');
    const jobs = [];
    rows.forEach(row => {
      const cells = row.querySelectorAll('td');
      if (cells.length >= 3) {
        const link = cells[0]?.querySelector('a');
        jobs.push({
          name: cells[0]?.textContent?.trim().substring(0, 80),
          href: link?.href || '',
          count: cells[1]?.textContent?.trim(),
          pay: cells[2]?.textContent?.trim()
        });
      }
    });
    return JSON.stringify(jobs.filter(j => j.href));
  `);
  console.log("Available jobs:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
