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

  // Find the bimopsstudio account element position
  let r = await eval_(`
    const els = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent.includes('bimopsstudio') && el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 80),
        class: (el.className || '').toString().substring(0, 60),
        rect: JSON.parse(JSON.stringify(el.getBoundingClientRect())),
        children: el.children.length
      }))
      .filter(el => el.rect.height > 20 && el.rect.height < 200);
    return JSON.stringify(els, null, 2);
  `);
  console.log("Account elements:");
  console.log(r);

  const els = JSON.parse(r);
  // Find the clickable account item (usually a li or div that's 50-100px tall)
  const accountItem = els.find(e => e.rect.height > 40 && e.rect.height < 150) || els[0];

  if (accountItem) {
    const x = Math.round(accountItem.rect.x + accountItem.rect.width / 2);
    const y = Math.round(accountItem.rect.y + accountItem.rect.height / 2);
    console.log(`\nClicking account at (${x}, ${y})`);

    // CDP mouse click
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });

    await sleep(8000);

    // Check tabs after
    ws.close(); await sleep(1000);
    const tabs2 = await (await fetch(CDP_HTTP + "/json")).json();
    console.log("\nTabs after click:");
    tabs2.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

    // Check if we're on Outlier now
    const oTab = tabs2.find(t => t.type === "page" && t.url.includes("app.outlier.ai"));
    if (oTab) {
      const ws2 = new WebSocket(oTab.webSocketDebuggerUrl);
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
      console.log("\nOutlier URL:", r);
      r = await eval2(`return document.body.innerText.substring(0, 4000)`);
      console.log("\nOutlier page:", r);
      ws2.close();
    } else {
      // Still on Google? Check
      const gTab = tabs2.find(t => t.type === "page" && t.url.includes("google.com"));
      if (gTab) {
        const ws2 = new WebSocket(gTab.webSocketDebuggerUrl);
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
        console.log("\nStill on Google:", r);
        r = await eval2(`return document.body.innerText.substring(0, 2000)`);
        console.log(r);
        ws2.close();
      }
    }
  }
})().catch(e => console.error("Error:", e.message));
