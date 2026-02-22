// Create Upwork account with weber@bimopsstudio.com
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found matching: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(() => { ${expr} })()`,
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

async function main() {
  // Navigate to Upwork signup fresh
  let { ws, send, eval_ } = await connectToPage("mail.google.com");
  console.log("Connected");

  await eval_(`window.location.href = 'https://www.upwork.com/nx/signup/?dest=home'`);
  await sleep(8000);
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: document.body.innerText.substring(0, 400)
    });
  `);
  console.log("Page:", r);
  const page = JSON.parse(r);

  // Check if we're already logged in or on verification page
  if (page.url.includes('please-verify') || page.body.includes('Verify')) {
    console.log("Still on verify page from old account. Let me log out first...");
    // Try to find logout
    await eval_(`window.location.href = 'https://www.upwork.com/ab/account-security/logout'`);
    await sleep(5000);
    ws.close();
    await sleep(1000);

    // Navigate to signup
    const tabsRes = await fetch(`${CDP_HTTP}/json`);
    const tabs = await tabsRes.json();
    const upTab = tabs.find(t => t.type === "page" && t.url.includes("upwork"));
    if (upTab) {
      const ws2 = new WebSocket(upTab.webSocketDebuggerUrl);
      await new Promise((res, rej) => { ws2.addEventListener("open", res); ws2.addEventListener("error", rej); });
      const pending2 = new Map();
      let id2 = 1;
      ws2.addEventListener("message", (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && pending2.has(msg.id)) {
          const p = pending2.get(msg.id);
          pending2.delete(msg.id);
          if (msg.error) p.rej(new Error(msg.error.message));
          else p.res(msg.result);
        }
      });
      const send2 = (method, params = {}) => new Promise((res, rej) => {
        const msgId = id2++;
        pending2.set(msgId, { res, rej });
        ws2.send(JSON.stringify({ id: msgId, method, params }));
      });
      const eval2 = async (expr) => {
        const r = await send2("Runtime.evaluate", {
          expression: `(() => { ${expr} })()`,
          returnByValue: true, awaitPromise: true
        });
        if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
        return r.result?.value;
      };

      r = await eval2(`return location.href`);
      console.log("After logout:", r);

      await eval2(`window.location.href = 'https://www.upwork.com/nx/signup/?dest=home'`);
      await sleep(5000);
      ws2.close();
      await sleep(1000);
    }

    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: document.body.innerText.substring(0, 400)
    });
  `);
  console.log("Signup page:", r);

  // Check if signup form is visible
  if (r.includes('freelancer') || r.includes('client')) {
    // Select freelancer
    r = await eval_(`
      const freelancerDiv = Array.from(document.querySelectorAll('div'))
        .find(el => el.textContent.trim() === "I'm a freelancer, looking for work"
          && el.offsetParent !== null && el.getBoundingClientRect().width > 50);
      if (freelancerDiv) {
        const rect = freelancerDiv.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    console.log("Freelancer option:", r);
    const fl = JSON.parse(r);
    if (!fl.error) {
      await clickAt(send, fl.x, fl.y);
      await sleep(500);
    }

    // Click Apply as Freelancer / Create Account
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Apply') || b.textContent.trim().includes('Create Account'));
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ text: btn.textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no button' });
    `);
    console.log("Submit button:", r);
    const btn = JSON.parse(r);
    if (!btn.error) {
      await clickAt(send, btn.x, btn.y);
      await sleep(5000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));
    }
  }

  // Now fill the form
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        id: el.id,
        type: el.type,
        placeholder: el.placeholder,
        label: el.labels?.[0]?.textContent?.trim() || ''
      }));
    return JSON.stringify(inputs);
  `);
  console.log("\nForm inputs:", r);

  // Fill form fields
  const fields = [
    { sel: '#first-name-input', val: 'Weber' },
    { sel: '#last-name-input', val: 'Gouin' },
    { sel: '#redesigned-input-email', val: 'weber@bimopsstudio.com' },
    { sel: '#password-input', val: 'W3ber!Upwork2026' }
  ];

  for (const field of fields) {
    r = await eval_(`
      const el = document.querySelector('${field.sel}');
      if (el) {
        el.scrollIntoView({ block: 'center' });
        el.focus();
        const rect = el.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found: ${field.sel}' });
    `);
    const pos = JSON.parse(r);
    if (pos.error) { console.log(pos.error); continue; }

    await clickAt(send, pos.x, pos.y);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    const displayVal = field.sel.includes('password') ? '***' : field.val;
    await send("Input.insertText", { text: field.val });
    await sleep(300);
    console.log(`${field.sel}: ${displayVal}`);
  }

  // Accept terms
  r = await eval_(`
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null);
    const results = [];
    for (const cb of cbs) {
      const label = cb.labels?.[0]?.textContent?.trim()?.substring(0, 50) || '';
      if (!cb.checked) {
        results.push({ label, x: Math.round(cb.getBoundingClientRect().x + 10), y: Math.round(cb.getBoundingClientRect().y + 10), checked: false });
      } else {
        results.push({ label, checked: true });
      }
    }
    return JSON.stringify(results);
  `);
  console.log("Checkboxes:", r);
  const cbs = JSON.parse(r);
  for (const cb of cbs) {
    if (!cb.checked) {
      await clickAt(send, cb.x, cb.y);
      await sleep(300);
      console.log(`Checked: ${cb.label}`);
    }
  }

  // Submit
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Create my account'));
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const submitBtn = JSON.parse(r);

  if (!submitBtn.error) {
    await sleep(500);
    console.log(`\nSubmitting at (${submitBtn.x}, ${submitBtn.y})`);
    await clickAt(send, submitBtn.x, submitBtn.y);
    await sleep(10000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        title: document.title,
        body: document.body.innerText.substring(0, 500)
      });
    `);
    console.log("After submit:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
