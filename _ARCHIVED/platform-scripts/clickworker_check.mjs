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

  // Scroll the .content div to show the form area
  let r = await eval_(`
    const contentDiv = document.querySelector('.content');
    if (contentDiv) {
      contentDiv.style.overflow = 'auto';
      contentDiv.scrollTop = 600;
      await new Promise(r => setTimeout(r, 300));
    }
    return 'scrolled';
  `);
  console.log("Scroll:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("Screenshot saved");

  // Check active step
  r = await eval_(`
    const steps = document.querySelectorAll('[class*="step"], [class*="Step"], .active, .current');
    return JSON.stringify(Array.from(steps).map(s => ({
      tag: s.tagName,
      class: (typeof s.className === 'string' ? s.className : '').substring(0, 60),
      text: s.textContent?.trim().substring(0, 50)
    })).slice(0, 20));
  `);
  console.log("\nStep indicators:", r);

  // All visible form fields
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea');
    return JSON.stringify(Array.from(inputs).map(i => ({
      type: i.type, name: i.name, id: i.id,
      value: i.type === 'password' ? '***' : i.value?.substring(0, 30),
      checked: i.type === 'checkbox' ? i.checked : undefined,
      visible: i.offsetParent !== null
    })).filter(i => i.visible));
  `);
  console.log("\nVisible fields:", r);

  // All checkboxes
  r = await eval_(`
    const cbs = document.querySelectorAll('input[type="checkbox"]');
    return JSON.stringify(Array.from(cbs).map(cb => ({
      name: cb.name, id: cb.id, checked: cb.checked,
      label: cb.closest('label')?.textContent?.trim().substring(0, 80) || cb.parentElement?.textContent?.trim().substring(0, 80) || 'no label',
      visible: cb.offsetParent !== null
    })));
  `);
  console.log("\nCheckboxes:", r);

  // Validation errors
  r = await eval_(`
    const els = document.querySelectorAll('[class*="error"], [class*="alert"], [class*="warning"], .help-block, .field_with_errors');
    return JSON.stringify(Array.from(els).filter(e => e.offsetParent !== null && e.textContent.trim().length > 0).map(e => e.textContent.trim().substring(0, 100)));
  `);
  console.log("\nErrors:", r);

  // Buttons
  r = await eval_(`
    const btns = document.querySelectorAll('button, input[type="submit"]');
    return JSON.stringify(Array.from(btns).map(b => ({
      text: (b.textContent?.trim() || b.value || '').substring(0, 40),
      disabled: b.disabled, visible: b.offsetParent !== null
    })));
  `);
  console.log("\nButtons:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
