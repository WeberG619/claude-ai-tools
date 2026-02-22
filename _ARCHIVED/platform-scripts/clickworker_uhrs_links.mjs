const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
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

  // Get all links on the page, especially the "click here" ones
  let r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    return JSON.stringify(links.filter(a => {
      const text = a.textContent?.trim().toLowerCase() || '';
      return text.includes('click here') || text.includes('register') ||
             a.href?.includes('microsoft') || a.href?.includes('live.com') ||
             a.href?.includes('hotmail') || a.href?.includes('outlook');
    }).map(a => ({
      text: a.textContent?.trim().substring(0, 80),
      href: a.href,
      target: a.target || ''
    })));
  `);
  console.log("Relevant links:", r);

  // Also get the full form area HTML to find embedded links
  r = await eval_(`
    const form = document.querySelector('form');
    return form ? form.outerHTML.substring(0, 5000) : 'no form';
  `);
  console.log("\nForm HTML:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
