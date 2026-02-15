// Check subcategory options and save gig overview
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
    if (r.exceptionDetails) { console.error("JS Err:", JSON.stringify(r.exceptionDetails).substring(0, 400)); return null; }
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  const { ws, send, eval_ } = await connect();

  // Step 1: Check all available subcategory options for "Programming & Tech"
  console.log("=== Step 1: List all subcategory options ===");
  const subOptions = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-3-input');
      if (!input) return 'subcategory input not found';

      let fiber = null;
      for (const key of Object.keys(input)) {
        if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
          fiber = input[key];
          break;
        }
      }
      if (!fiber) return 'no fiber';

      let current = fiber;
      let depth = 0;
      while (current && depth < 40) {
        const props = current.memoizedProps || current.pendingProps;
        if (props && props.options && props.options.length > 0 && props.onChange) {
          return JSON.stringify({
            options: props.options.map(o => ({ label: o.label, value: o.value })),
            currentValue: props.value ? { label: props.value.label, value: props.value.value } : null
          });
        }
        current = current.return;
        depth++;
      }
      return 'no options found';
    })()
  `);
  console.log("Subcategory options:", subOptions);

  // Parse and check if there's a better option than "Chatbot Development"
  if (subOptions && subOptions.startsWith('{')) {
    const parsed = JSON.parse(subOptions);
    console.log("\nAll subcategories:");
    parsed.options.forEach((o, i) => console.log(`  ${i}: ${o.label} (${o.value})`));
    console.log("\nCurrent:", parsed.currentValue?.label);

    // Look for "AI Applications" or "AI Apps" or similar
    const better = parsed.options.find(o =>
      o.label.toLowerCase().includes('ai app') ||
      o.label.toLowerCase().includes('ai agent') ||
      o.label.toLowerCase().includes('api') ||
      o.label.toLowerCase().includes('ai integration')
    );

    if (better && better.label !== parsed.currentValue?.label) {
      console.log(`\nSwitching to better subcategory: "${better.label}"...`);
      const switchResult = await eval_(`
        (function() {
          const input = document.querySelector('#react-select-3-input');
          let fiber = null;
          for (const key of Object.keys(input)) {
            if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
              fiber = input[key];
              break;
            }
          }

          let current = fiber;
          let depth = 0;
          while (current && depth < 40) {
            const props = current.memoizedProps || current.pendingProps;
            if (props && props.options && props.options.length > 0 && props.onChange) {
              const target = props.options.find(o => o.value === ${better.value});
              if (target) {
                props.onChange(target, { action: 'select-option', option: target });
                return 'switched to: ' + target.label;
              }
              return 'target value not found';
            }
            current = current.return;
            depth++;
          }
          return 'could not find onChange';
        })()
      `);
      console.log("Switch result:", switchResult);
      await sleep(1000);
    } else {
      console.log("Chatbot Development is the best fit, keeping it.");
    }
  }

  // Step 2: Check for any service type / nested subcategory selector
  console.log("\n=== Step 2: Check for service type selector ===");
  const serviceType = await eval_(`
    (function() {
      // Check for a third react-select
      const input4 = document.querySelector('#react-select-4-input');
      const input5 = document.querySelector('#react-select-5-input');

      const results = {};
      for (const [name, input] of [['select-4', input4], ['select-5', input5]]) {
        if (!input) { results[name] = 'not found'; continue; }
        let fiber = null;
        for (const key of Object.keys(input)) {
          if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
            fiber = input[key];
            break;
          }
        }
        if (!fiber) { results[name] = 'no fiber'; continue; }
        let current = fiber;
        let depth = 0;
        while (current && depth < 40) {
          const props = current.memoizedProps || current.pendingProps;
          if (props && props.options && props.options.length > 0) {
            results[name] = {
              options: props.options.map(o => o.label || o.value).slice(0, 20),
              value: props.value?.label
            };
            break;
          }
          current = current.return;
          depth++;
        }
        if (!results[name]) results[name] = 'no options found';
      }
      return JSON.stringify(results);
    })()
  `);
  console.log("Service type:", serviceType);

  // Step 3: Check for search tags input
  console.log("\n=== Step 3: Check page for tags/metadata ===");
  const pageState = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      // Check for tags input
      tagsInput: document.querySelector('[class*="tag"], [class*="Tag"], input[placeholder*="tag"]')?.outerHTML?.substring(0, 100) || 'none',
      // Check for positive keywords section
      keywords: document.querySelector('[class*="keyword"], [class*="Keyword"]')?.textContent?.substring(0, 100) || 'none',
      // Check for search tags
      searchTags: Array.from(document.querySelectorAll('[class*="search-tag"], [class*="SearchTag"]')).map(t => t.textContent.trim()),
      // All form buttons
      buttons: Array.from(document.querySelectorAll('button')).map(b => b.textContent.trim()).filter(t => t.length > 0 && t.length < 30),
      // Check for save/continue button
      saveBtn: Array.from(document.querySelectorAll('button, a')).find(b =>
        b.textContent.toLowerCase().includes('save') || b.textContent.toLowerCase().includes('continue')
      )?.textContent?.trim() || 'none'
    })
  `);
  console.log("Page state:", pageState);

  // Step 4: Look for the Save & Continue button and its coordinates
  console.log("\n=== Step 4: Find Save button ===");
  const saveCoords = await eval_(`
    (function() {
      const btns = Array.from(document.querySelectorAll('button, a'));
      const saveBtn = btns.find(b => {
        const t = b.textContent.trim().toLowerCase();
        return (t.includes('save') && t.includes('continue')) || t === 'save';
      });
      if (saveBtn) {
        const rect = saveBtn.getBoundingClientRect();
        return JSON.stringify({
          text: saveBtn.textContent.trim(),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          visible: rect.width > 0 && rect.height > 0
        });
      }

      // Also look for any primary action button at bottom
      const primary = btns.find(b => b.className.includes('primary') || b.className.includes('btn-primary'));
      if (primary) {
        const rect = primary.getBoundingClientRect();
        return JSON.stringify({
          text: primary.textContent.trim(),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          class: primary.className.substring(0, 50)
        });
      }

      return JSON.stringify({ allButtons: btns.map(b => b.textContent.trim()).filter(t => t.length > 0).slice(0, 20) });
    })()
  `);
  console.log("Save button:", saveCoords);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
