const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(30);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("mail.google"));
  if (!tab) { console.log("No Gmail tab"); return; }

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

  // Click on the email row
  let r = await eval_(`
    const rows = document.querySelectorAll('tr');
    for (const row of rows) {
      if (row.textContent.includes('clickworker') && row.textContent.includes('activate')) {
        const rect = row.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
    }
    return 'not found';
  `);
  console.log("Email row:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    await clickAt(send, pos.x, pos.y);
    console.log("Clicked email");
    await sleep(3000);

    // Now find the activation link in the email body
    r = await eval_(`
      const links = document.querySelectorAll('a[href]');
      const activateLinks = Array.from(links).filter(a =>
        a.href.includes('activate') || a.href.includes('confirm') ||
        (a.href.includes('clickworker') && a.href.includes('token'))
      );
      return JSON.stringify(activateLinks.map(a => ({ text: a.textContent.trim().substring(0, 50), href: a.href })));
    `);
    console.log("\nActivation links:", r);

    // Get the page text to find the link
    r = await eval_(`
      const body = document.body.innerText;
      // Find lines with activate or link
      const lines = body.split('\\n').filter(l => l.includes('activate') || l.includes('click') || l.includes('http'));
      return lines.join('\\n').substring(0, 1000);
    `);
    console.log("\nRelevant text:", r);

    // Screenshot
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const fs = await import('fs');
    fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
    console.log("\nScreenshot saved");
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
