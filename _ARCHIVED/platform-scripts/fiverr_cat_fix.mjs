// Fix category selection - target the correct dropdown with keyboard
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
    if (r.exceptionDetails) { console.error("JS Err:", JSON.stringify(r.exceptionDetails).substring(0, 200)); return null; }
    return r.result?.value;
  };
  async function pressKey(key, code, keyCode) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
  }
  async function typeChars(text) {
    for (const char of text) {
      await send("Input.dispatchKeyEvent", { type: "char", text: char, unmodifiedText: char });
      await sleep(80);
    }
  }
  return { ws, send, eval_, pressKey, typeChars };
}

async function main() {
  const { ws, send, eval_, pressKey, typeChars } = await connect();

  // Step 1: Focus the MAIN category react-select and open it
  console.log("=== Step 1: Focus main category ===");

  // First clear the subcategory issue by clicking away
  await eval_(`document.querySelector('h1, .gig-title, textarea')?.click()`);
  await sleep(500);

  // Now focus specifically the main category input
  const focused = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-2-input');
      if (!input) return 'not found';
      // Scroll to it first
      input.scrollIntoView({ block: 'center' });
      input.focus();
      return 'focused #react-select-2-input, activeElement: ' + document.activeElement?.id;
    })()
  `);
  console.log(focused);
  await sleep(500);

  // Step 2: Open dropdown with keyboard
  console.log("\n=== Step 2: Open main category dropdown ===");
  await pressKey("ArrowDown", "ArrowDown", 40);
  await sleep(1500);

  // Search for ANY dropdown menu that appeared anywhere in the DOM
  const menuCheck = await eval_(`
    JSON.stringify({
      menus: Array.from(document.querySelectorAll('[class*="menu"], [class*="Menu"]')).map(m => ({
        class: m.className.toString().substring(0, 60),
        childCount: m.children.length,
        text: m.textContent.substring(0, 200)
      })),
      listboxes: Array.from(document.querySelectorAll('[role="listbox"]')).map(l => ({
        childCount: l.children.length,
        text: l.textContent.substring(0, 200)
      })),
      options: Array.from(document.querySelectorAll('[role="option"]')).map(o => o.textContent.trim()).slice(0, 10),
      allOptions: Array.from(document.querySelectorAll('[class*="option"], [class*="Option"]')).map(o => ({
        text: o.textContent.trim().substring(0, 40),
        id: o.id || '',
        class: o.className.toString().substring(0, 40)
      })).slice(0, 10),
      activeElement: document.activeElement?.id || document.activeElement?.tagName,
      ariaExpanded: document.querySelector('[aria-expanded="true"]')?.className?.substring(0, 40) || 'none'
    })
  `);
  console.log("Menu check:", menuCheck);

  // Step 3: Try multiple ArrowDown presses and check what happens
  console.log("\n=== Step 3: Navigate with arrows ===");
  for (let i = 0; i < 3; i++) {
    await pressKey("ArrowDown", "ArrowDown", 40);
    await sleep(300);
  }

  const afterArrows = await eval_(`
    JSON.stringify({
      focusedOption: document.querySelector('[class*="option"][class*="focused"], [class*="option"][class*="Focused"]')?.textContent?.trim() || 'none',
      selectedOption: document.querySelector('[aria-selected="true"]')?.textContent?.trim() || 'none',
      menuVisible: !!document.querySelector('[class*="MenuList"], [class*="menuList"]'),
      allVisibleOptions: Array.from(document.querySelectorAll('[class*="option"]')).filter(o => o.offsetParent !== null).map(o => o.textContent.trim()).slice(0, 15)
    })
  `);
  console.log("After arrows:", afterArrows);

  // Step 4: Let's try another approach - simulate a real click via CDP Input.dispatchMouseEvent
  console.log("\n=== Step 4: Try mouse click on dropdown indicator ===");
  const coords = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-2-input');
      if (!input) return null;
      const container = input.closest('[class*="container"]');
      const indicator = container?.querySelector('svg')?.closest('div');
      if (indicator) {
        const rect = indicator.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
      }
      // Try the control div
      const control = container?.querySelector('[class*="control"]');
      if (control) {
        const rect = control.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width - 20, y: rect.y + rect.height/2 });
      }
      return null;
    })()
  `);
  console.log("Dropdown indicator coords:", coords);

  if (coords) {
    const { x, y } = JSON.parse(coords);
    console.log(`Clicking at (${x}, ${y})...`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    await sleep(1500);

    const afterClick = await eval_(`
      JSON.stringify({
        menuVisible: !!document.querySelector('[class*="MenuList"], [class*="menuList"]'),
        options: Array.from(document.querySelectorAll('[class*="option"]')).filter(o => o.offsetParent !== null).map(o => o.textContent.trim()).slice(0, 15),
        roleOptions: Array.from(document.querySelectorAll('[role="option"]')).map(o => o.textContent.trim()).slice(0, 15)
      })
    `);
    console.log("After mouse click:", afterClick);

    // If options appeared, find Programming & Tech
    const parsed = JSON.parse(afterClick);
    const allOpts = [...(parsed.options || []), ...(parsed.roleOptions || [])];
    if (allOpts.length > 0) {
      const progIdx = allOpts.findIndex(o => o.toLowerCase().includes('programming'));
      console.log(`Found ${allOpts.length} options. Programming at index: ${progIdx}`);

      if (progIdx >= 0) {
        // Click it directly via coordinates
        const optCoords = await eval_(`
          (function() {
            const options = Array.from(document.querySelectorAll('[class*="option"], [role="option"]')).filter(o => o.offsetParent !== null);
            const target = options.find(o => o.textContent.toLowerCase().includes('programming'));
            if (target) {
              const rect = target.getBoundingClientRect();
              return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
            }
            return null;
          })()
        `);

        if (optCoords) {
          const { x: ox, y: oy } = JSON.parse(optCoords);
          console.log(`Clicking Programming & Tech at (${ox}, ${oy})...`);
          await send("Input.dispatchMouseEvent", { type: "mousePressed", x: ox, y: oy, button: "left", clickCount: 1 });
          await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: ox, y: oy, button: "left", clickCount: 1 });
          await sleep(2000);
        }
      }
    }
  }

  // Final check
  const finalState = await eval_(`
    JSON.stringify({
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      title: document.querySelector('textarea')?.value
    })
  `);
  console.log("\n=== FINAL STATE ===");
  console.log(finalState);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
