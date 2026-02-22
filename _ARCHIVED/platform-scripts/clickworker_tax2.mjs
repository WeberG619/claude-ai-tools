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
  let tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No tab"); return; }

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

  // Navigate to payment details
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/payment_details" });
  await sleep(4000);

  // Click "Add now" for SSN section
  let r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    // Get all "Add now" links with their context
    return JSON.stringify(links.filter(a => a.textContent.trim().includes('Add now')).map(a => ({
      text: a.textContent.trim(),
      href: a.href,
      context: a.closest('div, section, tr, li')?.textContent?.trim().substring(0, 80) || ''
    })));
  `);
  console.log("Add now links:", r);

  // Click the SSN "Add now"
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'));
    const ssnLink = links.find(a => {
      const context = a.closest('div, section, tr, li')?.textContent || '';
      return a.textContent.trim().includes('Add now') && context.includes('Social Security');
    });
    if (ssnLink) { ssnLink.click(); return 'clicked SSN add'; }
    return 'not found';
  `);
  console.log("\nSSN link:", r);
  await sleep(3000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage:", r);

  // Check form
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      tag: i.tagName, type: i.type, name: i.name, id: i.id,
      placeholder: i.placeholder?.substring(0, 50) || '',
      label: i.labels?.[0]?.textContent?.trim().substring(0, 60) || ''
    })).slice(0, 20));
  `);
  console.log("\nForm:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\fiverr_newgig.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
