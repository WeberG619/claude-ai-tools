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

  // Click both checkboxes
  let r = await eval_(`
    const checkboxes = document.querySelectorAll('input[type="checkbox"], [role="checkbox"]');
    const results = [];
    for (const cb of checkboxes) {
      if (cb.offsetParent !== null || cb.closest('[role="checkbox"]')) {
        cb.click();
        results.push('clicked checkbox');
      }
    }
    // Also try clicking label/div elements that look like checkboxes
    const divCbs = document.querySelectorAll('[role="checkbox"], button[role="checkbox"]');
    for (const cb of divCbs) {
      cb.click();
      results.push('clicked role=checkbox');
    }
    return JSON.stringify(results);
  `);
  console.log("Checkboxes:", r);
  await sleep(500);

  // Try clicking the checkbox areas by finding them near the consent text
  r = await eval_(`
    // Find elements containing the consent text
    const allEls = document.querySelectorAll('*');
    const results = [];
    for (const el of allEls) {
      if (el.children.length === 0) {
        const text = el.textContent.trim();
        if (text.includes('I confirm that I am 18') || text.includes('I agree that my face')) {
          // Find nearby checkbox or clickable parent
          const parent = el.closest('label, button, div[role="checkbox"], [class*="check"]');
          if (parent) {
            const rect = parent.getBoundingClientRect();
            results.push({ text: text.substring(0, 40), x: Math.round(rect.x + 10), y: Math.round(rect.y + rect.height/2) });
          } else {
            const rect = el.getBoundingClientRect();
            results.push({ text: text.substring(0, 40), x: Math.round(rect.x - 20), y: Math.round(rect.y + rect.height/2) });
          }
        }
      }
    }
    return JSON.stringify(results);
  `);
  console.log("Consent items:", r);

  const items = JSON.parse(r);
  for (const item of items) {
    await clickAt(send, item.x, item.y);
    console.log("Clicked near:", item.text);
    await sleep(300);
  }

  await sleep(500);

  // Check Next button state
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Next'));
    if (btn) return JSON.stringify({ disabled: btn.disabled });
    return 'not found';
  `);
  console.log("\nNext button:", r);

  // If still disabled, try finding checkboxes differently
  const nextInfo = JSON.parse(r !== 'not found' ? r : '{"disabled":true}');
  if (nextInfo.disabled) {
    // Try finding any unchecked checkboxes by looking at all interactive elements
    r = await eval_(`
      const els = document.querySelectorAll('button, [role="switch"], [role="checkbox"], input[type="checkbox"], [class*="checkbox"], [class*="Checkbox"]');
      return JSON.stringify(Array.from(els).map(el => ({
        tag: el.tagName,
        role: el.getAttribute('role'),
        checked: el.checked || el.getAttribute('aria-checked'),
        classes: el.className?.substring(0, 80),
        text: el.textContent?.trim().substring(0, 40)
      })));
    `);
    console.log("\nAll checkbox-like elements:", r);
  }

  // Click Next if enabled
  if (!nextInfo.disabled) {
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Next'));
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return 'not found';
    `);
    if (r !== 'not found') {
      const pos = JSON.parse(r);
      await clickAt(send, pos.x, pos.y);
      console.log("Clicked Next");
      await sleep(5000);
      r = await eval_(`return window.location.href`);
      console.log("\nURL:", r);
      r = await eval_(`return document.body.innerText.substring(0, 3000)`);
      console.log("\nPage:", r);
    }
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
