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

  // Get details about the input buttons
  let r = await eval_(`
    const back = document.querySelector('#idBtn_Back');
    const next = document.querySelector('#idSIButton9');
    const results = {};
    if (back) {
      const rect = back.getBoundingClientRect();
      results.back = {value: back.value, type: back.type, x: rect.x + rect.width/2, y: rect.y + rect.height/2, w: rect.width, h: rect.height};
    }
    if (next) {
      const rect = next.getBoundingClientRect();
      results.next = {value: next.value, type: next.type, x: rect.x + rect.width/2, y: rect.y + rect.height/2, w: rect.width, h: rect.height};
    }
    return JSON.stringify(results);
  `);
  console.log("Buttons:", r);

  const btns = JSON.parse(r);

  // Click the Back/Cancel button
  if (btns.back) {
    console.log("Clicking Back/Cancel at", btns.back.x, btns.back.y, "value:", btns.back.value);
    await clickAt(send, btns.back.x, btns.back.y);
  } else {
    // Try clicking by ID directly
    r = await eval_(`
      const btn = document.querySelector('#idBtn_Back');
      if (btn) { btn.click(); return 'clicked #idBtn_Back'; }
      return 'not found';
    `);
    console.log("Fallback:", r);
  }

  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_ms_cancel.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
