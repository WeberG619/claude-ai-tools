const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("All targets:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

  // Look for Google accounts popup
  const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));

  if (googleTab) {
    console.log("\nFound Google popup:", googleTab.url.substring(0, 100));
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

    let r = await eval_(`return document.body.innerText.substring(0, 2000)`);
    console.log("\nGoogle popup content:", r);

    // Look for weberg619 account
    r = await eval_(`
      const els = Array.from(document.querySelectorAll('*'));
      const accounts = els.filter(el => el.textContent.includes('weberg619') || el.textContent.includes('Weber'));
      return JSON.stringify(accounts.slice(0, 5).map(el => ({
        tag: el.tagName,
        text: el.textContent.trim().substring(0, 60),
        rect: (() => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
      })));
    `);
    console.log("\nAccount elements:", r);

    ws.close();
  } else {
    console.log("\nNo Google popup found. Trying alternative: navigate directly to Fiverr with cookie-based login");

    // Maybe we need to try the email login instead
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

      const clickAt = async (x, y) => {
        await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
        await sleep(50);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
        await sleep(80);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
      };

      // Click "Continue with email/username"
      let r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.includes('email'));
        if (btn) {
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return 'not found';
      `);
      console.log("\nEmail login button:", r);

      if (r !== 'not found') {
        const pos = JSON.parse(r);
        await clickAt(pos.x, pos.y);
        console.log("Clicked email login");
        await sleep(2000);

        r = await eval_(`
          const inputs = document.querySelectorAll('input');
          return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
            type: i.type,
            name: i.name,
            id: i.id,
            placeholder: i.placeholder
          })));
        `);
        console.log("\nInputs:", r);
      }

      ws.close();
    }
  }
})().catch(e => console.error("Error:", e.message));
