// Click Next on Freelancer skills page, then handle whatever comes next
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found matching: ${urlMatch}`);
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
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com");
  console.log("Connected\n");

  // Get current page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      preview: document.body.innerText.substring(0, 800)
    });
  `);
  console.log("Current page:", r);

  // Find and click Next button
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim() });
    }
    // Also check for other navigation buttons
    const allBtns = Array.from(document.querySelectorAll('button, a'))
      .filter(b => b.offsetParent !== null)
      .map(b => ({ text: b.textContent.trim().substring(0, 30), tag: b.tagName }))
      .filter(b => b.text.length > 0);
    return JSON.stringify({ notFound: true, buttons: allBtns });
  `);
  console.log("Next button:", r);

  const btnInfo = JSON.parse(r);
  if (btnInfo.x) {
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: btnInfo.x, y: btnInfo.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: btnInfo.x, y: btnInfo.y, button: "left", clickCount: 1 });
    console.log("Clicked Next at", btnInfo.x, btnInfo.y);
  }

  await sleep(5000);

  // Check what page we're on now
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\nNew page state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
