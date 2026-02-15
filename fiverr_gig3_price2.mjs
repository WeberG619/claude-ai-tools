// Fix gig #3 pricing: delivery times, unlimited revision, features, then save
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
  await sleep(500);
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
  // Case-insensitive partial match
  const target = opts.find(o => o.text.toLowerCase().includes(optionText.toLowerCase()));
  if (target) {
    await clickAt(send, target.x, target.y);
    await sleep(300);
    return target.text;
  }
  return `not found: "${optionText}" in [${opts.slice(0, 5).map(o => o.text).join(', ')}...]`;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // === FIX DELIVERY TIMES ===
  console.log("=== Delivery Times ===");
  let r = await eval_(`
    const delivDropdowns = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && (el.textContent.trim().includes('Delivery') || el.textContent.trim() === 'Delivery Time'))
      .filter(el => !el.querySelector('.select-penta-design'))  // top-level only
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(delivDropdowns);
  `);
  console.log("Delivery dropdowns:", r);
  const delivDropdowns = JSON.parse(r);

  // Set: 3 days, 2 days, 1 day
  const deliveryTexts = ["3 days", "2 days", "1 day"];
  for (let i = 0; i < Math.min(delivDropdowns.length, 3); i++) {
    const result = await selectPenta(send, eval_, delivDropdowns[i].x, delivDropdowns[i].y, deliveryTexts[i]);
    console.log(`  Package ${i + 1}: ${result}`);
  }

  // === FIX REVISION 3 (Unlimited) ===
  console.log("\n=== Fix Premium Revision ===");
  r = await eval_(`
    // Get the 3rd revision dropdown (Premium)
    const revDropdowns = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => {
        const text = el.textContent.trim();
        return el.offsetParent !== null
          && !el.querySelector('.select-penta-design')
          && (text === 'Select' || text.match(/^\\d+$/) || text === 'UNLIMITED')
          && el.getBoundingClientRect().y < 1100;
      })
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(revDropdowns);
  `);
  console.log("Revision dropdowns:", r);
  const revDropdowns = JSON.parse(r);

  if (revDropdowns.length >= 3) {
    const result = await selectPenta(send, eval_, revDropdowns[2].x, revDropdowns[2].y, "unlimited");
    console.log(`  Premium revision: ${result}`);
  }

  // === FEATURE CHECKBOXES ===
  console.log("\n=== Features ===");
  // Scroll to make sure checkboxes are visible
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(500);

  r = await eval_(`
    // Get all checkboxes that are NOT in extras section and NOT the toggle
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null
          && !el.classList.contains('pkgs-toggler')
          && rect.x > 300  // Not in extras column (x~168)
          && rect.y > 0;
      })
      .map(el => ({
        checked: el.checked,
        x: Math.round(el.getBoundingClientRect().x + 10),
        y: Math.round(el.getBoundingClientRect().y + 10)
      }));
    return JSON.stringify(cbs);
  `);
  console.log("Package checkboxes:", r);
  const cbs = JSON.parse(r);

  // Group into rows (6 features x 3 columns = 18 checkboxes)
  const featureRows = [];
  let lastY = -1;
  let currentRow = [];
  for (const cb of cbs) {
    if (Math.abs(cb.y - lastY) > 20) {
      if (currentRow.length > 0) featureRows.push(currentRow);
      currentRow = [cb];
      lastY = cb.y;
    } else {
      currentRow.push(cb);
    }
  }
  if (currentRow.length > 0) featureRows.push(currentRow);

  console.log(`Found ${featureRows.length} rows with [${featureRows.map(r => r.length).join(',')}] cols`);

  // Features: Editable file, Review&critique, Edit&rewrite, Custom design, LinkedIn, Cover letter
  const checks = [
    [true, true, true],     // Editable file
    [false, false, false],  // Review & critique
    [false, false, true],   // Edit & rewrite
    [false, false, false],  // Custom design
    [false, false, true],   // LinkedIn
    [false, true, true]     // Cover letter
  ];

  for (let row = 0; row < Math.min(featureRows.length, checks.length); row++) {
    for (let col = 0; col < Math.min(featureRows[row].length, 3); col++) {
      const want = checks[row][col];
      const cb = featureRows[row][col];
      if (want && !cb.checked) {
        await clickAt(send, cb.x, cb.y);
        await sleep(200);
      } else if (!want && cb.checked) {
        await clickAt(send, cb.x, cb.y);
        await sleep(200);
      }
    }
  }
  console.log("Features configured");

  // === VERIFY BEFORE SAVE ===
  console.log("\n=== Verify ===");
  r = await eval_(`
    const prices = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.value);
    const deliveries = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().includes('day'))
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify({ prices, deliveries });
  `);
  console.log("Verification:", r);

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
