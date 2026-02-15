// Check Freelancer dashboard for notification prompt
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected to Freelancer\n");

  // Look for notification/popup dialogs
  let r = await eval_(`
    // Check for popup/modal/dialog/notification prompt
    const modals = Array.from(document.querySelectorAll('[class*="modal"], [class*="dialog"], [class*="popup"], [class*="overlay"], [class*="notification"], [role="dialog"], [role="alertdialog"]'))
      .filter(el => el.offsetParent !== null || window.getComputedStyle(el).display !== 'none')
      .map(el => ({
        tag: el.tagName,
        class: el.className?.toString()?.substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 300),
        rect: (() => { const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; })()
      }));

    // Also check for browser notification permission prompt text
    const allText = document.body.innerText;
    const notifMatch = allText.match(/.*notification.*|.*allow.*|.*block.*|.*send.*notification.*/gi);

    return JSON.stringify({
      url: location.href,
      modals: modals,
      notifText: notifMatch?.slice(0, 5),
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("Page state:", r);

  // Look for "Allow" / "Block" notification buttons or any dismiss button
  r = await eval_(`
    // Find any buttons related to notifications
    const btns = Array.from(document.querySelectorAll('button, a, [role="button"]'))
      .filter(b => b.offsetParent !== null)
      .map(b => ({
        text: b.textContent.trim().substring(0, 60),
        tag: b.tagName,
        class: b.className?.toString()?.substring(0, 60),
        x: Math.round(b.getBoundingClientRect().x + b.getBoundingClientRect().width/2),
        y: Math.round(b.getBoundingClientRect().y + b.getBoundingClientRect().height/2)
      }))
      .filter(b => b.text.length > 0);
    return JSON.stringify(btns);
  `);
  console.log("\nAll visible buttons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
