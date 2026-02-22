const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  // Create a new tab via CDP HTTP API
  const res = await fetch(`${CDP_HTTP}/json/new?https://app.outlier.ai`);
  const tab = await res.json();
  console.log("New tab:", tab.url);

  await sleep(8000);

  // Connect to it
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
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  // Check clickable elements
  r = await eval_(`
    const els = Array.from(document.querySelectorAll('button, a, [role="button"]'));
    return JSON.stringify(els.filter(el => el.offsetParent !== null && el.textContent.trim()).map(el => ({
      tag: el.tagName,
      text: el.textContent.trim().substring(0, 60),
      href: el.href || ''
    })).slice(0, 30));
  `);
  console.log("\nClickable:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
