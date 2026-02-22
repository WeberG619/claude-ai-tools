const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("upwork"));
  if (!tab) { console.log("No Upwork tab"); return; }

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

  // Click "Continue with Google"
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, a'))
      .find(b => b.textContent.includes('Google'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Google button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked Google sign-in");
    await sleep(5000);

    // Check for Google popup
    const tabs2 = await (await fetch(`${CDP_HTTP}/json`)).json();
    const googleTab = tabs2.find(t => t.type === "page" && t.url.includes("accounts.google.com"));

    if (googleTab) {
      console.log("Google popup found");
      const gws = new WebSocket(googleTab.webSocketDebuggerUrl);
      await new Promise((res, rej) => { gws.addEventListener("open", res); gws.addEventListener("error", rej); });
      let gid = 1;
      const gpending = new Map();
      gws.addEventListener("message", e => {
        const m = JSON.parse(e.data);
        if (m.id && gpending.has(m.id)) {
          const p = gpending.get(m.id);
          gpending.delete(m.id);
          if (m.error) p.rej(new Error(m.error.message));
          else p.res(m.result);
        }
      });
      const gsend = (method, params = {}) => new Promise((res, rej) => {
        const i = gid++;
        gpending.set(i, { res, rej });
        gws.send(JSON.stringify({ id: i, method, params }));
      });
      const geval = async (expr) => {
        const r = await gsend("Runtime.evaluate", {
          expression: `(async () => { ${expr} })()`,
          returnByValue: true, awaitPromise: true
        });
        if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
        return r.result?.value;
      };

      r = await geval(`return document.body.innerText.substring(0, 500)`);
      console.log("Google page:", r.substring(0, 200));

      // If account chooser, pick weberg619
      if (r.includes("Choose an account") || r.includes("weberg619")) {
        r = await geval(`
          const items = document.querySelectorAll('[data-email="weberg619@gmail.com"]');
          if (items.length > 0) { items[0].click(); return 'clicked'; }
          const all = document.querySelectorAll('li, div[role="link"]');
          for (const el of all) {
            if (el.textContent.includes('weberg619')) { el.click(); return 'clicked by text'; }
          }
          return 'not found';
        `);
        console.log("Account select:", r);
        await sleep(5000);

        // Check for consent
        try {
          r = await geval(`return document.body.innerText.substring(0, 300)`);
          if (r.includes("Continue")) {
            r = await geval(`
              const btn = Array.from(document.querySelectorAll('button'))
                .find(b => b.textContent.trim() === 'Continue');
              if (btn) { btn.click(); return 'clicked'; }
              return 'no button';
            `);
            console.log("Consent:", r);
            await sleep(8000);
          }
        } catch(e) {
          // Popup may have closed
          console.log("Popup closed (expected after auth)");
          await sleep(5000);
        }
      }

      // If consent screen directly
      if (r.includes("Continue") && r.includes("Upwork")) {
        r = await geval(`
          const btn = Array.from(document.querySelectorAll('button'))
            .find(b => b.textContent.trim() === 'Continue');
          if (btn) { btn.click(); return 'clicked'; }
          return 'no button';
        `);
        console.log("Consent:", r);
        await sleep(8000);
      }

      gws.close();
    }

    // Check Upwork page now
    await sleep(3000);
    r = await eval_(`return window.location.href`);
    console.log("\nUpwork URL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 2000)`);
    console.log("\nUpwork page:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
