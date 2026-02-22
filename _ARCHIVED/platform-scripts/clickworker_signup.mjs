const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  // Use the Outlier tab for Clickworker
  const tab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
  if (!tab) { console.log("No available tab"); return; }

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

  // Navigate to Clickworker signup
  await send("Page.navigate", { url: "https://www.clickworker.com/clickworker/" });
  await sleep(8000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage:", r);

  // Look for signup/register buttons
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a, button'));
    return JSON.stringify(links.filter(l => {
      const text = l.textContent.toLowerCase();
      return text.includes('sign up') || text.includes('register') || text.includes('join') || text.includes('create account') || text.includes('get started');
    }).map(l => ({
      tag: l.tagName,
      text: l.textContent.trim().substring(0, 50),
      href: l.href?.substring(0, 80) || ''
    })));
  `);
  console.log("\nSignup links:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
