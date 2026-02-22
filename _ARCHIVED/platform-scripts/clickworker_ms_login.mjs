const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(30);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && (t.url.includes("live.com") || t.url.includes("microsoft")));
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

  // Enter email
  let r = await eval_(`
    const input = document.querySelector('#usernameEntry, input[type="email"]');
    if (!input) return 'email input not found';
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeSetter.call(input, 'cw_25671709@hotmail.com');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return 'entered: ' + input.value;
  `);
  console.log("Email:", r);
  await sleep(500);

  // Click Next
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button[type="submit"]')).find(b => b.textContent.includes('Next'));
    if (btn) { btn.click(); return 'clicked Next'; }
    return 'Next not found';
  `);
  console.log("Next:", r);
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage:", r);

  // Check for password field
  r = await eval_(`
    const inputs = document.querySelectorAll('input, button, [role="button"]');
    return JSON.stringify(Array.from(inputs).filter(i => i.offsetParent !== null).map(i => ({
      tag: i.tagName, type: i.type || '', id: i.id || '',
      text: i.textContent?.trim().substring(0, 60) || '',
      placeholder: i.placeholder?.substring(0, 40) || ''
    })).slice(0, 20));
  `);
  console.log("\nFields:", r);

  // If password field exists, enter password
  const pwField = await eval_(`
    const pw = document.querySelector('input[type="password"]');
    return pw ? 'found' : 'not found';
  `);

  if (pwField === 'found') {
    r = await eval_(`
      const input = document.querySelector('input[type="password"]');
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(input, 'Weber@619.1974');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return 'password set';
    `);
    console.log("\nPassword:", r);
    await sleep(500);

    // Click Sign in
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button[type="submit"], input[type="submit"]')).find(b =>
        (b.textContent || b.value || '').match(/sign in|next|log in/i)
      );
      if (btn) { btn.click(); return 'clicked: ' + (btn.textContent || btn.value).trim(); }
      return 'sign in button not found';
    `);
    console.log("Sign in:", r);
    await sleep(5000);

    r = await eval_(`return window.location.href`);
    console.log("\nURL:", r);
    r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nPage:", r);
  }

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_ms_login.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
