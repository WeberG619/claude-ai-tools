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

  let r = await eval_(`return window.location.href`);
  console.log("URL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 2000)`);
  console.log("\nPage:", r);

  // Look for Cancel button (input#idBtn_Back)
  r = await eval_(`
    const btn = document.querySelector('#idBtn_Back');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({value: btn.value, x: rect.x + rect.width/2, y: rect.y + rect.height/2, w: rect.width, h: rect.height});
    }
    return 'not found';
  `);
  console.log("\nCancel btn:", r);

  if (r !== 'not found') {
    const info = JSON.parse(r);
    console.log("Clicking Cancel at", info.x, info.y);
    // Try JS click first
    r = await eval_(`
      const btn = document.querySelector('#idBtn_Back');
      btn.click();
      return 'JS clicked Cancel';
    `);
    console.log(r);
    await sleep(5000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL after:", r);
    r = await eval_(`return document.body.innerText.substring(0, 2000)`);
    console.log("\nPage after:", r);
  }

  // Check for "Stay signed in?" or permission grant pages
  r = await eval_(`
    const allBtns = document.querySelectorAll('input[type="button"], input[type="submit"], button');
    return JSON.stringify(Array.from(allBtns).filter(b => b.offsetParent !== null).map(b => ({
      tag: b.tagName, type: b.type, id: b.id,
      value: b.value?.substring(0, 40) || '',
      text: b.textContent?.trim().substring(0, 40) || ''
    })));
  `);
  console.log("\nAll buttons:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_ms_after.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
