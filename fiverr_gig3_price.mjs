// Fill gig #3 pricing: delivery, revisions, features, prices
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

async function tripleClick(send, x, y) {
  for (let c = 1; c <= 3; c++) {
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: c });
    await sleep(30);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: c });
    await sleep(30);
  }
}

async function selectPenta(send, eval_, dropdownX, dropdownY, optionText) {
  // Click the penta-select dropdown
  await clickAt(send, dropdownX, dropdownY);
  await sleep(500);

  // Find and click the option
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
  const target = opts.find(o => o.text.includes(optionText));
  if (target) {
    await clickAt(send, target.x, target.y);
    await sleep(300);
    return target.text;
  }
  return `not found: ${optionText} (options: ${opts.map(o => o.text).join(', ')})`;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // === PACKAGE DESCRIPTIONS (textareas in the header) ===
  console.log("=== Package Descriptions ===");
  let r = await eval_(`
    const textareas = Array.from(document.querySelectorAll('textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        value: el.value,
        placeholder: el.placeholder?.substring(0, 30),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(textareas);
  `);
  console.log("Textareas:", r);
  const textareas = JSON.parse(r);

  // Fill package names/descriptions
  const pkgDescs = [
    "Basic resume writing - clean, professional format",
    "Resume + cover letter - tailored for your target role",
    "Complete package: resume, cover letter, LinkedIn optimization"
  ];
  for (let i = 0; i < Math.min(textareas.length, 3); i++) {
    await tripleClick(send, textareas[i].x, textareas[i].y);
    await sleep(100);
    await send("Input.insertText", { text: pkgDescs[i] });
    await sleep(200);
    console.log(`Package ${i + 1}: "${pkgDescs[i]}"`);
  }

  // === DELIVERY TIME ===
  console.log("\n=== Delivery Time ===");
  // Get penta-select positions for delivery time (first 3)
  r = await eval_(`
    const pentaDropdowns = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().includes('Delivery'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(pentaDropdowns);
  `);
  console.log("Delivery dropdowns:", r);
  const delivDropdowns = JSON.parse(r);

  const deliveryTimes = ["3 Days", "2 Days", "1 Day"];
  for (let i = 0; i < Math.min(delivDropdowns.length, 3); i++) {
    const result = await selectPenta(send, eval_, delivDropdowns[i].x, delivDropdowns[i].y, deliveryTimes[i]);
    console.log(`  Package ${i + 1}: ${result}`);
  }

  // === REVISIONS ===
  console.log("\n=== Revisions ===");
  r = await eval_(`
    const pentaDropdowns = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && el.textContent.trim() === 'Select'
        && el.getBoundingClientRect().y < 1100)  // Only package area, not extras
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(pentaDropdowns);
  `);
  console.log("Revision dropdowns:", r);
  const revDropdowns = JSON.parse(r);

  const revisions = ["1", "2", "Unlimited"];
  for (let i = 0; i < Math.min(revDropdowns.length, 3); i++) {
    const result = await selectPenta(send, eval_, revDropdowns[i].x, revDropdowns[i].y, revisions[i]);
    console.log(`  Package ${i + 1}: ${result}`);
  }

  // === FEATURE CHECKBOXES ===
  console.log("\n=== Features ===");
  // Feature rows (from page text): Editable file, Review & critique, Edit & rewrite, Custom design, Optimize LinkedIn, Cover letter
  // Columns: Basic (x~452), Standard (x~638), Premium (x~824)
  // We want:
  // Basic: Editable file ✓
  // Standard: Editable file ✓, Cover letter ✓
  // Premium: Editable file ✓, Edit & rewrite ✓, Optimize LinkedIn ✓, Cover letter ✓

  r = await eval_(`
    // Get all checkbox rows in the package table
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null && !el.classList.contains('pkgs-toggler'))
      .map(el => ({
        checked: el.checked,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        // Get row label
        label: el.closest('tr, [class*="row"]')?.querySelector('[class*="label"], th, td:first-child')?.textContent?.trim()?.substring(0, 30) || ''
      }));
    // Group by y position to find rows
    const rows = {};
    checkboxes.forEach(cb => {
      const rowKey = Math.round(cb.y / 50) * 50;
      if (!rows[rowKey]) rows[rowKey] = [];
      rows[rowKey].push(cb);
    });
    return JSON.stringify({ total: checkboxes.length, rows: Object.keys(rows).length });
  `);
  console.log("Checkbox layout:", r);

  // Get the feature checkboxes in the package table area (y < 1500 to exclude extras)
  r = await eval_(`
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null
          && !el.classList.contains('pkgs-toggler')
          && rect.y > 900 && rect.y < 1500  // Package feature area
          && rect.x > 300;  // Not the extras column
      })
      .map(el => ({
        checked: el.checked,
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(cbs);
  `);
  console.log("Package checkboxes:", r);
  const pkgCheckboxes = JSON.parse(r);

  // Feature rows are in order: Editable file, Review & critique, Edit & rewrite, Custom design, Optimize LinkedIn, Cover letter
  // Each row has 3 checkboxes (Basic, Standard, Premium)
  // Group by approximate y
  const rows = [];
  let currentY = -1;
  let currentRow = [];
  for (const cb of pkgCheckboxes) {
    if (Math.abs(cb.y - currentY) > 30) {
      if (currentRow.length > 0) rows.push(currentRow);
      currentRow = [cb];
      currentY = cb.y;
    } else {
      currentRow.push(cb);
    }
  }
  if (currentRow.length > 0) rows.push(currentRow);

  console.log(`Found ${rows.length} feature rows with ${rows.map(r => r.length).join(',')} checkboxes`);

  // Features: [Editable, Review, Edit&rewrite, Custom, LinkedIn, Cover letter]
  // Basic (col 0): Editable
  // Standard (col 1): Editable, Cover letter
  // Premium (col 2): Editable, Edit&rewrite, LinkedIn, Cover letter
  const featureChecks = [
    [true, true, true],     // Editable file - all tiers
    [false, false, false],  // Review & critique - none
    [false, false, true],   // Edit & rewrite - premium only
    [false, false, false],  // Custom design - none
    [false, false, true],   // Optimize LinkedIn - premium only
    [false, true, true]     // Cover letter - standard + premium
  ];

  for (let rowIdx = 0; rowIdx < Math.min(rows.length, featureChecks.length); rowIdx++) {
    for (let colIdx = 0; colIdx < Math.min(rows[rowIdx].length, 3); colIdx++) {
      const shouldCheck = featureChecks[rowIdx][colIdx];
      const cb = rows[rowIdx][colIdx];
      if (shouldCheck && !cb.checked) {
        await clickAt(send, cb.x + 10, cb.y + 10);
        await sleep(200);
      }
    }
  }
  console.log("Features set");

  // === PRICES ===
  console.log("\n=== Prices ===");
  r = await eval_(`
    const priceInputs = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        value: el.value,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(priceInputs);
  `);
  const priceInputs = JSON.parse(r);
  const prices = ["15", "30", "60"];

  for (let i = 0; i < Math.min(priceInputs.length, 3); i++) {
    await tripleClick(send, priceInputs[i].x, priceInputs[i].y);
    await sleep(100);
    await send("Input.insertText", { text: prices[i] });
    await sleep(100);
    // Tab to trigger validation
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(200);
    console.log(`Price ${i + 1}: $${prices[i]}`);
  }

  // === UNCHECK EXTRAS THAT HAVE EMPTY PRICE-STEPPERS ===
  console.log("\n=== Extras ===");
  // From gig #2 experience: unchecked extras with empty prices block save
  // Uncheck "Extra fast delivery" and any other checked extras with empty values
  r = await eval_(`
    const extraCheckboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y > 1500 && el.checked;
      })
      .map(el => {
        const label = el.closest('[class*="extra"], [class*="addon"], tr, div')?.textContent?.trim()?.substring(0, 40) || '';
        return {
          checked: true,
          label,
          x: Math.round(el.getBoundingClientRect().x + 10),
          y: Math.round(el.getBoundingClientRect().y + 10)
        };
      });
    return JSON.stringify(extraCheckboxes);
  `);
  console.log("Checked extras:", r);
  const checkedExtras = JSON.parse(r);

  // Uncheck all extras to keep it simple (avoid empty price-stepper issues)
  for (const extra of checkedExtras) {
    console.log(`Unchecking: "${extra.label}"`);
    await clickAt(send, extra.x, extra.y);
    await sleep(300);
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  await sleep(800);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error) {
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(8000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
