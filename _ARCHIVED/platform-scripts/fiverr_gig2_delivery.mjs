// Find and set delivery times + missing fields on pricing page
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

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll to top of pricing table
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // Get full pricing table HTML structure
  let r = await eval_(`
    // Find the pricing table/container
    const table = document.querySelector('[class*="packages-table"], [class*="pricing-table"], table');
    if (!table) {
      // Try finding by the Scope & Pricing heading
      const heading = Array.from(document.querySelectorAll('h2, h3, [class*="heading"]'))
        .find(el => el.textContent.includes('Scope'));
      if (heading) {
        const container = heading.closest('section') || heading.parentElement;
        return JSON.stringify({
          containerClass: (container?.className?.toString() || '').substring(0, 80),
          html: container?.innerHTML?.substring(0, 2000) || 'no html'
        });
      }
    }
    if (table) {
      return JSON.stringify({
        tag: table.tagName,
        class: (table.className?.toString() || '').substring(0, 80),
        html: table.innerHTML.substring(0, 3000)
      });
    }
    return JSON.stringify({ error: 'no table' });
  `);
  console.log("Table structure:", r.substring(0, 500));

  // Find the DELIVERY TIME text and surrounding elements
  r = await eval_(`
    const allText = Array.from(document.querySelectorAll('*'))
      .filter(el => el.children.length === 0 && el.textContent.trim() === 'DELIVERY TIME')
      .map(el => {
        const parent = el.parentElement;
        const grandparent = parent?.parentElement;
        const row = el.closest('tr') || grandparent;
        return {
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 60),
          parentTag: parent?.tagName || '',
          parentClass: (parent?.className?.toString() || '').substring(0, 60),
          rowTag: row?.tagName || '',
          rowClass: (row?.className?.toString() || '').substring(0, 60),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        };
      });
    return JSON.stringify(allText);
  `);
  console.log("\nDELIVERY TIME elements:", r);

  // The delivery time and revision selectors are likely custom React dropdowns
  // Let's find them by looking at the row structure
  r = await eval_(`
    // Get all table rows with their cell structure
    const rows = Array.from(document.querySelectorAll('tr'))
      .filter(el => el.offsetParent !== null)
      .map(tr => {
        const cells = Array.from(tr.querySelectorAll('td, th'));
        return {
          rowText: tr.textContent.trim().substring(0, 60).replace(/\\n/g, ' '),
          cellCount: cells.length,
          y: Math.round(tr.getBoundingClientRect().y),
          cells: cells.map(td => ({
            text: td.textContent.trim().substring(0, 30),
            hasDropdown: !!td.querySelector('[class*="select"], [class*="dropdown"], [class*="picker"]'),
            hasCheckbox: !!td.querySelector('input[type="checkbox"]'),
            hasInput: !!td.querySelector('input[type="number"], input[type="text"]'),
            x: Math.round(td.getBoundingClientRect().x + td.getBoundingClientRect().width/2),
            y: Math.round(td.getBoundingClientRect().y + td.getBoundingClientRect().height/2)
          }))
        };
      });
    return JSON.stringify(rows);
  `);
  console.log("\nTable rows with cells:", r);
  const tableRows = JSON.parse(r);

  // Find rows with DELIVERY TIME and SELECT (revisions)
  const deliveryRow = tableRows.find(r => r.rowText.includes('DELIVERY TIME') || r.rowText.includes('Delivery Time'));
  const revisionRow = tableRows.find(r => r.rowText.includes('Revision') || r.rowText.includes('SELECT'));

  if (deliveryRow) {
    console.log("\n=== Delivery Time Row ===");
    console.log("Row:", JSON.stringify(deliveryRow));

    // Click each delivery cell (skip first which is the label)
    const dataCells = deliveryRow.cells.filter(c => !c.text.includes('Delivery'));
    for (let i = 0; i < dataCells.length; i++) {
      const cell = dataCells[i];
      if (cell.text === 'DELIVERY TIME' || cell.text === '') {
        console.log(`Clicking delivery cell ${i} at (${cell.x}, ${cell.y})`);
        await clickAt(send, cell.x, cell.y);
        await sleep(1000);

        // Look for any opened dropdown or popup
        r = await eval_(`
          const popups = Array.from(document.querySelectorAll('[class*="popup"], [class*="dropdown"], [class*="menu"], [role="listbox"], [class*="options"]'))
            .filter(el => {
              const rect = el.getBoundingClientRect();
              return el.offsetParent !== null && rect.height > 10 && rect.width > 10;
            })
            .map(el => ({
              class: (el.className?.toString() || '').substring(0, 60),
              text: el.textContent.trim().substring(0, 200),
              y: Math.round(el.getBoundingClientRect().y),
              children: el.children.length
            }));
          return JSON.stringify(popups);
        `);
        console.log("Popups after click:", r);

        // Also check the cell itself for internal dropdown
        r = await eval_(`
          const cell = document.elementFromPoint(${cell.x}, ${cell.y});
          if (cell) {
            const dd = cell.querySelector('[class*="select"], [class*="dropdown"]') || cell.closest('[class*="select"]');
            return JSON.stringify({
              cellTag: cell.tagName,
              cellClass: (cell.className?.toString() || '').substring(0, 60),
              ddClass: dd ? (dd.className?.toString() || '').substring(0, 60) : 'no dropdown',
              cellHTML: cell.innerHTML.substring(0, 300)
            });
          }
          return JSON.stringify({ error: 'no element at point' });
        `);
        console.log("Cell details:", r);

        // Click away to close any popup
        await clickAt(send, 300, 300);
        await sleep(300);
      }
    }
  }

  // Check what interactive elements are in the pricing area
  r = await eval_(`
    // Get all interactive elements within the package table area (y > 600, y < 1500)
    const interactive = Array.from(document.querySelectorAll('[class*="custom-select"], [class*="react-select"], [class*="orca-combo-box"], [class*="dropdown-toggle"], [class*="select-trigger"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 40) || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(interactive);
  `);
  console.log("\nCustom select elements:", r);

  // Try to take a screenshot via CDP to see the page
  r = await send("Page.captureScreenshot", { format: "png" });
  if (r.data) {
    const fs = await import('fs');
    fs.writeFileSync('/mnt/d/_CLAUDE-TOOLS/fiverr_pricing_screenshot.png', Buffer.from(r.data, 'base64'));
    console.log("\nScreenshot saved to /mnt/d/_CLAUDE-TOOLS/fiverr_pricing_screenshot.png");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
