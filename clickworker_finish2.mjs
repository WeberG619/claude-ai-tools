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

  // Check ALL buttons (including hidden)
  let r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    return JSON.stringify(btns.map(b => ({
      text: b.textContent.trim().substring(0, 30),
      disabled: b.disabled,
      visible: b.offsetParent !== null,
      display: window.getComputedStyle(b).display,
      rect: (() => { const r = b.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), w: Math.round(r.width), h: Math.round(r.height) }; })()
    })));
  `);
  console.log("All buttons:", r);

  // Also check for any submit inputs or anchor buttons
  r = await eval_(`
    const subs = Array.from(document.querySelectorAll('input[type="submit"], a.btn, a[class*="finish"], a[class*="Finish"]'));
    return JSON.stringify(subs.map(s => ({
      tag: s.tagName, text: (s.textContent?.trim() || s.value || '').substring(0, 30),
      class: (typeof s.className === 'string' ? s.className : '').substring(0, 60),
      href: s.href?.substring(0, 60) || '',
      visible: s.offsetParent !== null
    })));
  `);
  console.log("\nSubmit/anchor:", r);

  // The Finish button exists but is hidden. Let me find it and check its state after checkbox
  r = await eval_(`
    // Make sure checkbox is checked
    const cb = document.querySelector('#mobile_app_installed');
    if (cb && !cb.checked) cb.click();

    // Find finish button
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Finish'));
    if (!btn) return 'no finish button';

    return JSON.stringify({
      text: btn.textContent.trim(),
      disabled: btn.disabled,
      type: btn.type,
      class: btn.className?.substring(0, 60),
      parentClass: btn.parentElement?.className?.substring(0, 60),
      parentDisplay: window.getComputedStyle(btn.parentElement).display,
      parentVisibility: window.getComputedStyle(btn.parentElement).visibility,
      grandparentClass: btn.parentElement?.parentElement?.className?.substring(0, 60)
    });
  `);
  console.log("\nFinish button details:", r);

  // Try to make it visible by fixing the overflow and scrolling, then click
  r = await eval_(`
    // Fix overflow on all ancestors
    let el = document.querySelector('.content');
    while (el) {
      const s = window.getComputedStyle(el);
      if (s.overflow === 'hidden' || s.overflowY === 'hidden') {
        el.style.overflow = 'auto';
      }
      el = el.parentElement;
    }

    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Finish'));
    if (!btn) return 'no button';

    // Make sure parent is visible
    let p = btn.parentElement;
    while (p) {
      const s = window.getComputedStyle(p);
      if (s.display === 'none') p.style.display = 'block';
      p = p.parentElement;
    }

    btn.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(r => setTimeout(r, 500));
    const rect = btn.getBoundingClientRect();
    return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width), h: Math.round(rect.height), disabled: btn.disabled });
  `);
  console.log("\nFinish after fix:", r);

  if (r !== 'no button') {
    const pos = JSON.parse(r);
    if (pos.w > 0 && pos.h > 0 && pos.y > 0 && pos.y < 1200 && !pos.disabled) {
      await clickAt(send, pos.x, pos.y);
      console.log("CDP clicked Finish at", pos.x, pos.y);
    } else if (!pos.disabled) {
      // JS click
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim().includes('Finish'));
        if (btn) { btn.click(); return 'clicked'; }
        return 'not found';
      `);
      console.log("JS click Finish:", r);
    } else {
      console.log("Finish still disabled");
    }

    await sleep(10000);

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
