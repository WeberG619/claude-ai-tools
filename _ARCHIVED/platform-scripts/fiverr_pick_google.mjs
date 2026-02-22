const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
  if (!googleTab) { console.log("No Google popup found"); return; }

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

  const clickAt = async (x, y) => {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  };

  // Find weberg619 account option
  let r = await eval_(`
    const items = document.querySelectorAll('[data-email], li, [role="link"], a');
    const results = [];
    for (const el of items) {
      const email = el.getAttribute('data-email') || '';
      const text = el.textContent || '';
      if (email.includes('weberg619') || text.includes('weberg619')) {
        const rect = el.getBoundingClientRect();
        results.push({
          tag: el.tagName,
          email,
          text: text.trim().substring(0, 60),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        });
      }
    }
    return JSON.stringify(results);
  `);
  console.log("weberg619 elements:", r);

  const items = JSON.parse(r);
  if (items.length > 0) {
    // Click the first match
    const target = items[0];
    await clickAt(target.x, target.y);
    console.log(`Clicked: ${target.email || target.text}`);
    await sleep(8000);

    // Check where we ended up - switch to Fiverr tab
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

      ws2.close();
    }
  } else {
    // Try clicking by finding text "weberg619" anywhere on page
    r = await eval_(`
      const all = document.querySelectorAll('*');
      for (const el of all) {
        if (el.children.length === 0 && el.textContent.includes('weberg619')) {
          const rect = el.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: el.textContent.trim() });
        }
      }
      return 'not found';
    `);
    console.log("Fallback weberg619:", r);
    if (r !== 'not found') {
      const pos = JSON.parse(r);
      await clickAt(pos.x, pos.y);
      console.log("Clicked weberg619");
    }
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
