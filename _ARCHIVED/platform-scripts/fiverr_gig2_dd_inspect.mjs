// Inspect the delivery time dropdown internals and fix word counts
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

  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // Get the HTML of the first delivery time cell (Basic column)
  let r = await eval_(`
    const deliveryRow = Array.from(document.querySelectorAll('tr'))
      .find(tr => tr.textContent.includes('Delivery Time') && !tr.textContent.startsWith('Delivery'));
    if (!deliveryRow) return JSON.stringify({ error: 'no delivery row' });

    const cells = Array.from(deliveryRow.querySelectorAll('td'));
    // Second cell is Basic delivery time (first is label)
    const basicCell = cells[1];
    if (!basicCell) return JSON.stringify({ error: 'no basic cell' });

    return JSON.stringify({
      innerHTML: basicCell.innerHTML.substring(0, 1000),
      outerHTML: basicCell.outerHTML.substring(0, 1000),
      childElements: Array.from(basicCell.querySelectorAll('*')).map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        text: el.textContent?.trim()?.substring(0, 30) || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }))
    });
  `);
  console.log("Basic delivery cell:", r);
  const cellData = JSON.parse(r);

  if (cellData.childElements) {
    // Find the select/dropdown component inside
    const dropdown = cellData.childElements.find(el =>
      el.class.includes('select') || el.class.includes('dropdown') || el.class.includes('picker') || el.tag === 'SELECT'
    );
    console.log("\nDropdown element:", JSON.stringify(dropdown));

    if (dropdown) {
      console.log(`\nClicking dropdown at (${dropdown.x}, ${dropdown.y})`);
      await clickAt(send, dropdown.x, dropdown.y);
      await sleep(1500);

      // NOW check what appeared - be very specific, only look near the cell
      r = await eval_(`
        const cellY = ${dropdown.y};
        const cellX = ${dropdown.x};

        // Check for any new elements that appeared (menus, lists, etc.)
        const newEls = Array.from(document.querySelectorAll('*'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            // Must be visible, near the cell horizontally, and below it vertically
            return el.offsetParent !== null &&
                   rect.height > 5 && rect.height < 40 &&
                   rect.width > 30 && rect.width < 300 &&
                   Math.abs(rect.x - cellX) < 150 &&
                   rect.y > cellY - 20 &&
                   rect.y < cellY + 300 &&
                   el.children.length === 0 &&
                   el.textContent.trim().length > 0 &&
                   el.textContent.trim().length < 30;
          })
          .map(el => ({
            text: el.textContent.trim(),
            tag: el.tagName,
            class: (el.className?.toString() || '').substring(0, 60),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(newEls.slice(0, 20));
      `);
      console.log("Elements near dropdown:", r);
    }
  }

  // Also check for react-select style containers
  r = await eval_(`
    const reactSelects = Array.from(document.querySelectorAll('[class*="react-select"], [class*="orca-combo-box"], [class*="custom-select"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 850 && el.getBoundingClientRect().y < 1000)
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 30) || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(reactSelects);
  `);
  console.log("\nReact selects in delivery area:", r);

  // Check for native <select> elements that might be hidden/styled
  r = await eval_(`
    const allSelects = Array.from(document.querySelectorAll('select'));
    return JSON.stringify(allSelects.map(sel => ({
      name: sel.name || '',
      id: sel.id || '',
      class: (sel.className?.toString() || '').substring(0, 60),
      visible: sel.offsetParent !== null,
      display: getComputedStyle(sel).display,
      options: Array.from(sel.options).map(o => o.textContent.trim().substring(0, 20)).slice(0, 5),
      value: sel.value,
      y: Math.round(sel.getBoundingClientRect().y)
    })));
  `);
  console.log("\nAll <select> elements:", r);

  // Fix word counts - use React native value setter
  console.log("\n=== Fixing Word Counts ===");
  r = await eval_(`
    const wordInputs = Array.from(document.querySelectorAll('input[type="number"]'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 930 && el.getBoundingClientRect().y < 1000);

    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const counts = ['1000', '3000', '5000'];

    wordInputs.forEach((input, i) => {
      nativeSetter.call(input, counts[i] || '1000');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });

    return JSON.stringify(wordInputs.map(el => el.value));
  `);
  console.log("Word counts set:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
