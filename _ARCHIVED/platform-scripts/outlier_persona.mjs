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
  let { ws, send, eval_ } = await connectToPage("outlier");

  // Find the Persona iframe position
  let r = await eval_(`
    const iframes = document.querySelectorAll('iframe');
    const results = [];
    for (const f of iframes) {
      if (f.src && f.src.includes('persona')) {
        const rect = f.getBoundingClientRect();
        // Also check parent/container positioning
        const parent = f.parentElement;
        const parentRect = parent ? parent.getBoundingClientRect() : null;
        results.push({
          src: f.src.substring(0, 80),
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          w: Math.round(rect.width),
          h: Math.round(rect.height),
          display: window.getComputedStyle(f).display,
          visibility: window.getComputedStyle(f).visibility,
          opacity: window.getComputedStyle(f).opacity,
          parentTag: parent?.tagName,
          parentDisplay: parent ? window.getComputedStyle(parent).display : null,
          parentRect: parentRect ? { x: Math.round(parentRect.x), y: Math.round(parentRect.y), w: Math.round(parentRect.width), h: Math.round(parentRect.height) } : null
        });
      }
    }
    return JSON.stringify(results);
  `);
  console.log("Persona iframe:", r);

  // Also check if there's a modal or overlay
  r = await eval_(`
    const overlays = document.querySelectorAll('[class*="modal"], [class*="Modal"], [class*="overlay"], [class*="Overlay"], [class*="dialog"], [class*="Dialog"], [class*="persona"], [class*="Persona"]');
    return JSON.stringify(Array.from(overlays).map(el => {
      const rect = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        id: el.id?.substring(0, 40),
        classes: (typeof el.className === 'string' ? el.className : '').substring(0, 60),
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        w: Math.round(rect.width),
        h: Math.round(rect.height),
        display: window.getComputedStyle(el).display,
        visibility: window.getComputedStyle(el).visibility
      };
    }));
  `);
  console.log("\nOverlays/modals:", r);

  // Take a screenshot to see what's on screen
  const screenshot = await send("Page.captureScreenshot", { format: "png", quality: 50 });
  const fs = await import('fs');
  fs.writeFileSync('/mnt/d/_CLAUDE-TOOLS/outlier_screen.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved to /mnt/d/_CLAUDE-TOOLS/outlier_screen.png");

  ws.close();
})().catch(e => console.error("Error:", e.message));
