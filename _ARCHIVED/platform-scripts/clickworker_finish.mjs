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

  // 1. Check the mobile app checkbox
  let r = await eval_(`
    const cb = document.querySelector('#mobile_app_installed');
    if (cb && !cb.checked) {
      cb.click();
      return 'checked: ' + cb.checked;
    }
    return cb ? 'already checked: ' + cb.checked : 'not found';
  `);
  console.log("Mobile app checkbox:", r);
  await sleep(300);

  // 2. Find and click the Finish button
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(b => b.offsetParent !== null);
    return JSON.stringify(btns.map(b => ({
      text: b.textContent.trim().substring(0, 30),
      disabled: b.disabled,
      rect: (() => { const r = b.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
    })));
  `);
  console.log("Buttons:", r);

  // Click Finish
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .filter(b => b.offsetParent !== null)
      .find(b => b.textContent.trim() === 'Finish' || b.textContent.trim().includes('Finish'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btn.disabled });
    }
    return 'not found';
  `);
  console.log("\nFinish button:", r);

  if (r !== 'not found') {
    const pos = JSON.parse(r);
    if (!pos.disabled) {
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked Finish at", pos.x, pos.y);
    } else {
      console.log("Finish button is disabled!");
    }

    await sleep(10000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 4000)`);
    console.log("\nPage:", r);

    // Screenshot
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const fs = await import('fs');
    fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
    console.log("\nScreenshot saved");
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
