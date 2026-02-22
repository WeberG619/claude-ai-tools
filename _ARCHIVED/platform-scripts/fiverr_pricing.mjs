// Set pricing for gig #1: MCP server
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

  // Step 1: Analyze the pricing page structure
  console.log("=== Step 1: Analyze pricing page ===");
  const pageInfo = await eval_(`
    JSON.stringify({
      url: window.location.href,
      bodySnippet: document.body.innerText.substring(0, 800),
      buttons: Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null).map(b => b.textContent.trim()).filter(t => t.length > 0 && t.length < 30)
    })
  `);
  console.log("Page:", pageInfo);

  // Step 2: Map all pricing table fields
  console.log("\n=== Step 2: Map pricing fields ===");
  const fieldMap = await eval_(`
    (function() {
      const rows = Array.from(document.querySelectorAll('tr'));
      const result = [];

      for (const row of rows) {
        const cells = Array.from(row.children);
        if (cells.length < 2) continue;

        const label = cells[0]?.textContent?.trim() || '';
        const fields = [];

        for (let i = 1; i < cells.length; i++) {
          const cell = cells[i];
          const input = cell.querySelector('input');
          const textarea = cell.querySelector('textarea');
          const select = cell.querySelector('select');

          if (input) {
            fields.push({ col: i, type: 'input', inputType: input.type, name: input.name, value: input.value, placeholder: input.placeholder });
          }
          if (textarea) {
            fields.push({ col: i, type: 'textarea', name: textarea.name, value: textarea.value.substring(0, 30) });
          }
          if (select) {
            fields.push({ col: i, type: 'select', name: select.name, value: select.value, options: Array.from(select.options).map(o => ({ text: o.text.trim(), value: o.value })).slice(0, 10) });
          }
        }

        if (fields.length > 0) {
          result.push({ label: label.substring(0, 40), fields });
        }
      }

      return JSON.stringify(result);
    })()
  `);
  console.log("Fields:", fieldMap);

  const fields = JSON.parse(fieldMap);

  // Helper to set field value (React-compatible)
  const setField = async (name, value, isTextarea = false) => {
    return await eval_(`
      (function() {
        const el = document.querySelector('[name="${name}"]');
        if (!el) return 'not found: ${name}';
        const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
        setter.call(el, ${JSON.stringify(value)});
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        return 'set ' + el.name + ' = ' + el.value.substring(0, 30);
      })()
    `);
  };

  const setSelect = async (name, targetValue) => {
    return await eval_(`
      (function() {
        const sel = document.querySelector('[name="${name}"]');
        if (!sel) return 'not found: ${name}';
        const opt = Array.from(sel.options).find(o => o.value === '${targetValue}' || o.text.includes('${targetValue}'));
        if (opt) {
          sel.value = opt.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          return 'set to: ' + opt.text;
        }
        return 'no match for "${targetValue}". Options: ' + Array.from(sel.options).map(o => o.value + '=' + o.text.substring(0, 20)).join(', ');
      })()
    `);
  };

  // Step 3: Fill pricing fields
  console.log("\n=== Step 3: Fill pricing ===");

  // Pricing:
  // Basic ($150): 1 MCP tool, 7 day delivery, 2 revisions
  // Standard ($350): 3-5 MCP tools, 14 day delivery, 3 revisions
  // Premium ($750): Full MCP suite, 21 day delivery, unlimited revisions

  const pricing = {
    names: { 1: 'Basic MCP', 2: 'Standard MCP', 3: 'Full MCP Suite' },
    descriptions: {
      1: 'Single MCP tool connecting your AI to one data source or API endpoint',
      2: 'MCP server with 3-5 tools for comprehensive AI integration with your systems',
      3: 'Complete MCP server suite with unlimited tools, full documentation, and deployment support'
    },
    prices: { 1: '150', 2: '350', 3: '750' },
    delivery: { 1: '7', 2: '14', 3: '21' },
    revisions: { 1: '2', 2: '3', 3: '999' } // 999 or similar for unlimited
  };

  for (const row of fields) {
    const label = row.label.toLowerCase();

    for (const field of row.fields) {
      const col = field.col;
      let result = null;

      if ((label.includes('name') || label.includes('package')) && !label.includes('file')) {
        if (pricing.names[col]) {
          result = await setField(field.name, pricing.names[col], field.type === 'textarea');
        }
      } else if (label.includes('descri')) {
        if (pricing.descriptions[col]) {
          result = await setField(field.name, pricing.descriptions[col], true);
        }
      } else if (label.includes('price')) {
        if (pricing.prices[col]) {
          result = await setField(field.name, pricing.prices[col]);
        }
      } else if (label.includes('delivery') && field.type === 'select') {
        if (pricing.delivery[col]) {
          result = await setSelect(field.name, pricing.delivery[col]);
        }
      } else if (label.includes('revision') && field.type === 'select') {
        if (pricing.revisions[col]) {
          result = await setSelect(field.name, pricing.revisions[col]);
        }
      }

      if (result) console.log(`  ${row.label} [col${col}]: ${result}`);
    }
  }

  // Step 4: Check for any extra rows/fields
  console.log("\n=== Step 4: Extra fields ===");
  const extraCheck = await eval_(`
    JSON.stringify({
      allFieldValues: Array.from(document.querySelectorAll('tr')).map(row => {
        const label = row.cells?.[0]?.textContent?.trim()?.substring(0, 30) || '';
        const values = [];
        for (let i = 1; i < (row.cells?.length || 0); i++) {
          const el = row.cells[i].querySelector('input, textarea, select');
          if (el) values.push(el.value.substring(0, 20));
        }
        return values.length > 0 ? { label, values } : null;
      }).filter(Boolean),
      errors: Array.from(document.querySelectorAll('[class*="error"]')).map(e => e.textContent.trim().substring(0, 80)).filter(t => t.length > 0)
    })
  `);
  console.log("Extra check:", extraCheck);

  // Step 5: Save
  console.log("\n=== Step 5: Save ===");
  const saved = await eval_(`
    (function() {
      const btn = Array.from(document.querySelectorAll('button')).find(b =>
        b.textContent.trim() === 'Save & Continue' ||
        b.textContent.trim() === 'Save & Preview' ||
        b.textContent.trim() === 'Save'
      );
      if (btn) { btn.click(); return 'clicked: ' + btn.textContent.trim(); }
      return 'no save button. Buttons: ' + Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).filter(t => t.length > 0).join(', ');
    })()
  `);
  console.log("Save:", saved);
  await sleep(5000);

  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]')).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 0).slice(0, 5)
    })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
