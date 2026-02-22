// Sign up on PeoplePerHour
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
  let { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected to PeoplePerHour\n");

  // Check page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 3000),
      inputs: Array.from(document.querySelectorAll('input, select, textarea'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ tag: i.tagName, type: i.type, name: i.name, id: i.id, placeholder: i.placeholder })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ text: b.textContent.trim().substring(0, 60), type: b.type }))
        .filter(b => b.text.length > 0)
    });
  `);
  console.log("Page state:", r);

  const state = JSON.parse(r);

  // Fill form fields
  for (const input of state.inputs) {
    const selector = input.id ? `#${input.id}` :
                     input.name ? `input[name="${input.name}"]` :
                     `input[type="${input.type}"]`;

    let value = null;
    const nameLower = (input.name || input.placeholder || input.id || "").toLowerCase();

    if (input.type === "email" || nameLower.includes("email")) {
      value = "weberg619@gmail.com";
    } else if (input.type === "password" || nameLower.includes("password")) {
      value = PASS;
    } else if (nameLower.includes("first") && nameLower.includes("name")) {
      value = "Weber";
    } else if (nameLower.includes("last") && nameLower.includes("name")) {
      value = "Gouin";
    } else if (nameLower.includes("name") && !nameLower.includes("user")) {
      // Could be full name
      value = "Weber Gouin";
    } else if (nameLower.includes("user")) {
      value = "bimopsstudio";
    }

    if (value) {
      console.log(`\nFilling ${input.name || input.id || input.type}: "${value.substring(0, 20)}..."`);
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) { el.focus(); el.click(); }
      `);
      await sleep(200);
      // Clear first
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

  // Check for checkboxes (TOS, newsletter, etc.)
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.offsetParent !== null || c.parentElement?.offsetParent !== null)
      .map(c => ({
        id: c.id, name: c.name, checked: c.checked,
        label: c.parentElement?.textContent?.trim()?.substring(0, 80) || c.getAttribute('aria-label') || ''
      }));
    return JSON.stringify(checkboxes);
  `);
  console.log("\nCheckboxes:", r);

  const checkboxes = JSON.parse(r);
  for (const cb of checkboxes) {
    if (!cb.checked && (cb.label.toLowerCase().includes("agree") || cb.label.toLowerCase().includes("terms") || cb.label.toLowerCase().includes("accept"))) {
      console.log(`  Checking TOS checkbox: ${cb.label.substring(0, 50)}`);
      await eval_(`
        const cb = document.querySelector(${JSON.stringify(cb.id ? `#${cb.id}` : `input[name="${cb.name}"]`)});
        if (cb) {
          const rect = (cb.labels?.[0] || cb).getBoundingClientRect();
          return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
        }
        return null;
      `);
    }
  }

  // Verify form state
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(i => i.offsetParent !== null)
      .map(i => ({ type: i.type, name: i.name, value: i.type !== 'password' ? i.value : '***(' + i.value.length + ' chars)' }));
    return JSON.stringify(inputs);
  `);
  console.log("\nForm values:", r);

  // Check for submit button
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, input[type="submit"]'))
      .filter(b => b.offsetParent !== null)
      .map(b => ({
        text: b.textContent.trim().substring(0, 60) || b.value,
        tag: b.tagName, type: b.type,
        x: Math.round(b.getBoundingClientRect().x + b.getBoundingClientRect().width/2),
        y: Math.round(b.getBoundingClientRect().y + b.getBoundingClientRect().height/2)
      }))
      .filter(b => (b.text || '').length > 0);
    return JSON.stringify(btns);
  `);
  console.log("\nButtons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
