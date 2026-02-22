// Fill Fiverr gig #2 pricing - Proofreading packages
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function typeInField(send, x, y, text) {
  await clickAt(send, x, y);
  await sleep(200);
  // Select all then type
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(100);
  await send("Input.insertText", { text });
  await sleep(300);
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Check current page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: (document.body?.innerText || '').substring(0, 1000)
    });
  `);
  console.log("Page:", JSON.parse(r).url);

  // Map the pricing form fields
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null || el.type === 'hidden')
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 40),
        class: (el.className?.toString() || '').substring(0, 60),
        value: (el.value || '').substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }))
      .filter(el => el.y > 0);
    return JSON.stringify(inputs);
  `);
  console.log("Form fields:", r);
  const fields = JSON.parse(r);

  // Check if there's a toggle for "Offer packages" - need 3 tiers
  r = await eval_(`
    const toggle = document.querySelector('[class*="packages-toggle"], [class*="offer-packages"], input[type="checkbox"][id*="package"]');
    if (toggle) {
      const rect = toggle.getBoundingClientRect();
      return JSON.stringify({
        checked: toggle.checked,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    // Check for toggle switch
    const switchEl = Array.from(document.querySelectorAll('[class*="switch"], [class*="toggle"]'))
      .find(el => el.offsetParent !== null && el.getBoundingClientRect().y > 100);
    if (switchEl) {
      const rect = switchEl.getBoundingClientRect();
      return JSON.stringify({
        text: switchEl.textContent.trim().substring(0, 30),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    return JSON.stringify({ error: 'no toggle' });
  `);
  console.log("Package toggle:", r);

  // Get the package table structure
  r = await eval_(`
    // Find all editable cells in the pricing table
    const rows = Array.from(document.querySelectorAll('tr, [class*="row"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => {
        const cells = Array.from(el.querySelectorAll('td, [class*="cell"]'));
        return {
          label: (el.querySelector('th, [class*="label"], td:first-child')?.textContent?.trim() || '').substring(0, 30),
          cellCount: cells.length,
          y: Math.round(el.getBoundingClientRect().y)
        };
      })
      .filter(r => r.label && r.y > 0);
    return JSON.stringify(rows);
  `);
  console.log("Pricing rows:", r);

  // Identify the specific fields we need to fill
  // Package names (Basic/Standard/Premium), descriptions, delivery time, price, words included
  console.log("\n=== Filling Package Names ===");

  // Find the package name inputs (first row of inputs)
  r = await eval_(`
    const nameInputs = Array.from(document.querySelectorAll('input[class*="name"], input[placeholder*="Name"], textarea'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 100 && el.getBoundingClientRect().y < 400)
      .map(el => ({
        name: el.name || '',
        placeholder: el.placeholder || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        value: el.value
      }));
    return JSON.stringify(nameInputs);
  `);
  console.log("Name inputs:", r);

  // Look for all the input/textarea/select fields in the pricing table
  r = await eval_(`
    // Get the pricing table container
    const table = document.querySelector('[class*="pricing-table"], [class*="packages"], table');
    if (!table) return JSON.stringify({ error: 'no pricing table' });

    const allInputs = Array.from(table.querySelectorAll('input, textarea, select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        placeholder: (el.placeholder || '').substring(0, 30),
        class: (el.className?.toString() || '').substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        value: (el.value || '').substring(0, 30)
      }));
    return JSON.stringify(allInputs);
  `);
  console.log("Table inputs:", r);

  // Get the full visible content to understand the pricing form layout
  r = await eval_(`
    const pricingArea = document.querySelector('[class*="scope-pricing"], [class*="pricing-content"]');
    if (pricingArea) return pricingArea.innerText.substring(0, 2000);
    return (document.body?.innerText || '').substring(0, 2000);
  `);
  console.log("\nPricing area text:", r);

  // Find all textareas and inputs in the pricing section (package names + descriptions)
  r = await eval_(`
    const textareas = Array.from(document.querySelectorAll('textarea'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 100)
      .map(el => ({
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width),
        value: (el.value || '').substring(0, 40)
      }));
    return JSON.stringify(textareas);
  `);
  console.log("Textareas:", r);
  const textareas = JSON.parse(r);

  // Fill package name/description textareas
  // Typically: Row 1 = names, Row 2 = descriptions for Basic/Standard/Premium
  const packageData = {
    basic: { name: "Basic Edit", desc: "Proofreading up to 1000 words with grammar and spelling corrections" },
    standard: { name: "Standard Edit", desc: "Proofreading and light editing up to 3000 words with grammar, clarity, and flow improvements" },
    premium: { name: "Premium Rewrite", desc: "Full proofreading, editing, and rewriting up to 5000 words for maximum clarity and impact" }
  };

  // Group textareas by Y position (same row = same field type)
  const rows = {};
  for (const ta of textareas) {
    const rowKey = Math.round(ta.y / 30) * 30; // Group by ~30px
    if (!rows[rowKey]) rows[rowKey] = [];
    rows[rowKey].push(ta);
  }
  const sortedRows = Object.entries(rows).sort(([a], [b]) => Number(a) - Number(b));
  console.log("\nTextarea rows:", sortedRows.map(([y, tas]) => `y~${y}: ${tas.length} textareas`).join(', '));

  // First row of textareas = package names
  if (sortedRows.length >= 1) {
    const nameRow = sortedRows[0][1].sort((a, b) => a.x - b.x);
    const names = ["Basic Edit", "Standard Edit", "Premium Rewrite"];
    for (let i = 0; i < Math.min(nameRow.length, names.length); i++) {
      console.log(`Setting name ${i}: "${names[i]}" at (${nameRow[i].x}, ${nameRow[i].y})`);
      await typeInField(send, nameRow[i].x, nameRow[i].y, names[i]);
    }
  }

  // Second row = descriptions
  if (sortedRows.length >= 2) {
    const descRow = sortedRows[1][1].sort((a, b) => a.x - b.x);
    const descs = [
      packageData.basic.desc,
      packageData.standard.desc,
      packageData.premium.desc
    ];
    for (let i = 0; i < Math.min(descRow.length, descs.length); i++) {
      console.log(`Setting desc ${i}: "${descs[i].substring(0, 40)}..." at (${descRow[i].x}, ${descRow[i].y})`);
      await typeInField(send, descRow[i].x, descRow[i].y, descs[i]);
    }
  }

  // Handle delivery time dropdowns
  console.log("\n=== Setting Delivery Times ===");
  r = await eval_(`
    const selects = Array.from(document.querySelectorAll('select'))
      .filter(el => el.offsetParent !== null && el.name?.includes('delivery'))
      .map(el => ({
        name: el.name,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        options: Array.from(el.options).map(o => ({ text: o.textContent.trim(), value: o.value })).slice(0, 10)
      }));
    return JSON.stringify(selects);
  `);
  console.log("Delivery selects:", r);

  // Find all select dropdowns in the pricing area
  r = await eval_(`
    const allSelects = Array.from(document.querySelectorAll('select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name || '',
        id: el.id || '',
        class: (el.className?.toString() || '').substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        options: Array.from(el.options).map(o => o.textContent.trim().substring(0, 20)).slice(0, 5),
        value: el.value
      }));
    return JSON.stringify(allSelects);
  `);
  console.log("All selects:", r);
  const allSelects = JSON.parse(r);

  // Delivery time selects - set to 3 day, 2 day, 1 day for Basic/Standard/Premium
  const deliverySelects = allSelects.filter(s => s.options.some(o => o.includes('day')));
  const deliveryTimes = ["3", "2", "1"]; // values for 3-day, 2-day, 1-day
  for (let i = 0; i < Math.min(deliverySelects.length, deliveryTimes.length); i++) {
    console.log(`Setting delivery ${i} to ${deliveryTimes[i]} day(s)`);
    await eval_(`
      const sel = document.querySelectorAll('select')[${allSelects.indexOf(deliverySelects[i])}];
      if (sel) {
        const opt = Array.from(sel.options).find(o => o.value === '${deliveryTimes[i]}' || o.textContent.includes('${deliveryTimes[i]} day'));
        if (opt) {
          sel.value = opt.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return 'set: ' + opt.textContent.trim();
        }
        return 'no matching option';
      }
      return 'no select';
    `);
    await sleep(300);
  }

  // Handle "Words included" number inputs
  console.log("\n=== Setting Word Counts ===");
  r = await eval_(`
    const numberInputs = Array.from(document.querySelectorAll('input[type="number"], input[class*="words"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name || '',
        placeholder: el.placeholder || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        value: el.value
      }));
    return JSON.stringify(numberInputs);
  `);
  console.log("Number inputs:", r);
  const numInputs = JSON.parse(r);

  const wordCounts = ["1000", "3000", "5000"];
  for (let i = 0; i < Math.min(numInputs.length, wordCounts.length); i++) {
    console.log(`Setting words ${i} to ${wordCounts[i]}`);
    await typeInField(send, numInputs[i].x, numInputs[i].y, wordCounts[i]);
  }

  // Handle checkboxes (Grammar & spelling, Fact checking, AI detection)
  console.log("\n=== Setting Feature Checkboxes ===");
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name || '',
        id: el.id || '',
        checked: el.checked,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        label: el.closest('label')?.textContent?.trim()?.substring(0, 30) || ''
      }));
    return JSON.stringify(checkboxes);
  `);
  console.log("Checkboxes:", r);

  // Handle revisions select
  console.log("\n=== Setting Revisions ===");
  const revisionSelects = allSelects.filter(s => s.options.some(o => o.includes('Unlimited') || o.includes('revision')));
  for (const sel of revisionSelects) {
    await eval_(`
      const selects = Array.from(document.querySelectorAll('select')).filter(el => el.offsetParent !== null);
      for (const sel of selects) {
        const unlimitedOpt = Array.from(sel.options).find(o => o.textContent.includes('Unlimited'));
        if (unlimitedOpt) {
          sel.value = unlimitedOpt.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }
      return 'done';
    `);
  }

  // Handle price inputs
  console.log("\n=== Setting Prices ===");
  r = await eval_(`
    const priceInputs = Array.from(document.querySelectorAll('input[class*="price"], input[name*="price"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        value: el.value
      }));
    return JSON.stringify(priceInputs);
  `);
  console.log("Price inputs:", r);
  const priceInputs = JSON.parse(r);
  const prices = ["10", "25", "50"];
  for (let i = 0; i < Math.min(priceInputs.length, prices.length); i++) {
    console.log(`Setting price ${i} to $${prices[i]}`);
    await typeInField(send, priceInputs[i].x, priceInputs[i].y, prices[i]);
  }

  // Final state
  await sleep(500);
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: (document.body?.innerText || '').substring(0, 1500)
    });
  `);
  console.log("\n=== Current State ===");
  console.log(JSON.parse(r).body.substring(0, 500));

  // Try Save & Continue
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(800);

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
    console.log(`\nClicking Save & Continue at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 500)
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
