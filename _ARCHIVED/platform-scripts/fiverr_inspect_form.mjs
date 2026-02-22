// Inspect Fiverr gig form structure in detail
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

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // 1. Inspect the category react-select
  console.log("=== Category Select Structure ===");
  let r = await eval_(`
    const catInput = document.getElementById('react-select-2-input');
    if (!catInput) return 'input not found';

    // Walk up to find the react-select container
    let container = catInput;
    for (let i = 0; i < 10; i++) {
      container = container.parentElement;
      if (!container) break;
      if (container.className?.includes('select') || container.className?.includes('Select')) break;
    }

    return JSON.stringify({
      inputId: catInput.id,
      inputRole: catInput.getAttribute('role'),
      inputAria: catInput.getAttribute('aria-expanded'),
      containerClass: container?.className?.substring(0, 200),
      containerChildren: container ? Array.from(container.children).map(c => c.className?.substring(0, 80) + ' | ' + c.tagName).slice(0, 10) : [],
      // Check all elements with "select" in class name near the category area
      selectElements: Array.from(document.querySelectorAll('[class*="__control"], [class*="__menu"], [class*="__indicator"]'))
        .map(el => el.className.substring(0, 100))
        .slice(0, 10)
    });
  `);
  console.log(r);

  // 2. Click the category container to open dropdown
  console.log("\n=== Opening Category Dropdown ===");
  r = await eval_(`
    const catInput = document.getElementById('react-select-2-input');
    const container = catInput?.closest('[class*="__control"], [class*="css-"]');
    if (container) {
      container.click();
      return 'clicked container: ' + container.className.substring(0, 100);
    }
    // Fallback - click the input's parent
    const parent = catInput?.parentElement?.parentElement;
    if (parent) {
      parent.click();
      return 'clicked parent: ' + parent.className.substring(0, 100);
    }
    return 'nothing to click';
  `);
  console.log(r);
  await sleep(500);

  // Focus the input and type
  await eval_(`document.getElementById('react-select-2-input')?.focus()`);
  await sleep(300);

  // Type "Data" using keyboard events
  for (const char of "Data") {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
    await send("Input.dispatchKeyEvent", { type: "char", text: char });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
    await sleep(100);
  }
  await sleep(1000);

  // Check what appeared
  r = await eval_(`
    // Look for ALL elements that could be dropdown options
    const allVisible = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const cls = el.className?.toString() || '';
        return el.offsetParent !== null && (
          cls.includes('option') || cls.includes('Option') ||
          cls.includes('menu') || cls.includes('Menu') ||
          el.getAttribute('role') === 'option' ||
          el.getAttribute('role') === 'listbox'
        );
      })
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 100),
        role: el.getAttribute('role'),
        text: el.textContent?.trim().substring(0, 80),
        childCount: el.children.length
      }));

    return JSON.stringify(allVisible.slice(0, 20));
  `);
  console.log("\nDropdown elements:", r);

  // Also try a broader search - maybe it uses a portal/overlay
  r = await eval_(`
    // Check for portals or overlays at the end of body
    const lastChildren = Array.from(document.body.children).slice(-5).map(el => ({
      tag: el.tagName,
      class: (el.className?.toString() || '').substring(0, 100),
      id: el.id,
      text: el.textContent?.trim().substring(0, 200),
      display: window.getComputedStyle(el).display,
      zIndex: window.getComputedStyle(el).zIndex
    }));
    return JSON.stringify(lastChildren);
  `);
  console.log("\nBody last children:", r);

  // Try pressing ArrowDown to open and navigate
  console.log("\n=== Trying ArrowDown ===");
  await eval_(`document.getElementById('react-select-2-input')?.focus()`);
  await sleep(200);

  // Clear text first
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(300);

  // Press ArrowDown to open
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
  await sleep(1000);

  r = await eval_(`
    const allEls = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const cls = el.className?.toString() || '';
        const role = el.getAttribute('role') || '';
        return el.offsetParent !== null && (
          cls.includes('option') || cls.includes('Option') ||
          role === 'option' || role === 'listbox' ||
          cls.includes('__menu') || cls.includes('menu-list')
        );
      })
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 80),
        role: el.getAttribute('role'),
        text: el.textContent?.trim().substring(0, 100),
        children: el.children.length
      }));
    return JSON.stringify(allEls.slice(0, 20));
  `);
  console.log("After ArrowDown:", r);

  // 3. Inspect tag input area
  console.log("\n=== Tag Input Structure ===");
  r = await eval_(`
    // Find all text near "Search tags" or "Positive keywords"
    const allText = document.body.innerText;
    const tagSection = allText.indexOf('Search tags');
    const tagContext = tagSection > -1 ? allText.substring(tagSection, tagSection + 300) : 'not found';

    // Find inputs near the tag section
    const allInputs = Array.from(document.querySelectorAll('input[type="text"], input:not([type])'))
      .filter(i => i.offsetParent !== null)
      .map(i => {
        const rect = i.getBoundingClientRect();
        return {
          id: i.id,
          name: i.name,
          placeholder: i.placeholder,
          class: (i.className?.toString() || '').substring(0, 100),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          value: i.value.substring(0, 30)
        };
      });

    return JSON.stringify({ tagContext, inputs: allInputs });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
