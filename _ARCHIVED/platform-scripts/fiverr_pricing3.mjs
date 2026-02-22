// Fix pricing: use CDP clicks for prices, fix fine-tuning, revisions
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
  return { ws, send, eval_, cdpClick, pressKey, typeText };
}

async function main() {
  const { ws, send, eval_, cdpClick, pressKey, typeText } = await connect();

  // Step 1: Investigate the price input mechanism
  console.log("=== Step 1: Price input analysis ===");
  const priceAnalysis = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const priceRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('price'));
      if (!priceRow) return 'no price row';

      const cells = [];
      for (let i = 1; i <= 3; i++) {
        const cell = priceRow.cells[i];
        if (!cell) continue;

        const input = cell.querySelector('input[type="number"]');
        const allInputs = Array.from(cell.querySelectorAll('input'));
        const allDivs = Array.from(cell.querySelectorAll('div')).filter(d => d.children.length === 0);

        // Check React fiber for any props
        let fiberInfo = null;
        if (input) {
          for (const key of Object.keys(input)) {
            if (key.startsWith('__reactFiber')) {
              let fiber = input[key];
              let current = fiber;
              for (let d = 0; d < 15; d++) {
                const props = current?.memoizedProps;
                if (props?.onChange || props?.onBlur) {
                  fiberInfo = { depth: d, hasOnChange: !!props.onChange, hasOnBlur: !!props.onBlur, min: props.min, max: props.max, step: props.step };
                  break;
                }
                current = current?.return;
              }
              break;
            }
          }
        }

        const rect = input?.getBoundingClientRect();
        cells.push({
          col: i,
          value: input?.value,
          type: input?.type,
          min: input?.min,
          max: input?.max,
          step: input?.step,
          x: rect ? Math.round(rect.x + rect.width/2) : null,
          y: rect ? Math.round(rect.y + rect.height/2) : null,
          allInputCount: allInputs.length,
          fiberInfo,
          cellHTML: cell.innerHTML.substring(0, 200)
        });
      }
      return JSON.stringify(cells);
    })()
  `);
  console.log("Price analysis:", priceAnalysis);

  // Step 2: Set prices using CDP keyboard - click, select all, type new value
  console.log("\n=== Step 2: Set prices via CDP keyboard ===");
  const prices = JSON.parse(priceAnalysis);

  const targetPrices = { 1: '90', 2: '250', 3: '500' };

  for (const cellInfo of prices) {
    if (!cellInfo.x) continue;
    const target = targetPrices[cellInfo.col];
    if (!target) continue;

    console.log(`Setting col ${cellInfo.col} to $${target} (currently $${cellInfo.value})...`);

    // Click the input to focus it
    await cdpClick(cellInfo.x, cellInfo.y);
    await sleep(300);

    // Select all text (Ctrl+A)
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 2 }); // 2 = ctrl
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", windowsVirtualKeyCode: 65 });
    await sleep(100);

    // Type new value
    await typeText(target);
    await sleep(200);

    // Tab away to trigger blur/change
    await pressKey("Tab", "Tab", 9);
    await sleep(500);
  }

  // Step 3: Fix Fine-tuning checkbox (Premium only)
  console.log("\n=== Step 3: Fix checkboxes via CDP ===");

  // Get coordinates of the Fine-tuning checkboxes
  const cbCoords = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const results = {};

      for (const row of rows) {
        const label = (row.cells?.[0]?.textContent?.trim() || '').substring(0, 30);

        for (let i = 1; i <= 3; i++) {
          const cb = row.cells?.[i]?.querySelector('input[type="checkbox"]');
          if (!cb) continue;
          const el = cb.closest('label') || cb;
          const rect = el.getBoundingClientRect();

          if (!results[label]) results[label] = {};
          results[label][i] = {
            checked: cb.checked,
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2)
          };
        }
      }
      return JSON.stringify(results);
    })()
  `);
  console.log("Checkbox coords:", cbCoords);

  const cbData = JSON.parse(cbCoords);

  // Fix fine-tuning: should be checked for Premium (col 3) only
  for (const [label, cols] of Object.entries(cbData)) {
    if (label.toLowerCase().includes('fine-tun')) {
      // Check col 3 if not checked
      if (cols[3] && !cols[3].checked) {
        console.log(`  Clicking Fine-tuning Premium at (${cols[3].x}, ${cols[3].y})`);
        await cdpClick(cols[3].x, cols[3].y);
        await sleep(400);
      }
    }
  }

  // Step 4: Fix revisions dropdown
  console.log("\n=== Step 4: Fix revisions ===");

  // Find revision dropdown triggers
  const revInfo = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const revRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('revision'));
      if (!revRow) return 'no revision row';

      const cells = [];
      for (let i = 1; i <= 3; i++) {
        const cell = revRow.cells[i];
        if (!cell) continue;
        const hidden = cell.querySelector('input[type="hidden"]');
        // The visible element is likely a custom dropdown
        const clickable = cell.querySelector('[class*="dropdown"], [class*="select"], [role="listbox"], [role="button"]') || cell.children[0];
        if (clickable) {
          const rect = clickable.getBoundingClientRect();
          cells.push({
            col: i,
            currentValue: hidden?.value,
            visibleText: clickable.textContent.trim().substring(0, 20),
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2),
            class: clickable.className?.substring?.(0, 30) || ''
          });
        }
      }
      return JSON.stringify(cells);
    })()
  `);
  console.log("Revision dropdowns:", revInfo);

  const revData = JSON.parse(revInfo);
  const targetRevs = { 1: '2', 2: '3', 3: 'unlimited' };

  for (const rev of (Array.isArray(revData) ? revData : [])) {
    const target = targetRevs[rev.col];
    if (!target) continue;

    console.log(`\nSetting revision col ${rev.col} to "${target}" (current: ${rev.currentValue})...`);
    await cdpClick(rev.x, rev.y);
    await sleep(1000);

    // Find the options in the dropdown
    const optResult = await eval_(`
      (function() {
        // Look for dropdown options anywhere on page
        const options = Array.from(document.querySelectorAll('[class*="option"], [role="option"], [class*="dropdown-item"], [class*="menu-item"]')).filter(o => o.offsetParent !== null);
        const match = options.find(o => {
          const t = o.textContent.trim().toLowerCase();
          return t === '${target}' || t.includes('${target}');
        });
        if (match) {
          const rect = match.getBoundingClientRect();
          return JSON.stringify({ text: match.textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ options: options.map(o => o.textContent.trim()).slice(0, 15) });
      })()
    `);
    console.log(`  Options:`, optResult);

    const optData = JSON.parse(optResult);
    if (optData.x) {
      await cdpClick(optData.x, optData.y);
      await sleep(500);
    } else {
      // Close the dropdown
      await pressKey("Escape", "Escape", 27);
      await sleep(300);
    }
  }

  // Step 5: Verify and save
  console.log("\n=== Step 5: Verify ===");
  const final = await eval_(`
    JSON.stringify({
      prices: (() => {
        const rows = Array.from(document.querySelectorAll('tr'));
        const priceRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('price'));
        if (!priceRow) return [];
        return [1,2,3].map(i => priceRow.cells[i]?.querySelector('input')?.value);
      })(),
      revisions: (() => {
        const rows = Array.from(document.querySelectorAll('tr'));
        const revRow = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('revision'));
        if (!revRow) return [];
        return [1,2,3].map(i => revRow.cells[i]?.querySelector('input[type="hidden"]')?.value || revRow.cells[i]?.textContent?.trim()?.substring(0, 10));
      })(),
      fineTuning: (() => {
        const rows = Array.from(document.querySelectorAll('tr'));
        const row = rows.find(r => r.cells?.[0]?.textContent?.toLowerCase()?.includes('fine'));
        if (!row) return [];
        return [1,2,3].map(i => row.cells[i]?.querySelector('input[type="checkbox"]')?.checked);
      })(),
      errors: Array.from(document.querySelectorAll('[class*="error"]')).map(e => e.textContent.trim().substring(0, 80)).filter(t => t.length > 0)
    })
  `);
  console.log("Final:", final);

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
