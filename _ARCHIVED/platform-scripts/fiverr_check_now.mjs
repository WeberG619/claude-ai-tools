const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("All pages:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url?.substring(0, 120)));

  // Check Google popup
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
  if (googleTab) {
    console.log("\nGoogle popup still open");
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

    const r = await eval_(`return document.body.innerText.substring(0, 500)`);
    console.log("Content:", r);

    // If there's a Continue button, click it
    const r2 = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Continue');
      if (btn) { btn.click(); return 'clicked Continue'; }
      return 'no Continue button';
    `);
    console.log("Action:", r2);

    ws.close();
    await sleep(8000);
  }

  // Check Fiverr
  const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
  const fiverrTab = tabs2.find(t => t.type === "page" && t.url.includes("fiverr"));
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

    let r = await eval_(`return window.location.href`);
    console.log("\nFiverr URL:", r);

    const loggedIn = !(await eval_(`return document.body.innerText`)).includes("Sign in to your account");
    console.log("Logged in:", loggedIn);

    if (loggedIn) {
      r = await eval_(`return document.body.innerText.substring(0, 1500)`);
      console.log("Page:", r);
    }

    ws.close();
  }
})().catch(e => console.error("Error:", e.message));
