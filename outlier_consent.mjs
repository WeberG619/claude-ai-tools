const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(CDP_HTTP + "/json")).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
  if (!tab) { console.log("No Google tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener("open", r));
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

  // Find and click "Continue" button
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, [role="button"]'))
      .find(el => el.textContent.trim() === 'Continue' && el.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Continue button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: pos.x, y: pos.y });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("Clicked Continue");

    await sleep(10000);

    ws.close(); await sleep(1000);
    const tabs2 = await (await fetch(CDP_HTTP + "/json")).json();
    console.log("\nTabs after consent:");
    tabs2.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

    // Find Outlier tab
    const oTab = tabs2.find(t => t.type === "page" && t.url.includes("outlier") && !t.url.includes("google"));
    const anyTab = tabs2.find(t => t.type === "page" && (t.url.includes("outlier") || t.url.includes("google")));
    const checkTab = oTab || anyTab;

    if (checkTab) {
      const ws2 = new WebSocket(checkTab.webSocketDebuggerUrl);
      await new Promise(r => ws2.addEventListener("open", r));
      const pending2 = new Map();
      let id2 = 1;
      ws2.addEventListener("message", e => {
        const m = JSON.parse(e.data);
        if (m.id && pending2.has(m.id)) {
          const p = pending2.get(m.id);
          pending2.delete(m.id);
          if (m.error) p.rej(new Error(m.error.message));
          else p.res(m.result);
        }
      });
      const eval2 = async (expr) => {
        const i = id2++;
        const r = await new Promise((res, rej) => {
          pending2.set(i, { res, rej });
          ws2.send(JSON.stringify({ id: i, method: "Runtime.evaluate", params: {
            expression: `(async () => { ${expr} })()`,
            returnByValue: true, awaitPromise: true
          }}));
        });
        if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
        return r.result?.value;
      };

      r = await eval2(`return window.location.href`);
      console.log("\nURL:", r);
      r = await eval2(`return document.body.innerText.substring(0, 5000)`);
      console.log("\nPage:", r);

      // Bring to front
      const send2 = (method, params = {}) => new Promise((res, rej) => {
        const i = id2++;
        pending2.set(i, { res, rej });
        ws2.send(JSON.stringify({ id: i, method, params }));
      });
      await send2("Page.bringToFront");

      ws2.close();
    }
  }
})().catch(e => console.error("Error:", e.message));
