const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  // Check all tabs
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("All page targets:");
  tabs.filter(t => t.type === "page" || t.type === "iframe").forEach(t =>
    console.log(`  ${t.type}: ${t.url?.substring(0, 120)}`)
  );

  // Check if Google popup is still there
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
  if (googleTab) {
    console.log("\nGoogle popup still open!");
    const ws = new WebSocket(googleTab.webSocketDebuggerUrl);
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
    console.log("Google URL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 2000)`);
    console.log("Google content:", r);

    // Look for any buttons (Allow, Continue, Confirm, etc.)
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button, input[type="submit"], a'));
      return JSON.stringify(btns.filter(b => b.offsetParent !== null).map(b => ({
        tag: b.tagName,
        text: b.textContent.trim().substring(0, 50),
        type: b.type || '',
        id: b.id || '',
        rect: (() => { const r = b.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
      })));
    `);
    console.log("\nButtons:", r);

    ws.close();
  }

  // Also reload Fiverr page to check
  const fiverrTab = tabs.find(t => t.type === "page" && t.url.includes("fiverr"));
  if (fiverrTab) {
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

    // Reload Fiverr page
    await send("Page.reload", {});
    await sleep(5000);

    let r = await eval_(`return window.location.href`);
    console.log("\nFiverr URL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 1000)`);
    console.log("Fiverr page:", r);

    ws.close();
  }
})().catch(e => console.error("Error:", e.message));
