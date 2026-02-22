// Change category from Writing & Translation to Programming & Tech
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.url.includes("edit") && t.type === "page");
  if (!tab) throw new Error("No Fiverr edit tab found");
  console.log(`Connected: ${tab.url}`);
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
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (r.exceptionDetails) {
      console.error("JS Error:", JSON.stringify(r.exceptionDetails).substring(0, 300));
      return null;
    }
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  const { ws, eval_ } = await connect();

  // Step 1: Open the main category dropdown
  console.log("=== Opening main category dropdown ===");
  const openResult = await eval_(`
    (function() {
      // Find the category react-select - it's the first one showing "WRITING & TRANSLATION"
      const input = document.querySelector('#react-select-2-input');
      if (!input) return 'input not found';

      // Click the dropdown indicator or the container to open
      const container = input.closest('[class*="container"]');
      const indicator = container?.querySelector('[class*="indicatorContainer"]') ||
                       container?.querySelector('[class*="DropdownIndicator"]') ||
                       container?.querySelector('svg')?.parentElement;

      // Try multiple approaches to open
      if (indicator) indicator.click();
      // Also simulate mouseDown on the control
      const control = container?.querySelector('[class*="control"]');
      if (control) {
        control.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      }
      input.focus();

      return 'dropdown opened';
    })()
  `);
  console.log(openResult);
  await sleep(1500);

  // Step 2: Check what options appeared
  const options1 = await eval_(`
    JSON.stringify(
      Array.from(document.querySelectorAll('[id*="react-select-2-option"]')).map(o => ({
        text: o.textContent.trim(),
        id: o.id
      }))
    )
  `);
  console.log("Main category options:", options1);

  // Step 3: If no options visible, try typing to filter
  if (!options1 || options1 === '[]') {
    console.log("No options visible, trying keyboard approach...");
    // Use CDP Input to type into the select
    await eval_(`
      (function() {
        const input = document.querySelector('#react-select-2-input');
        if (input) {
          input.focus();
          // Clear any existing value
          input.value = '';
          input.dispatchEvent(new Event('input', { bubbles: true }));
        }
      })()
    `);

    // Type "Prog" using CDP keyboard events
    const chars = 'Prog';
    for (const char of chars) {
      await eval_(`
        (function() {
          const input = document.querySelector('#react-select-2-input');
          if (input) {
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(input, input.value + '${char}');
            input.dispatchEvent(new Event('input', { bubbles: true }));
          }
        })()
      `);
      await sleep(200);
    }
    await sleep(1500);

    const options2 = await eval_(`
      JSON.stringify(
        Array.from(document.querySelectorAll('[id*="react-select"][id*="option"]')).map(o => ({
          text: o.textContent.trim(),
          id: o.id
        }))
      )
    `);
    console.log("Filtered options:", options2);
  }

  // Step 4: Select "Programming & Tech"
  const selectResult = await eval_(`
    (function() {
      const options = Array.from(document.querySelectorAll('[id*="react-select"][id*="option"]'));
      const target = options.find(o => o.textContent.toLowerCase().includes('programming'));
      if (target) {
        target.click();
        return 'SELECTED: ' + target.textContent.trim();
      }

      // If still no options, try a different approach - simulate keyboard navigation
      const input = document.querySelector('#react-select-2-input');
      if (input) {
        // Press down arrow key repeatedly to scroll through options
        for (let i = 0; i < 5; i++) {
          input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', keyCode: 40, bubbles: true }));
        }
        return 'tried arrow keys. Options count: ' + options.length;
      }
      return 'nothing worked';
    })()
  `);
  console.log("Select result:", selectResult);
  await sleep(2000);

  // Step 5: Check if category changed
  const stateCheck = await eval_(`
    JSON.stringify({
      mainCat: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      bodySnippet: document.body.innerText.substring(
        document.body.innerText.indexOf('Category'),
        document.body.innerText.indexOf('Category') + 200
      )
    })
  `);
  console.log("Category state:", stateCheck);

  // Step 6: If main category changed, now handle subcategory
  console.log("\n=== Handling subcategory ===");
  await sleep(1000);
  const subResult = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-3-input');
      if (!input) return 'no subcategory input yet';

      const container = input.closest('[class*="container"]');
      const control = container?.querySelector('[class*="control"]');
      if (control) control.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      input.focus();
      return 'subcategory opened';
    })()
  `);
  console.log(subResult);
  await sleep(1500);

  const subOptions = await eval_(`
    JSON.stringify(
      Array.from(document.querySelectorAll('[id*="react-select-3-option"]')).map(o => ({
        text: o.textContent.trim(),
        id: o.id
      })).slice(0, 15)
    )
  `);
  console.log("Subcategory options:", subOptions);

  // Select AI-related subcategory
  const subSelect = await eval_(`
    (function() {
      const options = Array.from(document.querySelectorAll('[id*="react-select-3-option"]'));
      // Look for AI Apps, AI Agents, Chatbots, or similar
      const priorities = ['ai app', 'ai agent', 'chatbot', 'ai service', 'machine learning', 'software development', 'web programming', 'api'];
      for (const keyword of priorities) {
        const match = options.find(o => o.textContent.toLowerCase().includes(keyword));
        if (match) {
          match.click();
          return 'SELECTED SUB: ' + match.textContent.trim();
        }
      }
      return 'no match. Available: ' + options.map(o => o.textContent.trim()).join(' | ');
    })()
  `);
  console.log("Subcategory:", subSelect);
  await sleep(2000);

  // Final state
  const finalState = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      url: window.location.href
    })
  `);
  console.log("\nFinal state:", finalState);

  ws.close();
  console.log("\nDone. Check Fiverr to verify, then scroll down and click Save.");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
