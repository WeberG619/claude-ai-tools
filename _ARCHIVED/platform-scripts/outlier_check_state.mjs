const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("Tabs:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

  // Try outlier first, then google
  const outlierTab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google"));
  const target = outlierTab || googleTab;

  if (target) {
    const match = target.url.includes("outlier") ? "outlier" : "accounts.google";
    const { ws, send, eval_ } = await connectToPage(match);
    const url = await eval_(`return window.location.href`);
    console.log("\nURL:", url);
    const text = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage:", text);

    const els = await eval_(`
      const items = Array.from(document.querySelectorAll('button, a, [role="button"], input[type="file"]'));
      return JSON.stringify(items.filter(el => el.offsetParent !== null).map(el => ({
        tag: el.tagName,
        text: (el.textContent || '').trim().substring(0, 60),
        type: el.type || '',
        href: el.href || ''
      })).slice(0, 30));
    `);
    console.log("\nClickable:", els);
    ws.close();
  } else {
    console.log("No Outlier or Google tab found");
  }
})().catch(e => console.error("Error:", e.message));
