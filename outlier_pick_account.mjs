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
  let { ws, send, eval_ } = await connectToPage("accounts.google.com");

  // Click bridgeai619 account
  let r = await eval_(`
    const item = Array.from(document.querySelectorAll('li'))
      .find(el => el.textContent.includes('bridgeai619'));
    if (item) {
      const rect = item.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("bridgeai619 account:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked bridgeai619");
    await sleep(8000);

    // Check where we ended up
    ws.close();
    await sleep(1000);
    const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
    console.log("\nTabs:");
    tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url.substring(0, 120)));

    const outlierTab = tabs.find(t => t.type === "page" && t.url.includes("outlier"));
    const googleTab = tabs.find(t => t.type === "page" && t.url.includes("accounts.google"));

    const targetTab = outlierTab || googleTab;
    if (targetTab) {
      const match = targetTab.url.includes("outlier") ? "outlier" : "accounts.google";
      ({ ws, send, eval_ } = await connectToPage(match));
      r = await eval_(`return window.location.href`);
      console.log("\nURL:", r);
      r = await eval_(`return document.body.innerText.substring(0, 5000)`);
      console.log("\nPage:", r);
      ws.close();
    }
  }
})().catch(e => console.error("Error:", e.message));
