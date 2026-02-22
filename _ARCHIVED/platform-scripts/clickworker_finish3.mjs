const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

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

  // Ensure checkbox is checked
  let r = await eval_(`
    const cb = document.querySelector('#mobile_app_installed');
    if (cb && !cb.checked) cb.click();
    return 'checkbox: ' + (cb?.checked || 'not found');
  `);
  console.log(r);
  await sleep(200);

  // Find the Finish input submit button
  r = await eval_(`
    const btn = document.querySelector('input[type="submit"]');
    if (btn) {
      btn.scrollIntoView({ block: 'center', behavior: 'instant' });
      await new Promise(r => setTimeout(r, 300));
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({
        value: btn.value,
        disabled: btn.disabled,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width),
        h: Math.round(rect.height)
      });
    }
    return 'not found';
  `);
  console.log("Finish button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    if (pos.w > 0 && pos.y > 0 && pos.y < 1200) {
      await clickAt(send, pos.x, pos.y);
      console.log("CDP clicked Finish at", pos.x, pos.y);
    } else {
      // JS click fallback
      r = await eval_(`
        const btn = document.querySelector('input[type="submit"]');
        if (btn) { btn.click(); return 'clicked'; }
        return 'not found';
      `);
      console.log("JS click:", r);
    }

    await sleep(12000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 4000)`);
    console.log("\nPage:", r);
  }

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
