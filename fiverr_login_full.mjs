const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  // Get Fiverr tab
  let tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const fiverrTab = tabs.find(t => t.type === "page" && t.url.includes("fiverr"));
  if (!fiverrTab) { console.log("No Fiverr tab"); return; }

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

  // Step 1: Navigate to login
  await send("Page.navigate", { url: "https://www.fiverr.com/login" });
  await sleep(5000);
  console.log("Step 1: On login page");

  // Step 2: Click "Continue with Google" using CDP mouse events (not JS click)
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Google'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Step 2: Google button at:", r);

  if (r === 'not found') { console.log("No Google button found"); ws.close(); return; }

  const googlePos = JSON.parse(r);
  await clickAt(googlePos.x, googlePos.y);
  console.log("Clicked Google button via CDP mouse events");

  // Step 3: Wait for Google popup to appear
  await sleep(3000);
  tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));

  if (!googleTab) {
    console.log("Waiting more for Google popup...");
    await sleep(3000);
    tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
    googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google.com"));
  }

  if (!googleTab) {
    console.log("No Google popup appeared");
    ws.close();
    return;
  }

  console.log("Step 3: Google popup found:", googleTab.url.substring(0, 80));

  // Step 4: Connect to Google popup and select weberg619
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

  r = await geval(`return document.body.innerText.substring(0, 1000)`);
  console.log("Step 4: Google popup says:", r.substring(0, 200));

  // Check if it's account chooser or consent
  if (r.includes("Choose an account")) {
    // Click weberg619
    r = await geval(`
      const items = document.querySelectorAll('[data-email="weberg619@gmail.com"]');
      if (items.length > 0) {
        items[0].click();
        return 'clicked data-email';
      }
      // Fallback: find by text
      const all = document.querySelectorAll('li, div[role="link"]');
      for (const el of all) {
        if (el.textContent.includes('weberg619')) {
          el.click();
          return 'clicked by text';
        }
      }
      return 'not found';
    `);
    console.log("Account selection:", r);
    await sleep(5000);

    // Re-read popup content (might be consent now)
    r = await geval(`return document.body.innerText.substring(0, 500)`);
    console.log("After account select:", r.substring(0, 200));
  }

  // If consent screen, click Continue
  if (r.includes("Continue") && r.includes("Fiverr")) {
    r = await geval(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Continue');
      if (btn) {
        btn.click();
        return 'clicked';
      }
      return 'not found';
    `);
    console.log("Step 5: Consent Continue:", r);
    await sleep(8000);
  }

  // Step 6: Check Fiverr page (DON'T reload it - let the popup callback do its job)
  r = await eval_(`return window.location.href`);
  console.log("\nFiverr URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 1500)`);
  console.log("Fiverr page:", r.substring(0, 500));

  const loggedIn = !r.includes("Sign in to your account");
  console.log("\nLogged in:", loggedIn);

  gws.close();
  ws.close();
})().catch(e => console.error("Error:", e.message));
