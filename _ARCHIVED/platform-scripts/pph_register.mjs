// Register on PeoplePerHour
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
  await sleep(3000); // Wait for page load
  let { ws, send, eval_ } = await connectToPage("peopleperhour.com/site/register");
  console.log("Connected to PeoplePerHour\n");

  // Check page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 3000),
      inputs: Array.from(document.querySelectorAll('input, select, textarea'))
        .filter(i => i.offsetParent !== null || (i.parentElement && i.parentElement.offsetParent !== null))
        .map(i => ({
          tag: i.tagName, type: i.type, name: i.name, id: i.id,
          placeholder: i.placeholder,
          ariaLabel: i.getAttribute('aria-label'),
          label: i.labels?.[0]?.textContent?.trim()?.substring(0, 50) || ''
        })),
      buttons: Array.from(document.querySelectorAll('button, input[type="submit"]'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ text: (b.textContent || b.value || '').trim().substring(0, 60), type: b.type }))
        .filter(b => b.text.length > 0)
    });
  `);
  console.log("Page:", r);

  const state = JSON.parse(r);

  // Check if there's a "Freelancer" option to select (vs Buyer)
  if (state.preview.includes("Freelancer") && state.preview.includes("Buyer")) {
    console.log("\nLooking for Freelancer option...");
    r = await eval_(`
      const freelancerBtn = Array.from(document.querySelectorAll('button, a, div, label, [role="button"]'))
        .find(el => el.offsetParent !== null && el.textContent.trim() === 'Freelancer');
      if (freelancerBtn) {
        const rect = freelancerBtn.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: freelancerBtn.textContent.trim() });
      }
      return null;
    `);
    if (r) {
      const pos = JSON.parse(r);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      console.log("  Selected Freelancer option");
      await sleep(1000);
    }
  }

  // Map fields and fill them
  const fieldMap = {
    'first_name': 'Weber',
    'firstName': 'Weber',
    'first': 'Weber',
    'last_name': 'Gouin',
    'lastName': 'Gouin',
    'last': 'Gouin',
    'email': 'weberg619@gmail.com',
    'password': PASS,
    'username': 'bimopsstudio',
    'name': 'Weber Gouin'
  };

  // Re-check inputs after potential state change
  r = await eval_(`
    return JSON.stringify(
      Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null || (i.closest('form') && i.type !== 'hidden'))
        .map(i => ({
          type: i.type, name: i.name, id: i.id,
          placeholder: i.placeholder,
          label: i.labels?.[0]?.textContent?.trim()?.substring(0, 50) || '',
          ariaLabel: i.getAttribute('aria-label') || ''
        }))
        .filter(i => i.type !== 'hidden' && i.type !== 'submit' && !i.name?.includes('recaptcha'))
    );
  `);
  console.log("\nInputs:", r);
  const inputs = JSON.parse(r);

  for (const input of inputs) {
    const nameLower = (input.name || input.id || input.placeholder || input.label || input.ariaLabel || "").toLowerCase();
    let value = null;

    if (input.type === 'email' || nameLower.includes('email')) {
      value = 'weberg619@gmail.com';
    } else if (input.type === 'password' || nameLower.includes('password')) {
      value = PASS;
    } else if (nameLower.includes('first') && (nameLower.includes('name') || nameLower.includes('fname'))) {
      value = 'Weber';
    } else if (nameLower.includes('last') && (nameLower.includes('name') || nameLower.includes('lname'))) {
      value = 'Gouin';
    } else if (nameLower.includes('user')) {
      value = 'bimopsstudio';
    } else if (nameLower === 'name' || nameLower.includes('full name') || (input.placeholder?.toLowerCase().includes('name') && !nameLower.includes('first') && !nameLower.includes('last'))) {
      value = 'Weber Gouin';
    }

    if (value) {
      const selector = input.id ? `#${input.id}` :
                       input.name ? `input[name="${input.name}"]` :
                       `input[placeholder="${input.placeholder}"]`;
      console.log(`\nFilling ${input.name || input.id || input.placeholder}: "${value.substring(0, 20)}${value.length > 20 ? '...' : ''}"`);

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
      console.log("  Done");
    }
  }

  // Check for TOS checkbox
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
    if (!cb.checked && (cb.label.toLowerCase().includes('agree') || cb.label.toLowerCase().includes('terms') || cb.label.toLowerCase().includes('accept') || cb.label.toLowerCase().includes('privacy'))) {
      const selector = cb.id ? `#${cb.id}` : `input[name="${cb.name}"]`;
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) {
          const target = el.labels?.[0] || el;
          const rect = target.getBoundingClientRect();
          return JSON.stringify({ x: rect.x + 10, y: rect.y + rect.height/2 });
        }
      `);
      // Click the checkbox label area
      r = await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) {
          const target = el.labels?.[0] || el;
          target.click();
          return 'clicked: ' + cb.label.substring(0, 50);
        }
        return 'not found';
      `);
      console.log("  Checkbox:", r);
      await sleep(300);
    }
  }

  // Find submit button
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

  // Verify form
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(i => i.offsetParent !== null && i.type !== 'hidden')
      .map(i => ({
        name: i.name || i.id || i.type,
        value: i.type === 'password' ? '***' : i.value?.substring(0, 30),
        checked: i.type === 'checkbox' ? i.checked : undefined
      }));
    return JSON.stringify(inputs);
  `);
  console.log("\nForm state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
