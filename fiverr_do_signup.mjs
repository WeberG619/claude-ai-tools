// Sign up on Fiverr
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PASS = process.argv[2];

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}. Pages: ${tabs.filter(t=>t.type==="page").map(t=>t.url.substring(0,60)).join(", ")}`);
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
  await sleep(2000);
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected to Fiverr\n");

  // Check what's on the page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 3000),
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ type: i.type, name: i.name, id: i.id, placeholder: i.placeholder, ariaLabel: i.getAttribute('aria-label'), autocomplete: i.autocomplete })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ text: b.textContent.trim().substring(0, 60), type: b.type, ariaLabel: b.getAttribute('aria-label') }))
        .filter(b => b.text.length > 0),
      links: Array.from(document.querySelectorAll('a'))
        .filter(a => a.offsetParent !== null)
        .map(a => ({ text: a.textContent.trim().substring(0, 60), href: a.href?.substring(0, 80) }))
        .filter(a => a.text.length > 0 && (a.text.toLowerCase().includes('email') || a.text.toLowerCase().includes('sign') || a.text.toLowerCase().includes('join') || a.text.toLowerCase().includes('continue')))
    });
  `);
  console.log("Page:", r);

  const state = JSON.parse(r);

  // Fiverr typically shows social login buttons first, then "Continue with Email"
  // Look for the email option
  const emailBtn = state.buttons.find(b => b.text.toLowerCase().includes('email'));
  const emailLink = state.links.find(l => l.text.toLowerCase().includes('email'));

  if (emailBtn || emailLink) {
    const target = emailBtn ? 'button' : 'link';
    console.log(`\nClicking "${(emailBtn || emailLink).text}" (${target})...`);

    r = await eval_(`
      const el = Array.from(document.querySelectorAll('button, a'))
        .find(b => b.offsetParent !== null && b.textContent.toLowerCase().includes('email'));
      if (el) {
        const rect = el.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: el.textContent.trim() });
      }
      return null;
    `);

    if (r) {
      const pos = JSON.parse(r);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      console.log("  Clicked at", Math.round(pos.x), Math.round(pos.y));
      await sleep(2000);
    }
  }

  // Now check for the email form
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ type: i.type, name: i.name, id: i.id, placeholder: i.placeholder })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ text: b.textContent.trim().substring(0, 60), type: b.type }))
        .filter(b => b.text.length > 0)
    });
  `);
  console.log("\nAfter email click:", r);
  const formState = JSON.parse(r);

  // Fill email
  const emailInput = formState.inputs.find(i => i.type === 'email' || i.name?.includes('email') || i.placeholder?.toLowerCase().includes('email'));
  if (emailInput) {
    const selector = emailInput.id ? `#${emailInput.id}` :
                     emailInput.name ? `input[name="${emailInput.name}"]` :
                     'input[type="email"]';
    console.log("\nFilling email...");
    await eval_(`
      const el = document.querySelector(${JSON.stringify(selector)});
      if (el) { el.focus(); el.click(); }
    `);
    await sleep(200);
    await send("Input.insertText", { text: "weberg619@gmail.com" });
    await sleep(500);
    console.log("  Email entered");
  }

  // Check if there's a "Continue" button to go to the next step
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.offsetParent !== null && (b.textContent.trim().toLowerCase().includes('continue') || b.textContent.trim().toLowerCase().includes('join') || b.type === 'submit'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim() });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    console.log(`\nClicking "${pos.text}"...`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(3000);
  }

  // Check if we need to fill more fields (password, username, etc.)
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 2000),
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ type: i.type, name: i.name, id: i.id, placeholder: i.placeholder })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ text: b.textContent.trim().substring(0, 60) }))
        .filter(b => b.text.length > 0)
    });
  `);
  console.log("\n=== Current State ===");
  console.log(r);

  // Fill password if present
  const currentState = JSON.parse(r);
  const passField = currentState.inputs.find(i => i.type === 'password');
  if (passField) {
    const selector = passField.id ? `#${passField.id}` : 'input[type="password"]';
    console.log("\nFilling password...");
    await eval_(`
      const el = document.querySelector(${JSON.stringify(selector)});
      if (el) { el.focus(); el.click(); }
    `);
    await sleep(200);
    await send("Input.insertText", { text: PASS });
    await sleep(500);
    console.log("  Password entered");
  }

  // Fill username if present
  const userField = currentState.inputs.find(i => i.name?.includes('username') || i.placeholder?.toLowerCase().includes('username') || i.id?.includes('username'));
  if (userField) {
    const selector = userField.id ? `#${userField.id}` : `input[name="${userField.name}"]`;
    console.log("\nFilling username...");
    await eval_(`
      const el = document.querySelector(${JSON.stringify(selector)});
      if (el) { el.focus(); el.click(); }
    `);
    await sleep(200);
    await send("Input.insertText", { text: "bimopsstudio" });
    await sleep(500);
    console.log("  Username entered");
  }

  // Final state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 1500),
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ type: i.type, name: i.name, value: i.type !== 'password' ? i.value : '***' }))
    });
  `);
  console.log("\n=== FINAL ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
