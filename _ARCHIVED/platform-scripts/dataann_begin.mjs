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
  let { ws, send, eval_ } = await connectToPage("app.dataannotation");

  // First dismiss the phone verification banner
  let r = await eval_(`
    const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === '×');
    if (closeBtn) { closeBtn.click(); return 'dismissed'; }
    return 'no banner';
  `);
  console.log("Banner:", r);
  await sleep(500);

  // Scroll the Programming Projects button into view and get exact position of "Begin This Starter Assessment" text
  r = await eval_(`
    const allBtns = Array.from(document.querySelectorAll('button'));
    const beginBtn = allBtns.find(b => b.textContent.includes('Begin This Starter Assessment'));
    if (beginBtn) {
      beginBtn.scrollIntoView({ behavior: 'instant', block: 'center' });
      await new Promise(r => setTimeout(r, 300));
      const rect = beginBtn.getBoundingClientRect();
      // Find the inner "Begin" text span
      const spans = beginBtn.querySelectorAll('*');
      for (const span of spans) {
        if (span.textContent.trim() === 'Begin This Starter Assessment' && span.children.length === 0) {
          const sr = span.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(sr.x + sr.width/2), y: Math.round(sr.y + sr.height/2), tag: span.tagName, btnRect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height } });
        }
      }
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height - 20), tag: 'button', btnRect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height } });
    }
    return 'not found';
  `);
  console.log("Begin button:", r);

  if (r !== 'not found') {
    const info = JSON.parse(r);
    console.log("Clicking at:", info.x, info.y);
    await clickAt(send, info.x, info.y);
    console.log("Clicked");
    await sleep(1000);

    // Try JS click as fallback
    r = await eval_(`
      const allBtns = Array.from(document.querySelectorAll('button'));
      const beginBtn = allBtns.find(b => b.textContent.includes('Begin This Starter Assessment'));
      if (beginBtn) {
        beginBtn.click();
        return 'JS clicked';
      }
      return 'not found';
    `);
    console.log("JS click:", r);
    await sleep(5000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 6000)`);
    console.log("\nPage:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
