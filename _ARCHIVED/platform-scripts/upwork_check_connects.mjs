const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("upwork"));
  if (!tab) { console.log("No Upwork tab"); return; }

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

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  // Navigate to find work page where connects are shown
  await send("Page.navigate", { url: "https://www.upwork.com/nx/find-work/best-matches" });
  await sleep(8000);

  r = await eval_(`return window.location.href`);
  console.log("URL:", r);

  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Search for Connects info specifically
  r = await eval_(`
    const text = document.body.innerText;
    const lines = text.split('\\n');
    const connectLines = lines.filter(l => l.toLowerCase().includes('connect'));
    return JSON.stringify(connectLines.slice(0, 10));
  `);
  console.log("\nConnect-related lines:", r);

  // Also check the sidebar/stats area
  r = await eval_(`
    const els = document.querySelectorAll('[class*="connect"], [data-test*="connect"], [class*="Connect"]');
    return JSON.stringify(Array.from(els).map(el => ({
      tag: el.tagName,
      text: el.textContent.trim().substring(0, 80),
      classes: (typeof el.className === 'string' ? el.className : '').substring(0, 60)
    })));
  `);
  console.log("\nConnect elements:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
