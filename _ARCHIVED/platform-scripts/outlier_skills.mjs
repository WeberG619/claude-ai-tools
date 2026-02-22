const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Try clicking "Import and Review" directly
  await clickAt(send, 828, 782);
  console.log("Clicked Import and Review");
  await sleep(3000);

  // Check what happened
  let r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);

  r = await eval_(`return document.body.innerText.substring(0, 5000)`);
  console.log("\nPage:");
  console.log(r);

  // If still on same page, we probably need LinkedIn or resume
  // Check for error messages
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="alert"], [class*="warning"], [role="alert"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim());
    return JSON.stringify(errors);
  `);
  console.log("\nErrors:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
