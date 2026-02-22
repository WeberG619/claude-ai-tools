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
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("microsoft") || t.url.includes("live.com")));
  if (!tab) tab = tabs.find(t => t.type === "page");
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

  // Find Cancel button
  let r = await eval_(`
    const btns = document.querySelectorAll('button, a, [role="button"]');
    return JSON.stringify(Array.from(btns).filter(b => b.offsetParent !== null || b.offsetWidth > 0).map(b => ({
      tag: b.tagName, text: b.textContent?.trim().substring(0, 40),
      id: b.id || '',
      rect: (() => { const r = b.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; })()
    })));
  `);
  console.log("Buttons:", r);

  // Click Cancel
  r = await eval_(`
    const cancel = Array.from(document.querySelectorAll('button, a, [role="button"]')).find(b =>
      b.textContent?.trim().toLowerCase() === 'cancel'
    );
    if (cancel) {
      const rect = cancel.getBoundingClientRect();
      return JSON.stringify({found: true, x: rect.x + rect.width/2, y: rect.y + rect.height/2});
    }
    return JSON.stringify({found: false});
  `);
  console.log("\nCancel:", r);

  const cancelInfo = JSON.parse(r);
  if (cancelInfo.found) {
    await clickAt(send, cancelInfo.x, cancelInfo.y);
    console.log("Clicked Cancel at", cancelInfo.x, cancelInfo.y);
  } else {
    // Try JS click
    r = await eval_(`
      const cancel = Array.from(document.querySelectorAll('button')).find(b => b.textContent?.trim() === 'Cancel');
      if (cancel) { cancel.click(); return 'JS clicked Cancel'; }
      return 'Cancel not found';
    `);
    console.log("Fallback:", r);
  }

  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Get interactive elements
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea, button, a.btn, [role="button"]');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      tag: i.tagName, type: i.type || '', id: i.id || '',
      text: i.textContent?.trim().substring(0, 60) || '',
      href: i.href || ''
    })).slice(0, 20));
  `);
  console.log("\nElements:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_ms_skip.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
