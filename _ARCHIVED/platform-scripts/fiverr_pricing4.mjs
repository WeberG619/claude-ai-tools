// Fix pricing: use CDP keyboard for prices, proper checkbox clicks, proper revision selection
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.url.includes("edit"));
  if (!tab) throw new Error("No Fiverr edit tab");
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
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) { console.error("JS Err:", JSON.stringify(r.exceptionDetails).substring(0, 500)); return null; }
    return r.result?.value;
  };
  async function cdpClick(x, y) {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(100);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1, buttons: 1 });
    await sleep(80);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  }
  async function tripleClick(x, y) {
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 3 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 3 });
  }
  async function pressKey(key, code, keyCode) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
  }
  async function typeText(text) {
    for (const char of text) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char, unmodifiedText: char });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
      await sleep(60);
    }
  }
  return { ws, send, eval_, cdpClick, tripleClick, pressKey, typeText };
}

async function main() {
  const { ws, send, eval_, cdpClick, tripleClick, pressKey, typeText } = await connect();

  // Step 1: Get all price input coordinates
  console.log("=== Step 1: Price inputs ===");
  const priceCoords = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const priceRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('price'));
      if (!priceRow) return '[]';
      return JSON.stringify([1,2,3].map(i => {
        const input = priceRow.cells[i]?.querySelector('input.price-input, input[type="number"]');
        if (!input) return null;
        const rect = input.getBoundingClientRect();
        return { col: i, value: input.value, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) };
      }).filter(Boolean));
    })()
  `);
  console.log("Prices:", priceCoords);

  const prices = JSON.parse(priceCoords);
  const targetPrices = { 1: '90', 2: '250', 3: '500' };

  for (const p of prices) {
    const target = targetPrices[p.col];
    console.log(`\nSetting col ${p.col}: $${p.value} -> $${target}`);

    // Triple-click to select all
    await tripleClick(p.x, p.y);
    await sleep(300);

    // Also Ctrl+A to be sure
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", windowsVirtualKeyCode: 65 });
    await sleep(200);

    // Delete existing value
    await pressKey("Backspace", "Backspace", 8);
    await sleep(200);

    // Type new value
    await typeText(target);
    await sleep(300);

    // Tab to trigger blur
    await pressKey("Tab", "Tab", 9);
    await sleep(500);

    // Verify
    const newVal = await eval_(`
      (function() {
        const rows = Array.from(document.querySelectorAll('tr'));
        const priceRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('price'));
        return priceRow?.cells[${p.col}]?.querySelector('input')?.value || 'unknown';
      })()
    `);
    console.log(`  Value after: $${newVal}`);
  }

  // Step 2: Fix fine-tuning checkbox via CDP click
  console.log("\n=== Step 2: Fix Fine-tuning ===");
  const ftCoord = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const row = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('fine'));
      if (!row) return null;
      const cell = row.cells[3]; // Premium column
      const cb = cell?.querySelector('input[type="checkbox"]');
      if (!cb) return null;
      // Click on the label or container, not the hidden checkbox
      const label = cb.closest('label') || cb.parentElement;
      const rect = label.getBoundingClientRect();
      return JSON.stringify({
        checked: cb.checked,
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    })()
  `);
  console.log("Fine-tuning Premium:", ftCoord);

  if (ftCoord) {
    const ft = JSON.parse(ftCoord);
    if (!ft.checked) {
      console.log(`  CDP clicking at (${ft.x}, ${ft.y})...`);
      await cdpClick(ft.x, ft.y);
      await sleep(500);

      // Verify
      const ftCheck = await eval_(`
        (function() {
          const rows = Array.from(document.querySelectorAll('tr'));
          const row = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('fine'));
          return row?.cells[3]?.querySelector('input[type="checkbox"]')?.checked;
        })()
      `);
      console.log(`  Now checked: ${ftCheck}`);
    }
  }

  // Step 3: Fix revisions - find the actual revision row and its dropdowns
  console.log("\n=== Step 3: Fix Revisions ===");
  const revStructure = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const revRow = rows.find(r => {
        const text = r.cells?.[0]?.textContent?.toLowerCase() || '';
        return text.includes('revision');
      });
      if (!revRow) return 'no revision row found';

      // Scroll to it
      revRow.scrollIntoView({ block: 'center' });

      const cells = [];
      for (let i = 1; i <= 3; i++) {
        const cell = revRow.cells[i];
        if (!cell) continue;

        // Get ALL child elements
        const allEls = Array.from(cell.querySelectorAll('*'));
        const hidden = cell.querySelector('input[type="hidden"]');
        const text = cell.textContent.trim();

        // Find clickable dropdown element
        const clickable = allEls.find(el => {
          const s = window.getComputedStyle(el);
          return (s.cursor === 'pointer' || el.role === 'button' || el.tagName === 'BUTTON') && el.offsetParent;
        }) || cell.querySelector('[class*="dropdown"]') || cell.querySelector('[class*="select"]');

        const rect = (clickable || cell).getBoundingClientRect();
        cells.push({
          col: i,
          hiddenValue: hidden?.value,
          text: text.substring(0, 20),
          clickableTag: clickable?.tagName,
          clickableClass: clickable?.className?.substring?.(0, 30) || '',
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          html: cell.innerHTML.substring(0, 200)
        });
      }
      return JSON.stringify(cells);
    })()
  `);
  console.log("Revision structure:", revStructure);

  const revCells = JSON.parse(revStructure);
  if (Array.isArray(revCells)) {
    const targetRevs = { 1: '2', 2: '3', 3: 'Unlimited' };

    for (const rev of revCells) {
      const target = targetRevs[rev.col];
      console.log(`\nRevision col ${rev.col}: current="${rev.hiddenValue}" target="${target}"`);
      console.log(`  Clicking at (${rev.x}, ${rev.y})...`);
      await cdpClick(rev.x, rev.y);
      await sleep(1000);

      // Check for dropdown options
      const opts = await eval_(`
        (function() {
          // Look for newly appeared dropdown options
          const popups = Array.from(document.querySelectorAll('[class*="popup"], [class*="dropdown"], [class*="menu"], [role="listbox"]')).filter(el => el.offsetParent !== null);
          const options = Array.from(document.querySelectorAll('[class*="option"], [role="option"], li')).filter(o => {
            const rect = o.getBoundingClientRect();
            return o.offsetParent !== null && rect.height > 0 && rect.width > 50;
          });

          return JSON.stringify({
            popupCount: popups.length,
            options: options.map(o => {
              const rect = o.getBoundingClientRect();
              return {
                text: o.textContent.trim().substring(0, 20),
                x: Math.round(rect.x + rect.width/2),
                y: Math.round(rect.y + rect.height/2)
              };
            }).slice(0, 15)
          });
        })()
      `);
      console.log(`  Options:`, opts);

      const optData = JSON.parse(opts);
      if (optData.options.length > 0) {
        const match = optData.options.find(o => o.text.includes(target) || o.text.toLowerCase().includes(target.toLowerCase()));
        if (match) {
          console.log(`  Clicking "${match.text}" at (${match.x}, ${match.y})`);
          await cdpClick(match.x, match.y);
          await sleep(500);
        } else {
          console.log(`  No match for "${target}". Closing.`);
          await pressKey("Escape", "Escape", 27);
        }
      }
    }
  }

  // Step 4: Check for the actual error source
  console.log("\n=== Step 4: Debug error ===");
  const debugInfo = await eval_(`
    (function() {
      // Check all error messages in detail
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], .alert'));
      const errorDetails = errors.map(e => ({
        text: e.textContent.trim().substring(0, 100),
        class: e.className?.substring?.(0, 40) || '',
        parent: e.parentElement?.className?.substring?.(0, 40) || '',
        visible: e.offsetParent !== null
      }));

      // Check form validation state
      const form = document.querySelector('form');
      const invalidFields = form ? Array.from(form.querySelectorAll(':invalid')).map(el => ({
        tag: el.tagName,
        name: el.name,
        value: el.value?.substring(0, 20),
        validity: el.validity ? {
          valid: el.validity.valid,
          rangeUnderflow: el.validity.rangeUnderflow,
          valueMissing: el.validity.valueMissing,
          typeMismatch: el.validity.typeMismatch
        } : null
      })) : [];

      // Get React form state if possible
      const allPriceInputs = Array.from(document.querySelectorAll('.price-input, input[type="number"]'));

      return JSON.stringify({
        errorDetails,
        invalidFields,
        priceValues: allPriceInputs.map(i => ({ name: i.name, value: i.value, min: i.min, valid: i.validity?.valid })),
        // Check if there's a "predefined options" section
        predefinedSection: document.body.innerText.includes('predefined') ?
          document.body.innerText.substring(
            Math.max(0, document.body.innerText.indexOf('predefined') - 100),
            document.body.innerText.indexOf('predefined') + 200
          ) : 'not found'
      });
    })()
  `);
  console.log("Debug:", debugInfo);

  // Step 5: Just save (there might not be an actual blocking error)
  console.log("\n=== Step 5: Save ===");
  await eval_(`
    Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Save & Preview')?.click()
  `);
  await sleep(5000);

  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      step: new URLSearchParams(window.location.search).get('step'),
      errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]')).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 0).slice(0, 5)
    })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
