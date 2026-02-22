// Set pricing by table position (no name attrs)
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
  return { ws, send, eval_, cdpClick };
}

async function main() {
  const { ws, send, eval_, cdpClick } = await connect();

  // Helper: set value of a field found by row label and column index
  const setByPosition = async (rowLabel, col, value) => {
    return await eval_(`
      (function() {
        const rows = Array.from(document.querySelectorAll('tr'));
        const row = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('${rowLabel.toLowerCase()}'));
        if (!row) return 'row not found: ${rowLabel}';

        const cell = row.cells[${col}];
        if (!cell) return 'cell not found: col ${col}';

        const el = cell.querySelector('textarea') || cell.querySelector('input:not([type="hidden"]):not([type="checkbox"])') || cell.querySelector('input[type="number"]');
        if (!el) return 'no input in cell';

        const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(el, ${JSON.stringify(value)});
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        return 'set to: ' + el.value.substring(0, 30);
      })()
    `);
  };

  // Helper: click a dropdown value (for delivery time, revisions which use custom dropdowns)
  const clickDropdownOption = async (rowLabel, col, targetText) => {
    // First click the dropdown trigger in the cell
    const coords = await eval_(`
      (function() {
        const rows = Array.from(document.querySelectorAll('tr'));
        const row = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('${rowLabel.toLowerCase()}'));
        if (!row) return null;
        const cell = row.cells[${col}];
        if (!cell) return null;
        // Find the dropdown trigger (usually a div that shows the current value)
        const trigger = cell.querySelector('[class*="dropdown"], [class*="select"], [class*="custom-select"], button, [role="button"]') || cell.querySelector('div');
        if (trigger) {
          const rect = trigger.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return null;
      })()
    `);

    if (!coords) return `dropdown trigger not found for ${rowLabel} col ${col}`;
    const { x, y } = JSON.parse(coords);
    await cdpClick(x, y);
    await sleep(800);

    // Find and click the target option
    const result = await eval_(`
      (function() {
        const options = Array.from(document.querySelectorAll('[class*="option"], [class*="dropdown-item"], [role="option"], li')).filter(o => o.offsetParent !== null);
        const target = options.find(o => o.textContent.trim().toLowerCase().includes('${targetText.toLowerCase()}'));
        if (target) {
          target.click();
          return 'selected: ' + target.textContent.trim();
        }
        return 'option not found: ${targetText}. Available: ' + options.map(o => o.textContent.trim()).slice(0, 10).join(', ');
      })()
    `);
    return result;
  };

  // Step 1: Update package titles
  console.log("=== Step 1: Update titles ===");
  console.log(await setByPosition('title', 1, 'Basic MCP Tool'));
  console.log(await setByPosition('title', 2, 'Standard MCP Server'));
  console.log(await setByPosition('title', 3, 'Full MCP Suite'));
  await sleep(300);

  // Step 2: Update descriptions
  console.log("\n=== Step 2: Update descriptions ===");
  console.log(await setByPosition('description', 1, 'Single MCP tool connecting AI to one API or data source'));
  console.log(await setByPosition('description', 2, 'MCP server with 3-5 tools for comprehensive AI-system integration'));
  console.log(await setByPosition('description', 3, 'Complete MCP suite with unlimited tools, documentation, and deployment'));
  await sleep(300);

  // Step 3: Set delivery times via dropdown clicks
  console.log("\n=== Step 3: Set delivery times ===");
  // Check current delivery time structure
  const deliveryInfo = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const deliveryRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('delivery'));
      if (!deliveryRow) return 'delivery row not found';

      const cells = [];
      for (let i = 1; i <= 3; i++) {
        const cell = deliveryRow.cells[i];
        if (!cell) continue;
        const hidden = cell.querySelector('input[type="hidden"]');
        const visible = cell.querySelector('[class*="dropdown"], [class*="select"], [role="button"], button');
        const allChildren = Array.from(cell.querySelectorAll('*')).map(el => ({
          tag: el.tagName,
          class: el.className.substring(0, 30),
          text: el.textContent.trim().substring(0, 20)
        })).slice(0, 5);
        cells.push({
          col: i,
          hiddenValue: hidden?.value,
          visibleText: visible?.textContent?.trim(),
          children: allChildren
        });
      }
      return JSON.stringify(cells);
    })()
  `);
  console.log("Delivery structure:", deliveryInfo);

  // Try clicking delivery dropdown for each column
  for (const [col, days] of [[1, '7'], [2, '14'], [3, '21']]) {
    const r = await clickDropdownOption('delivery', col, days);
    console.log(`  Col ${col} (${days} days): ${r}`);
    await sleep(500);
  }

  // Step 4: Set prices (min $90)
  console.log("\n=== Step 4: Set prices ===");
  // Prices: Basic $90, Standard $250, Premium $500

  // The price inputs are type="number" - find them directly
  const priceResult = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const priceRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('price'));
      if (!priceRow) return 'price row not found';

      const results = [];
      const prices = [null, 90, 250, 500]; // col 0 is label

      for (let i = 1; i <= 3; i++) {
        const cell = priceRow.cells[i];
        if (!cell) continue;
        const input = cell.querySelector('input[type="number"]');
        if (input) {
          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          setter.call(input, prices[i].toString());
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          input.dispatchEvent(new Event('blur', { bubbles: true }));
          results.push('col' + i + ': $' + input.value);
        }
      }
      return results.join(', ');
    })()
  `);
  console.log("Prices:", priceResult);

  // Step 5: Check/set feature checkboxes
  console.log("\n=== Step 5: Feature checkboxes ===");
  const checkboxResult = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const results = [];

      for (const row of rows) {
        const label = row.cells?.[0]?.textContent?.trim()?.substring(0, 30) || '';
        const cbs = [];
        for (let i = 1; i <= 3; i++) {
          const cell = row.cells?.[i];
          const cb = cell?.querySelector('input[type="checkbox"]');
          if (cb) {
            cbs.push({ col: i, checked: cb.checked });
          }
        }
        if (cbs.length > 0) {
          results.push({ label, checkboxes: cbs });
        }
      }
      return JSON.stringify(results);
    })()
  `);
  console.log("Checkboxes:", checkboxResult);

  // Set checkboxes based on tier:
  // Integration: all 3
  // Database: standard + premium
  // Fine-tuning: premium only
  // Source code: all 3
  // Comments: standard + premium
  const cbSettings = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const results = [];

      for (const row of rows) {
        const label = (row.cells?.[0]?.textContent?.trim() || '').toLowerCase();

        let wanted = {};
        if (label.includes('integration of an ai') || label.includes('source code')) {
          wanted = { 1: true, 2: true, 3: true };
        } else if (label.includes('database') || label.includes('detailed code')) {
          wanted = { 1: false, 2: true, 3: true };
        } else if (label.includes('fine-tun')) {
          wanted = { 1: false, 2: false, 3: true };
        }

        if (Object.keys(wanted).length === 0) continue;

        for (let i = 1; i <= 3; i++) {
          const cb = row.cells?.[i]?.querySelector('input[type="checkbox"]');
          if (!cb) continue;
          if (wanted[i] !== undefined && cb.checked !== wanted[i]) {
            cb.click();
            results.push(label.substring(0, 20) + ' col' + i + ': ' + (wanted[i] ? 'checked' : 'unchecked'));
          }
        }
      }
      return results.join(', ');
    })()
  `);
  console.log("Checkbox changes:", cbSettings);

  // Step 6: Set revisions via dropdown
  console.log("\n=== Step 6: Set revisions ===");
  for (const [col, revs] of [[1, '2'], [2, '3'], [3, 'unlimited']]) {
    const r = await clickDropdownOption('revision', col, revs);
    console.log(`  Col ${col}: ${r}`);
    await sleep(500);
  }

  // Step 7: Final check & save
  console.log("\n=== Step 7: Final state ===");
  const finalState = await eval_(`
    JSON.stringify({
      rows: Array.from(document.querySelectorAll('tr')).map(row => {
        const label = row.cells?.[0]?.textContent?.trim()?.substring(0, 25) || '';
        const vals = [];
        for (let i = 1; i <= 3; i++) {
          const el = row.cells?.[i]?.querySelector('input, textarea, select');
          if (el) vals.push(el.type === 'checkbox' ? (el.checked ? 'Y' : 'N') : el.value.substring(0, 15));
          else vals.push(row.cells?.[i]?.textContent?.trim()?.substring(0, 15) || '');
        }
        return vals.length > 0 ? label + ': ' + vals.join(' | ') : null;
      }).filter(Boolean),
      errors: Array.from(document.querySelectorAll('[class*="error"]')).map(e => e.textContent.trim().substring(0, 80)).filter(t => t.length > 0)
    })
  `);
  console.log("State:", finalState);

  // Save
  console.log("\n=== Saving... ===");
  await eval_(`
    Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Save & Preview')?.click()
  `);
  await sleep(5000);

  const afterSave = await eval_(`
    JSON.stringify({ url: window.location.href, errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]')).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 0).slice(0, 5) })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
