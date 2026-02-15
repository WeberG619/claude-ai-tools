const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) { console.log("No Clickworker tab"); return; }

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

  // First, scroll the overflow:hidden parent to make button visible
  let r = await eval_(`
    const contentDiv = document.querySelector('.content');
    if (contentDiv) {
      // Change overflow to auto so we can scroll
      contentDiv.style.overflow = 'auto';
      contentDiv.scrollTop = contentDiv.scrollHeight;
      await new Promise(r => setTimeout(r, 300));
    }

    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Continue');
    if (btn) {
      btn.scrollIntoView({ block: 'center', behavior: 'instant' });
      await new Promise(r => setTimeout(r, 300));
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({
        rect: { x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height) },
        scrollTop: contentDiv?.scrollTop
      });
    }
    return 'not found';
  `);
  console.log("After overflow fix:", r);

  // If button is now visible, use CDP click. Otherwise use JS click.
  if (r !== 'not found') {
    const data = JSON.parse(r);
    if (data.rect.w > 0 && data.rect.h > 0 && data.rect.y > 0 && data.rect.y < 1200) {
      // Button is visible, use CDP mouse click
      const { x, y } = data.rect;
      await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(80);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
      console.log("CDP clicked at", x, y);
    } else {
      // Still not visible, use JS click
      console.log("Button still not in viewport, using JS .click()");
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim() === 'Continue');
        if (btn) { btn.click(); return 'clicked'; }
        return 'not found';
      `);
      console.log("JS click:", r);
    }
  }

  await sleep(10000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Check for errors
  r = await eval_(`
    const text = document.body.innerText;
    const lines = text.split('\\n').filter(l => l.trim().length > 0);
    return JSON.stringify(lines.filter(l =>
      l.toLowerCase().includes('error') || l.toLowerCase().includes('invalid') ||
      l.toLowerCase().includes('please') || l.toLowerCase().includes('required') ||
      l.toLowerCase().includes('taken') || l.toLowerCase().includes('already') ||
      l.toLowerCase().includes('confirm') || l.toLowerCase().includes('step 3')
    ).slice(0, 15));
  `);
  console.log("\nMessages:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
