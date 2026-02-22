// Complete Freelancer profile fields and place bid on the data entry job
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

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

async function fillInput(send, eval_, selector, value) {
  const r = await eval_(`
    const el = document.querySelector(${JSON.stringify(selector)});
    if (el) { el.focus(); el.click(); return 'found'; }
    return 'not found';
  `);
  if (r === 'not found') return false;
  await sleep(200);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(100);
  await send("Input.insertText", { text: value });
  await sleep(300);
  return true;
}

async function clickBtn(send, eval_, textMatch) {
  const r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, a, [role="button"]'))
      .filter(b => b.offsetParent !== null && b.textContent.trim().toLowerCase().includes(${JSON.stringify(textMatch.toLowerCase())}));
    if (btns.length > 0) {
      const rect = btns[0].getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btns[0].textContent.trim().substring(0, 50) });
    }
    return null;
  `);
  if (!r) return false;
  const pos = JSON.parse(r);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
  console.log(`  Clicked "${pos.text}"`);
  return true;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // Check what fields need filling
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(i => i.offsetParent !== null && i.type !== 'hidden')
      .map(i => ({
        tag: i.tagName, type: i.type, name: i.name, id: i.id,
        placeholder: i.placeholder?.substring(0, 40),
        value: i.type !== 'password' ? i.value?.substring(0, 30) : '***',
        label: i.labels?.[0]?.textContent?.trim()?.substring(0, 40) || ''
      }));
    return JSON.stringify(inputs);
  `);
  console.log("Form fields:", r);

  // Fill profile fields
  console.log("\n--- Filling Profile ---");

  // First Name
  const firstNameFilled = await fillInput(send, eval_, 'input[placeholder="First Name"], input[name*="firstName"], input[id*="firstName"]', 'Weber');
  console.log("First Name:", firstNameFilled ? "filled" : "not found");

  // Last Name
  const lastNameFilled = await fillInput(send, eval_, 'input[placeholder="Last Name"], input[name*="lastName"], input[id*="lastName"]', 'Gouin');
  console.log("Last Name:", lastNameFilled ? "filled" : "not found");

  // Professional Headline
  const headlineFilled = await fillInput(send, eval_, 'input[placeholder*="headline" i], input[name*="headline" i], input[id*="headline" i]', 'Writer & Data Specialist | AI Tools');
  console.log("Headline:", headlineFilled ? "filled" : "not found");

  // Summary
  r = await eval_(`
    const ta = Array.from(document.querySelectorAll('textarea'))
      .find(t => t.offsetParent !== null && !t.id?.includes('recaptcha'));
    return ta ? (ta.id || ta.name || 'found') : 'not found';
  `);
  if (r !== 'not found') {
    const summarySelector = r === 'found' ? 'textarea' : `#${r}`;
    await fillInput(send, eval_, summarySelector,
      'Professional writer and data specialist with AI-enhanced workflows. Fast, accurate delivery of content, data processing, and research. Specializing in data entry, Excel, article writing, technical writing, copywriting, and research reports.');
    console.log("Summary: filled");
  }

  // Hourly Rate
  r = await eval_(`
    const rateInput = Array.from(document.querySelectorAll('input'))
      .find(i => i.offsetParent !== null && (i.placeholder?.toLowerCase().includes('rate') || i.name?.toLowerCase().includes('rate') || i.parentElement?.textContent?.includes('Hourly Rate')));
    if (rateInput) {
      return rateInput.id || rateInput.name || 'rate-found';
    }
    // Try looking for input near "Hourly Rate" or "USD per hour" text
    const labels = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent.trim() === 'Hourly Rate' || el.textContent.includes('USD per hour'));
    if (labels.length > 0) {
      const nearbyInput = labels[0].parentElement?.querySelector('input') || labels[0].closest('div')?.querySelector('input');
      if (nearbyInput) return nearbyInput.id || nearbyInput.name || 'rate-nearby';
    }
    return 'not found';
  `);
  console.log("Rate input:", r);

  if (r !== 'not found') {
    // Try to fill rate by finding input near "$" and "USD per hour"
    await eval_(`
      const inputs = Array.from(document.querySelectorAll('input[type="number"], input[type="text"]'))
        .filter(i => i.offsetParent !== null);
      // Find one near "USD per hour" text
      for (const input of inputs) {
        const parent = input.closest('div') || input.parentElement;
        if (parent?.textContent?.includes('USD per hour') || parent?.textContent?.includes('Hourly Rate')) {
          input.focus();
          input.click();
          return 'focused rate';
        }
      }
      return 'no rate input';
    `);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
    await sleep(100);
    await send("Input.insertText", { text: "35" });
    console.log("Hourly Rate: set to $35");
    await sleep(300);
  }

  // Address - just need city
  r = await eval_(`
    const addrInput = Array.from(document.querySelectorAll('input'))
      .find(i => i.offsetParent !== null && (i.placeholder?.toLowerCase().includes('address') || i.placeholder?.toLowerCase().includes('city') || i.name?.toLowerCase().includes('address') || i.name?.toLowerCase().includes('location')));
    return addrInput ? (addrInput.id || addrInput.name || 'addr-found') : 'not found';
  `);
  console.log("Address input:", r);

  if (r !== 'not found') {
    await eval_(`
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null && (i.placeholder?.toLowerCase().includes('address') || i.placeholder?.toLowerCase().includes('city') || i.name?.toLowerCase().includes('address')));
      if (inputs[0]) { inputs[0].focus(); inputs[0].click(); }
    `);
    await sleep(200);
    await send("Input.insertText", { text: "Seattle, WA" });
    await sleep(1500);

    // Click the first autocomplete suggestion
    r = await eval_(`
      const suggestions = Array.from(document.querySelectorAll('[class*="suggestion"], [class*="dropdown"] li, [class*="autocomplete"] li, [class*="pac-item"], [role="option"]'))
        .filter(el => el.offsetParent !== null);
      if (suggestions.length > 0) {
        suggestions[0].click();
        return 'selected: ' + suggestions[0].textContent.trim().substring(0, 50);
      }
      return 'no suggestions (' + document.querySelectorAll('.pac-item').length + ' pac-items)';
    `);
    console.log("Address:", r);
    await sleep(500);
  }

  // Click Save on the profile section
  console.log("\nSaving profile...");
  const saved = await clickBtn(send, eval_, "Save");
  await sleep(3000);

  // Check if profile is complete and bid form appeared
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      // Check for bid form
      hasBidForm: !!document.querySelector('[class*="bid"], [class*="Bid"], textarea[name*="description"], textarea[placeholder*="bid"]'),
      // Check for any error messages
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [class*="alert"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100))
        .filter(t => t.length > 5),
      // Get all visible textareas and inputs for bid form
      inputs: Array.from(document.querySelectorAll('input, textarea'))
        .filter(i => i.offsetParent !== null && i.type !== 'hidden')
        .map(i => ({ tag: i.tagName, type: i.type, name: i.name, id: i.id, placeholder: i.placeholder?.substring(0, 50) })),
      preview: document.body.innerText.substring(0, 3000)
    });
  `);
  console.log("\nAfter save:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
