// Fix gig #3 pricing - final attempt with JS state manipulation
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
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

async function selectPenta(send, eval_, dropdownX, dropdownY, optionText) {
  await clickAt(send, dropdownX, dropdownY);
  await sleep(600);
  const r = await eval_(`
    const opts = Array.from(document.querySelectorAll('.table-select-option'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(opts);
  `);
  const opts = JSON.parse(r);
  const target = opts.find(o => o.text.toLowerCase().includes(optionText.toLowerCase()));
  if (target) {
    await clickAt(send, target.x, target.y);
    await sleep(400);
    return target.text;
  }
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  return `NOT FOUND`;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // First, navigate back to wizard=1 if needed
  let r = await eval_(`return new URL(location.href).searchParams.get('wizard')`);
  if (r !== '1') {
    console.log("Not on wizard=1, navigating...");
    await eval_(`window.location.href = location.href.replace(/wizard=\\d+/, 'wizard=1').replace(/&tab=\\w+/, '')`);
    await sleep(5000);
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
  }

  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // === STEP 1: Set package titles using click + focus + insertText for each individually ===
  console.log("=== Titles ===");
  const titles = ["Basic", "Standard", "Premium"];
  for (let i = 0; i < 3; i++) {
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('.pkg-title-input'))
        .filter(el => el.offsetParent !== null);
      if (inputs[${i}]) {
        inputs[${i}].scrollIntoView({ block: 'center' });
        inputs[${i}].focus();
        const rect = inputs[${i}].getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: inputs[${i}].value });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    const pos = JSON.parse(r);
    if (pos.error) continue;
    if (pos.val === titles[i]) { console.log(`  Title ${i+1}: already "${titles[i]}"`); continue; }

    await clickAt(send, pos.x, pos.y);
    await sleep(200);
    // Select all content
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.insertText", { text: titles[i] });
    await sleep(200);
    console.log(`  Title ${i+1}: "${titles[i]}"`);
  }

  // === STEP 2: Set descriptions ===
  console.log("\n=== Descriptions ===");
  const descs = [
    "Professional resume with keyword optimization",
    "Resume plus cover letter for your target role",
    "Resume, cover letter, and LinkedIn profile"
  ];
  for (let i = 0; i < 3; i++) {
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('.pkg-description-input'))
        .filter(el => el.offsetParent !== null);
      if (inputs[${i}]) {
        inputs[${i}].scrollIntoView({ block: 'center' });
        inputs[${i}].focus();
        const rect = inputs[${i}].getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    const pos = JSON.parse(r);
    if (pos.error) continue;

    await clickAt(send, pos.x, pos.y);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.insertText", { text: descs[i] });
    await sleep(200);
    console.log(`  Desc ${i+1}: set`);
  }

  // === STEP 3: Delivery times ===
  console.log("\n=== Delivery ===");
  r = await eval_(`
    const dd = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && !el.querySelector('.select-penta-design')
        && el.textContent.trim().includes('Delivery') && el.getBoundingClientRect().y > 0)
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(dd);
  `);
  const dd = JSON.parse(r);
  for (let i = 0; i < Math.min(dd.length, 3); i++) {
    const result = await selectPenta(send, eval_, dd[i].x, dd[i].y, ["3 days", "2 days", "1 day"][i]);
    console.log(`  ${result}`);
  }

  // === STEP 4: Revisions ===
  console.log("\n=== Revisions ===");
  r = await eval_(`
    const rd = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && !el.querySelector('.select-penta-design')
        && (el.textContent.trim() === 'Select' || /^\\d+$/.test(el.textContent.trim()) || el.textContent.trim() === 'UNLIMITED')
        && el.getBoundingClientRect().y > 0 && el.getBoundingClientRect().y < 1200)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(rd);
  `);
  const rd = JSON.parse(r);
  for (let i = 0; i < Math.min(rd.length, 3); i++) {
    const wanted = ["1", "2", "unlimited"][i];
    if (rd[i].text.toLowerCase() === wanted) {
      console.log(`  Rev ${i+1}: already "${rd[i].text}"`);
    } else {
      const result = await selectPenta(send, eval_, rd[i].x, rd[i].y, wanted);
      console.log(`  Rev ${i+1}: ${result}`);
    }
  }

  // === STEP 5: Prices - set each one individually with careful focus ===
  console.log("\n=== Prices ===");
  const prices = ["15", "30", "60"];
  for (let i = 0; i < 3; i++) {
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('.price-input'))
        .filter(el => el.offsetParent !== null);
      if (inputs[${i}]) {
        inputs[${i}].scrollIntoView({ block: 'center' });
        inputs[${i}].focus();
        const rect = inputs[${i}].getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: inputs[${i}].value });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    const pos = JSON.parse(r);
    if (pos.error) continue;

    // Click to focus
    await clickAt(send, pos.x, pos.y);
    await sleep(300);

    // Select all
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);

    // Delete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(100);

    // Insert price
    await send("Input.insertText", { text: prices[i] });
    await sleep(300);

    // Click somewhere else to blur
    await clickAt(send, pos.x + 200, pos.y);
    await sleep(300);

    console.log(`  Price ${i+1}: $${prices[i]}`);
  }

  // Verify all prices
  r = await eval_(`
    return JSON.stringify(Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null).map(el => el.value));
  `);
  console.log("Prices verify:", r);

  // === STEP 6: Uncheck all extras via JS ===
  console.log("\n=== Uncheck Extras via JS ===");
  r = await eval_(`
    // Find ALL checked checkboxes in extras section (x < 300)
    const extras = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => {
        return el.offsetParent !== null && el.checked
          && !el.classList.contains('pkgs-toggler')
          && el.getBoundingClientRect().x < 300;
      });
    const results = [];
    for (const cb of extras) {
      const label = cb.closest('div, li, tr')?.textContent?.trim()?.substring(0, 30) || 'unknown';
      // Use native setter to uncheck
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'checked').set;
      nativeSetter.call(cb, false);
      cb.dispatchEvent(new Event('input', { bubbles: true }));
      cb.dispatchEvent(new Event('change', { bubbles: true }));
      cb.dispatchEvent(new Event('click', { bubbles: true }));
      results.push(label);
    }
    return JSON.stringify(results);
  `);
  console.log("Unchecked via JS:", r);
  await sleep(500);

  // Verify extras
  r = await eval_(`
    const checked = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null && el.checked && !el.classList.contains('pkgs-toggler') && el.getBoundingClientRect().x < 300)
      .map(el => el.closest('div, li')?.textContent?.trim()?.substring(0, 30) || '');
    return JSON.stringify(checked);
  `);
  console.log("Still checked extras:", r);

  // === STEP 7: SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(1000);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error) {
    console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(10000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        tab: new URL(location.href).searchParams.get('tab'),
        errors
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
