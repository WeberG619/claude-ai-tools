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

  // Check jQuery event handlers on submit and form
  let r = await eval_(`
    const form = document.querySelector('#registration_form');
    const submit = document.querySelector('input[type="submit"]');

    // Get jQuery events
    let formEvents = [];
    let submitEvents = [];
    try {
      if (typeof jQuery !== 'undefined') {
        const fEvents = jQuery._data(form, 'events');
        if (fEvents) {
          for (const [type, handlers] of Object.entries(fEvents)) {
            formEvents.push({ type, count: handlers.length, handlers: handlers.map(h => h.handler?.toString()?.substring(0, 150)) });
          }
        }
        const sEvents = jQuery._data(submit, 'events');
        if (sEvents) {
          for (const [type, handlers] of Object.entries(sEvents)) {
            submitEvents.push({ type, count: handlers.length, handlers: handlers.map(h => h.handler?.toString()?.substring(0, 150)) });
          }
        }
      }
    } catch(e) {
      return 'jQuery events error: ' + e.message;
    }

    return JSON.stringify({ formEvents, submitEvents }, null, 2);
  `);
  console.log("jQuery events:", r);

  // Check for click handlers on the step 3 wizard container/buttons
  r = await eval_(`
    // Check the step 3 panel/container
    const submit = document.querySelector('input[type="submit"]');
    const container = submit?.closest('[class*="step"], [class*="tab"], [class*="panel"]');
    let containerEvents = [];
    if (container && typeof jQuery !== 'undefined') {
      try {
        const cEvents = jQuery._data(container, 'events');
        if (cEvents) {
          for (const [type, handlers] of Object.entries(cEvents)) {
            containerEvents.push({ type, count: handlers.length });
          }
        }
      } catch(e) {}
    }

    // Check for delegated events on document
    let docEvents = [];
    try {
      const dEvents = jQuery._data(document, 'events');
      if (dEvents) {
        for (const [type, handlers] of Object.entries(dEvents)) {
          const relevant = handlers.filter(h => {
            const s = h.handler?.toString() || '';
            return s.includes('submit') || s.includes('finish') || s.includes('Finish') || s.includes('registration') || s.includes('step');
          });
          if (relevant.length > 0) {
            docEvents.push({ type, count: relevant.length, selectors: relevant.map(h => h.selector).filter(Boolean) });
          }
        }
      }
    } catch(e) {}

    return JSON.stringify({ containerClass: container?.className?.substring(0, 60), containerEvents, docEvents }, null, 2);
  `);
  console.log("\nContainer/doc events:", r);

  // Approach: focus the submit and press Enter via CDP
  r = await eval_(`
    const submit = document.querySelector('input[type="submit"]');
    submit.focus();
    return 'focused: ' + (document.activeElement === submit);
  `);
  console.log("\nFocus:", r);
  await sleep(200);

  // Press Enter via CDP
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  console.log("Pressed Enter");

  await sleep(10000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_state.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
