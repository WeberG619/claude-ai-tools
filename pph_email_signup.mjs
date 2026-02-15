// PeoplePerHour - select freelancer, sign up with email
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PASS = process.argv[2];

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("peopleperhour.com/site/register");
  console.log("Connected to PPH\n");

  // Step 1: Click "I want to work as a freelancer" radio
  console.log("Selecting freelancer...");
  let r = await eval_(`
    const radio = document.getElementById('provider');
    if (radio) {
      const label = radio.labels?.[0] || radio.parentElement;
      const rect = label.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("  Clicked freelancer radio");
    await sleep(500);
  }

  // Step 2: Click "Sign up with email"
  console.log("\nClicking 'Sign up with email'...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.toLowerCase().includes('sign up with email') && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim() });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("  Clicked:", pos.text);
    await sleep(3000);
  }

  // Step 3: Check what form appeared
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 2000),
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => (i.offsetParent !== null || i.closest('form')) && i.type !== 'hidden' && !i.name?.includes('recaptcha') && i.type !== 'radio')
        .map(i => ({
          type: i.type, name: i.name, id: i.id,
          placeholder: i.placeholder,
          label: (i.labels?.[0]?.textContent || '').trim().substring(0, 50)
        })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ text: b.textContent.trim().substring(0, 60), type: b.type }))
        .filter(b => b.text.length > 0)
    });
  `);
  console.log("\nForm state:", r);

  const state = JSON.parse(r);

  // Fill in the form fields
  for (const input of state.inputs) {
    const nameLower = (input.name || input.id || input.placeholder || input.label || "").toLowerCase();
    let value = null;

    if (input.type === 'email' || nameLower.includes('email')) {
      value = 'weberg619@gmail.com';
    } else if (input.type === 'password' || nameLower.includes('password')) {
      value = PASS;
    } else if ((nameLower.includes('first') || nameLower.includes('fname')) && !nameLower.includes('last')) {
      value = 'Weber';
    } else if (nameLower.includes('last') || nameLower.includes('lname') || nameLower.includes('surname')) {
      value = 'Gouin';
    } else if (nameLower.includes('user') || nameLower.includes('display')) {
      value = 'BIMOpsStudio';
    } else if (nameLower === 'name' || input.placeholder?.toLowerCase() === 'name' || input.label?.toLowerCase() === 'name') {
      value = 'Weber Gouin';
    }

    if (value) {
      const selector = input.id ? `#${input.id}` :
                       input.name ? `input[name="${input.name}"]` :
                       `input[placeholder="${input.placeholder}"]`;

      console.log(`\nFilling ${input.name || input.id || input.placeholder || input.type}: "${value.substring(0, 20)}${value.length > 20 ? '...' : ''}"`);

      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) { el.focus(); el.click(); }
      `);
      await sleep(200);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(50);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
      await sleep(100);
      await send("Input.insertText", { text: value });
      await sleep(300);
    }
  }

  // Check for TOS/agreement checkbox
  r = await eval_(`
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
    return JSON.stringify(cbs.map(c => ({
      id: c.id, name: c.name, checked: c.checked,
      label: (c.labels?.[0]?.textContent || c.parentElement?.textContent || '').trim().substring(0, 100)
    })));
  `);
  console.log("\nCheckboxes:", r);
  const cbs = JSON.parse(r);
  for (const cb of cbs) {
    if (!cb.checked) {
      const selector = cb.id ? `#${cb.id}` : `input[name="${cb.name}"]`;
      r = await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) {
          const target = el.labels?.[0] || el.parentElement || el;
          target.click();
          return 'checked: ' + ${JSON.stringify(cb.label?.substring(0, 50))};
        }
        return 'not found';
      `);
      console.log("  Checkbox:", r);
      await sleep(200);
    }
  }

  // Find and click submit
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, input[type="submit"]'))
      .filter(b => b.offsetParent !== null)
      .map(b => ({
        text: (b.textContent || b.value || '').trim().substring(0, 60),
        tag: b.tagName, type: b.type,
        x: Math.round(b.getBoundingClientRect().x + b.getBoundingClientRect().width/2),
        y: Math.round(b.getBoundingClientRect().y + b.getBoundingClientRect().height/2)
      }))
      .filter(b => b.text.length > 0);
    return JSON.stringify(btns);
  `);
  console.log("\nButtons:", r);

  const buttons = JSON.parse(r);
  const submitBtn = buttons.find(b =>
    b.text.toLowerCase().includes('sign up') ||
    b.text.toLowerCase().includes('register') ||
    b.text.toLowerCase().includes('create') ||
    b.text.toLowerCase().includes('join') ||
    b.type === 'submit'
  );

  if (submitBtn) {
    console.log(`\nClicking submit: "${submitBtn.text}"...`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: submitBtn.x, y: submitBtn.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: submitBtn.x, y: submitBtn.y, button: "left", clickCount: 1 });
    await sleep(8000);

    // Check result
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 1500),
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [class*="alert"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 100))
          .filter(t => t.length > 3)
      });
    `);
    console.log("\nResult:", r);
  } else {
    console.log("\nNo submit button found. Manual submission needed.");
  }

  // Final form state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null && i.type !== 'hidden')
        .map(i => ({ name: i.name || i.id || i.type, value: i.type === 'password' ? '***' : i.value?.substring(0, 30) }))
    });
  `);
  console.log("\nFinal:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
