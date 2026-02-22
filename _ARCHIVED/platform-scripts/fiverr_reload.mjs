const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("All page targets:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url?.substring(0, 100)));

  const fiverrTab = tabs.find(t => t.type === "page" && t.url.includes("fiverr"));
  if (!fiverrTab) { console.log("No Fiverr tab"); return; }

  const ws = new WebSocket(fiverrTab.webSocketDebuggerUrl);
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

  // Navigate to Fiverr homepage to check login status
  await send("Page.navigate", { url: "https://www.fiverr.com/" });
  await sleep(5000);

  let r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);

  // Check if logged in by looking for username or dashboard elements
  r = await eval_(`
    const text = document.body.innerText;
    const hasSignIn = text.includes('Sign in');
    const hasJoin = text.includes('Join');
    const hasDashboard = text.includes('Dashboard');
    const hasInbox = text.includes('Inbox');
    const hasOrders = text.includes('Orders');
    return JSON.stringify({ hasSignIn, hasJoin, hasDashboard, hasInbox, hasOrders });
  `);
  console.log("Login check:", r);

  r = await eval_(`return document.body.innerText.substring(0, 1500)`);
  console.log("\nPage:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
