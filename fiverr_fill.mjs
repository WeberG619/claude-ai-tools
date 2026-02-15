// Fill Fiverr signup form
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found matching: ${urlMatch}. Available: ${tabs.map(t=>t.url).join(', ')}`);
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

  let { ws, send, eval_ } = await connectToTab("fiverr.com");
  console.log("Connected to Fiverr\n");

  // Check what's on the page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 2000),
      inputs: Array.from(document.querySelectorAll('input, select, textarea'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({ tag: i.tagName, type: i.type, id: i.id, name: i.name, placeholder: i.placeholder }))
    });
  `);
  console.log("Page state:", r);

  const state = JSON.parse(r);
  console.log("\nURL:", state.url);
  console.log("Inputs found:", state.inputs.length);

  // Check if it's a join/register form
  if (state.preview.includes("Join Fiverr") || state.preview.includes("Sign Up") || state.preview.includes("Create") || state.url.includes("join")) {
    console.log("\nFilling signup form...");

    // Look for email input
    const emailInput = state.inputs.find(i => i.type === 'email' || i.name?.includes('email') || i.placeholder?.toLowerCase().includes('email'));
    if (emailInput) {
      console.log("  Found email input:", emailInput.id || emailInput.name || emailInput.placeholder);
      const selector = emailInput.id ? `#${emailInput.id}` : `input[type="email"], input[name*="email"]`;

      // Focus and type email
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) { el.focus(); el.click(); }
      `);
      await sleep(200);
      await send("Input.insertText", { text: "weberg619@gmail.com" });
      await sleep(300);
      console.log("  Entered email");
    }

    // Look for password input
    const passInput = state.inputs.find(i => i.type === 'password');
    if (passInput) {
      console.log("  Found password input");
      const selector = passInput.id ? `#${passInput.id}` : `input[type="password"]`;
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) { el.focus(); el.click(); }
      `);
      await sleep(200);
      await send("Input.insertText", { text: process.argv[2] || "" });
      await sleep(300);
      console.log("  Entered password");
    }

    // Look for username input
    const userInput = state.inputs.find(i => i.name?.includes('username') || i.placeholder?.toLowerCase().includes('username') || i.id?.includes('username'));
    if (userInput) {
      console.log("  Found username input:", userInput.placeholder || userInput.id);
      const selector = userInput.id ? `#${userInput.id}` : `input[name*="username"]`;
      await eval_(`
        const el = document.querySelector(${JSON.stringify(selector)});
        if (el) { el.focus(); el.click(); }
      `);
      await sleep(200);
      await send("Input.insertText", { text: "bimopsstudio" });
      await sleep(300);
      console.log("  Entered username");
    }

    // Check for buttons
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button, input[type="submit"], a'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ tag: b.tagName, text: b.textContent.trim().substring(0, 50), type: b.type }))
        .filter(b => b.text.length > 0);
      return JSON.stringify(btns);
    `);
    console.log("\n  Buttons:", r);
  }

  // Get final state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\n=== Final State ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
