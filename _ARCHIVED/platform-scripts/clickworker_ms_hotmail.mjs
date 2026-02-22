const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("signup.live") || t.url.includes("live.com") || t.url.includes("microsoft")));
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

  // Look for "Get a new email address" link/button
  let r = await eval_(`
    const allEls = document.querySelectorAll('*');
    const found = [];
    for (const el of allEls) {
      const t = el.textContent?.trim() || '';
      if ((t.includes('new email') || t.includes('Get a new') || t.includes('hotmail') || t.includes('outlook')) && el.children.length === 0) {
        found.push({
          tag: el.tagName, id: el.id, class: el.className?.substring?.(0, 60) || '',
          text: t.substring(0, 80),
          role: el.getAttribute('role') || '',
          onclick: el.onclick ? 'yes' : ''
        });
      }
    }
    return JSON.stringify(found);
  `);
  console.log("New email elements:", r);

  // If there's a "Get a new email address" option, click it
  r = await eval_(`
    const span = Array.from(document.querySelectorAll('span[role="button"], a, button')).find(s =>
      s.textContent.toLowerCase().includes('new email') || s.textContent.toLowerCase().includes('get a new')
    );
    if (span) { span.click(); return 'clicked: ' + span.textContent.trim(); }
    return 'not found - trying to enter email directly';
  `);
  console.log("\nAction:", r);

  if (r.includes('not found')) {
    // Just enter the hotmail email directly in the email field
    r = await eval_(`
      const input = document.querySelector('#floatingLabelInput4, input[type="email"], input[name="Email"]');
      if (!input) return 'email input not found';
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(input, 'cw_25671709@hotmail.com');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return 'entered: ' + input.value;
    `);
    console.log("Email entered:", r);
    await sleep(500);

    // Click Next
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button[type="submit"]')).find(b => b.textContent.includes('Next'));
      if (btn) { btn.click(); return 'clicked Next'; }
      return 'Next not found';
    `);
    console.log("Next:", r);
  }

  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 4000)`);
  console.log("\nPage:", r);

  // Get form fields
  r = await eval_(`
    const inputs = document.querySelectorAll('input, select, textarea, button');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      tag: i.tagName, type: i.type, name: i.name || '', id: i.id || '',
      value: i.type === 'password' ? '***' : i.value?.substring(0, 60) || '',
      text: i.textContent?.trim().substring(0, 60) || '',
      placeholder: i.placeholder?.substring(0, 60) || ''
    })).slice(0, 20));
  `);
  console.log("\nForm fields:", r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_ms_hotmail.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
