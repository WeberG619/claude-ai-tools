const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
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
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  let { ws, send, eval_ } = await connectToPage("fiverr");

  // Navigate to Fiverr login page first
  await send("Page.navigate", { url: "https://www.fiverr.com/login" });
  await sleep(5000);

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 2000)`);
  console.log("\nPage:", r);

  // Check if already logged in (redirected to dashboard)
  if (r.includes("Dashboard") || r.includes("weberg619") || !r.includes("Sign in") && !r.includes("Log in")) {
    console.log("\nAlready logged in! Navigating to profile...");
    await send("Page.navigate", { url: "https://www.fiverr.com/seller_dashboard/profile" });
    await sleep(5000);
    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nPage:", r);
  } else {
    // Look for Google sign-in or email login
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button, a'));
      return JSON.stringify(btns.filter(b => b.offsetParent !== null).map(b => ({
        tag: b.tagName,
        text: b.textContent.trim().substring(0, 50),
        href: b.href?.substring(0, 80) || ''
      })).filter(b => b.text.includes('Google') || b.text.includes('Continue') || b.text.includes('Sign') || b.text.includes('Log')));
    `);
    console.log("\nLogin options:", r);

    // Try Continue with Google
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button, a'))
        .find(b => b.textContent.includes('Google'));
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return 'not found';
    `);
    console.log("\nGoogle button:", r);

    if (r !== 'not found') {
      const pos = JSON.parse(r);
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked Google sign-in");
      await sleep(8000);
      r = await eval_(`return window.location.href`);
      console.log("\nURL after Google:", r);
      r = await eval_(`return document.body.innerText.substring(0, 2000)`);
      console.log("\nPage:", r);
    }
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
