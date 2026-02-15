const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  // Connect to the DataAnnotation tab and navigate it to Outlier
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("dataannotation.tech/workers"));
  if (!tab) { console.log("No suitable tab"); return; }

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

  // Navigate to Outlier
  await send("Page.navigate", { url: "https://app.outlier.ai" });
  console.log("Navigating to Outlier...");
  await sleep(8000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:", r);

  r = await eval_(`
    const els = Array.from(document.querySelectorAll('button, a, [role="button"]'));
    return JSON.stringify(els.filter(el => el.offsetParent !== null && el.textContent.trim()).map(el => ({
      tag: el.tagName,
      text: el.textContent.trim().substring(0, 80),
      href: el.href || ''
    })).slice(0, 30));
  `);
  console.log("\nClickable:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
