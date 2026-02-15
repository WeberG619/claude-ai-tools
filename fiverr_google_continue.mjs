const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
  if (!googleTab) { console.log("No Google popup"); return; }

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

  // Click Continue button
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Continue');
    if (btn) {
      btn.click();
      return 'clicked';
    }
    return 'not found';
  `);
  console.log("Continue:", r);

  await sleep(8000);

  // Check Fiverr tab
  const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
  const fiverrTab = tabs2.find(t => t.type === "page" && t.url.includes("fiverr"));
  if (fiverrTab) {
    const ws2 = new WebSocket(fiverrTab.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws2.addEventListener("open", res); ws2.addEventListener("error", rej); });
    let id2 = 1;
    const pending2 = new Map();
    ws2.addEventListener("message", e => {
      const m = JSON.parse(e.data);
      if (m.id && pending2.has(m.id)) {
        const p = pending2.get(m.id);
        pending2.delete(m.id);
        if (m.error) p.rej(new Error(m.error.message));
        else p.res(m.result);
      }
    });
    const send2 = (method, params = {}) => new Promise((res, rej) => {
      const i = id2++;
      pending2.set(i, { res, rej });
      ws2.send(JSON.stringify({ id: i, method, params }));
    });
    const eval2 = async (expr) => {
      const r = await send2("Runtime.evaluate", {
        expression: `(async () => { ${expr} })()`,
        returnByValue: true, awaitPromise: true
      });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    r = await eval2(`return window.location.href`);
    console.log("\nFiverr URL:", r);
    r = await eval2(`return document.body.innerText.substring(0, 2000)`);
    console.log("\nFiverr page:", r);

    // If logged in, navigate to profile settings
    if (!r.includes("Sign in to your account")) {
      console.log("\nLogged in! Navigating to profile page...");
      await send2("Page.navigate", { url: "https://www.fiverr.com/users/weberg619" });
      await sleep(5000);
      r = await eval2(`return window.location.href`);
      console.log("\nProfile URL:", r);
      r = await eval2(`return document.body.innerText.substring(0, 3000)`);
      console.log("\nProfile page:", r);
    }

    ws2.close();
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
