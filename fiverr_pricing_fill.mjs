// Fill Fiverr pricing page (Step 2) and save
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function typeInField(send, eval_, selector, index, text) {
  // Focus and clear the field, then type
  await eval_(`
    const els = document.querySelectorAll('${selector}');
    const el = els[${index}];
    if (el) {
      el.scrollIntoView({ block: 'center' });
      el.focus();
      el.click();
    }
    return el ? 'ok' : 'not found';
  `);
  await sleep(200);
  // Select all and delete existing content
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);
  // Type new text
  await send("Input.insertText", { text });
  await sleep(300);
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // === Step 1: Fill package titles ===
  console.log("=== Filling Package Titles ===");
  const titles = ["Basic Data Entry", "Standard Data Entry", "Premium Data Entry"];
  for (let i = 0; i < 3; i++) {
    await typeInField(send, eval_, '.pkg-title-input', i, titles[i]);
    console.log(`Title ${i}: "${titles[i]}"`);
  }

  // === Step 2: Fill package descriptions ===
  console.log("\n=== Filling Package Descriptions ===");
  const descriptions = [
    "Up to 1 hour of accurate data entry, Excel spreadsheet work, or data processing",
    "Up to 2 hours of accurate data entry, Excel spreadsheet work, or data processing with revisions",
    "Up to 3 hours of comprehensive data entry, Excel spreadsheet work, and data processing with unlimited revisions"
  ];
  for (let i = 0; i < 3; i++) {
    await typeInField(send, eval_, '.pkg-description-input', i, descriptions[i]);
    console.log(`Description ${i}: done`);
  }

  // === Step 3: Set delivery times ===
  console.log("\n=== Setting Delivery Times ===");
  // First, inspect the delivery time dropdowns
  let r = await eval_(`
    // Find delivery time selectors - they should be custom dropdowns
    const deliveryDropdowns = Array.from(document.querySelectorAll('[class*="delivery"], select, [class*="select"], [class*="dropdown"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 40),
        y: Math.round(el.getBoundingClientRect().y),
        x: Math.round(el.getBoundingClientRect().x),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));

    // Also find elements that say "DELIVERY TIME"
    const dtLabels = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.trim() === 'DELIVERY TIME' && el.children.length === 0)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y),
        nextSibling: el.nextElementSibling?.tagName,
        parent: el.parentElement?.tagName + '.' + (el.parentElement?.className?.toString() || '').substring(0, 40)
      }));

    // Find custom select/dropdown elements in the pricing table area
    const customSelects = Array.from(document.querySelectorAll('.duration-select, [class*="custom-select"], [class*="CustomSelect"], [class*="select-wrapper"], [class*="SelectWrapper"]'))
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        html: el.outerHTML?.substring(0, 300)
      }));

    return JSON.stringify({ deliveryDropdowns: deliveryDropdowns.slice(0, 10), dtLabels, customSelects });
  `);
  console.log("Delivery dropdowns:", r);

  // Get the exact structure around delivery time
  r = await eval_(`
    // Find all elements that look like dropdowns in the pricing table
    const pricingTable = document.querySelector('[class*="gig_upcrate-package"]') || document.querySelector('form');
    if (!pricingTable) return JSON.stringify({ error: 'no pricing table' });

    // Look for select-like elements
    const selects = Array.from(pricingTable.querySelectorAll('select'));
    const selectInfo = selects.map(s => ({
      name: s.name || '',
      class: (s.className?.toString() || '').substring(0, 60),
      options: Array.from(s.options).map(o => ({ value: o.value, text: o.text })),
      y: Math.round(s.getBoundingClientRect().y),
      visible: s.offsetParent !== null
    }));

    // Look for custom dropdown triggers
    const triggers = Array.from(pricingTable.querySelectorAll('[class*="trigger"], [class*="Trigger"], [role="listbox"], [role="combobox"], [class*="duration"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 40),
        y: Math.round(el.getBoundingClientRect().y),
        rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y), w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height) }
      }));

    return JSON.stringify({ selects: selectInfo, triggers: triggers.slice(0, 10) });
  `);
  console.log("Selects & triggers:", r);

  // Look for the actual dropdown containers near the "DELIVERY TIME" text
  r = await eval_(`
    // Get parent rows of the pricing table
    const table = document.querySelector('table') || document.querySelector('[class*="package-table"]');
    if (!table) {
      // Try to find delivery time elements by looking at specific y-ranges
      const allEls = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 600 && rect.y < 1200 && rect.height > 20 && rect.height < 60 && rect.width > 100;
        })
        .map(el => ({
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 60),
          text: el.textContent?.trim()?.substring(0, 40),
          y: Math.round(el.getBoundingClientRect().y),
          h: Math.round(el.getBoundingClientRect().height)
        }));
      return JSON.stringify({ noTable: true, nearbyEls: allEls.slice(0, 20) });
    }

    // Get table rows
    const rows = Array.from(table.querySelectorAll('tr'));
    const rowInfo = rows.map(row => ({
      cells: Array.from(row.querySelectorAll('td, th')).map(cell => ({
        text: cell.textContent?.trim()?.substring(0, 40),
        html: cell.innerHTML?.substring(0, 200),
        class: (cell.className?.toString() || '').substring(0, 40)
      })),
      y: Math.round(row.getBoundingClientRect().y)
    }));

    return JSON.stringify({ rows: rowInfo });
  `);
  console.log("\nTable structure:", r);

  // Let me look at the actual delivery time row HTML
  r = await eval_(`
    // Find the row that contains "DELIVERY TIME"
    const allRows = Array.from(document.querySelectorAll('tr'));
    const dtRow = allRows.find(r => r.textContent.includes('DELIVERY TIME'));
    if (!dtRow) return JSON.stringify({ error: 'delivery time row not found' });
    return JSON.stringify({
      html: dtRow.innerHTML.substring(0, 2000),
      y: Math.round(dtRow.getBoundingClientRect().y)
    });
  `);
  console.log("\nDelivery time row:", r);

  const dtInfo = JSON.parse(r);
  if (dtInfo.html) {
    // Parse the HTML to find dropdown selectors
    console.log("\n=== Clicking delivery time dropdowns ===");

    // Get coordinates of the delivery time dropdowns
    r = await eval_(`
      const dtRow = Array.from(document.querySelectorAll('tr'))
        .find(r => r.textContent.includes('DELIVERY TIME'));
      if (!dtRow) return JSON.stringify({ error: 'no dt row' });

      // Find clickable elements in the delivery time cells
      const cells = Array.from(dtRow.querySelectorAll('td'));
      const dropdowns = cells.map((cell, i) => {
        const clickable = cell.querySelector('[class*="select"], [class*="dropdown"], [class*="trigger"], button, [role="button"], [role="listbox"]') || cell;
        const rect = clickable.getBoundingClientRect();
        return {
          cellIndex: i,
          tag: clickable.tagName,
          class: (clickable.className?.toString() || '').substring(0, 60),
          text: clickable.textContent?.trim()?.substring(0, 30),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          w: Math.round(rect.width),
          h: Math.round(rect.height)
        };
      });
      return JSON.stringify(dropdowns);
    `);
    console.log("Delivery dropdowns:", r);

    const dropdowns = JSON.parse(r);
    const deliveryDays = [1, 2, 3]; // Basic=1day, Standard=2days, Premium=3days

    for (let i = 0; i < Math.min(dropdowns.length, 3); i++) {
      const dd = dropdowns[i];
      if (dd.w < 10) continue; // Skip if too small (label cell)

      console.log(`\nClicking delivery dropdown ${i}: "${dd.text}" at (${dd.x}, ${dd.y})`);
      // Scroll into view first
      await eval_(`
        const dtRow = Array.from(document.querySelectorAll('tr'))
          .find(r => r.textContent.includes('DELIVERY TIME'));
        dtRow?.scrollIntoView({ block: 'center' });
      `);
      await sleep(300);

      // Re-get coordinates after scroll
      const newR = await eval_(`
        const dtRow = Array.from(document.querySelectorAll('tr'))
          .find(r => r.textContent.includes('DELIVERY TIME'));
        const cells = Array.from(dtRow.querySelectorAll('td'));
        const clickable = cells[${i}]?.querySelector('[class*="select"], [class*="dropdown"], [class*="trigger"], button, [role="button"]') || cells[${i}];
        if (!clickable) return JSON.stringify({ error: 'not found' });
        const rect = clickable.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      `);
      const coords = JSON.parse(newR);

      await clickAt(send, coords.x, coords.y);
      await sleep(500);

      // Look for dropdown options
      r = await eval_(`
        const options = Array.from(document.querySelectorAll('[class*="option"], [role="option"], li'))
          .filter(el => {
            if (!el.offsetParent) return false;
            const t = el.textContent.trim().toLowerCase();
            return t.includes('day') || t.includes('hour');
          })
          .map(el => ({
            text: el.textContent.trim().substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
            class: (el.className?.toString() || '').substring(0, 40)
          }));
        return JSON.stringify(options);
      `);
      const options = JSON.parse(r);
      console.log(`Options: ${options.map(o => o.text).join(', ')}`);

      if (options.length > 0) {
        // Find the matching day option
        const target = deliveryDays[i];
        const match = options.find(o => o.text.includes(`${target} day`) || o.text.includes(`${target} Day`)) ||
                      options.find(o => o.text.includes(`${target}`)) ||
                      options[Math.min(i, options.length - 1)];
        if (match) {
          console.log(`Selecting: "${match.text}"`);
          await clickAt(send, match.x, match.y);
          await sleep(300);
        }
      }
    }
  }

  // === Step 4: Set Revisions ===
  console.log("\n\n=== Setting Revisions ===");
  r = await eval_(`
    // Find the revisions row
    const allRows = Array.from(document.querySelectorAll('tr'));
    const revRow = allRows.find(r => r.textContent.includes('Revisions') || r.textContent.includes('REVISIONS'));
    if (!revRow) return JSON.stringify({ error: 'revisions row not found' });

    const cells = Array.from(revRow.querySelectorAll('td'));
    const dropdowns = cells.map((cell, i) => {
      const clickable = cell.querySelector('[class*="select"], [class*="dropdown"], [class*="trigger"], button, [role="button"]') || cell;
      const rect = clickable.getBoundingClientRect();
      return {
        cellIndex: i,
        text: clickable.textContent?.trim()?.substring(0, 30),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        w: Math.round(rect.width)
      };
    });
    revRow.scrollIntoView({ block: 'center' });
    return JSON.stringify(dropdowns);
  `);
  console.log("Revisions dropdowns:", r);

  const revDropdowns = JSON.parse(r);
  const revisions = [1, 2, 3]; // Basic=1, Standard=2, Premium=3

  for (let i = 0; i < Math.min(revDropdowns.length, 3); i++) {
    const dd = revDropdowns[i];
    if (dd.w < 10) continue;

    // Re-get coordinates after scroll
    const newR = await eval_(`
      const revRow = Array.from(document.querySelectorAll('tr'))
        .find(r => r.textContent.includes('Revisions'));
      const cells = Array.from(revRow.querySelectorAll('td'));
      const clickable = cells[${i}]?.querySelector('[class*="select"], [class*="dropdown"], button') || cells[${i}];
      if (!clickable) return JSON.stringify({ error: 'not found' });
      const rect = clickable.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const coords = JSON.parse(newR);

    console.log(`\nClicking revision dropdown ${i} at (${coords.x}, ${coords.y})`);
    await clickAt(send, coords.x, coords.y);
    await sleep(500);

    // Look for options
    r = await eval_(`
      const options = Array.from(document.querySelectorAll('[class*="option"], [role="option"], li'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 10 && el.getBoundingClientRect().height < 60)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(options);
    `);
    const options = JSON.parse(r);
    console.log(`Options: ${options.map(o => o.text).join(', ')}`);

    if (options.length > 0) {
      const target = revisions[i];
      // For revisions: match number or "unlimited"
      const match = options.find(o => o.text === `${target}`) ||
                    options.find(o => o.text.includes(`${target}`)) ||
                    (i === 2 ? options.find(o => o.text.toLowerCase().includes('unlimited')) : null) ||
                    options[Math.min(target - 1, options.length - 1)];
      if (match) {
        console.log(`Selecting: "${match.text}"`);
        await clickAt(send, match.x, match.y);
        await sleep(300);
      }
    }
  }

  // === Step 5: Set Prices ===
  console.log("\n\n=== Setting Prices ===");
  const prices = ["20", "35", "50"];
  for (let i = 0; i < 3; i++) {
    await typeInField(send, eval_, '.price-input', i, prices[i]);
    console.log(`Price ${i}: $${prices[i]}`);
  }

  // === Step 6: Verify and Save ===
  console.log("\n\n=== Verification ===");
  r = await eval_(`
    return JSON.stringify({
      pkg1: {
        title: document.querySelector('input[name="gig[packages][1][title]"]')?.value,
        desc: document.querySelector('input[name="gig[packages][1][description]"]')?.value?.substring(0, 50),
        duration: document.querySelector('input[name="gig[packages][1][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][1][price]"]')?.value
      },
      pkg2: {
        title: document.querySelector('input[name="gig[packages][2][title]"]')?.value,
        desc: document.querySelector('input[name="gig[packages][2][description]"]')?.value?.substring(0, 50),
        duration: document.querySelector('input[name="gig[packages][2][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][2][price]"]')?.value
      },
      pkg3: {
        title: document.querySelector('input[name="gig[packages][3][title]"]')?.value,
        desc: document.querySelector('input[name="gig[packages][3][description]"]')?.value?.substring(0, 50),
        duration: document.querySelector('input[name="gig[packages][3][duration]"]')?.value,
        price: document.querySelector('input[name="gig[packages][3][price]"]')?.value
      }
    });
  `);
  console.log("Hidden fields state:", r);

  // Click Save & Continue
  console.log("\n=== Saving ===");
  await eval_(`
    const btn = document.querySelector('.btn-submit') ||
      Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Save & Continue'));
    if (btn) { btn.scrollIntoView({ block: 'center' }); btn.click(); }
    return btn ? 'clicked' : 'not found';
  `);
  await sleep(5000);

  // Check result
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="validation"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 80)),
      preview: document.body?.innerText?.substring(0, 800)
    });
  `);
  console.log("\nAfter save:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
