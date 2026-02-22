// Use CDP mouse events to click the main category dropdown
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
  async function cdpClick(x, y) {
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
  }
  async function pressKey(key, code, keyCode) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode });
  }
  return { ws, send, eval_, cdpClick, pressKey };
}

async function main() {
  const { ws, send, eval_, cdpClick, pressKey } = await connect();

  // Step 1: Close any open dropdown by pressing Escape
  console.log("Closing any open dropdown...");
  await pressKey("Escape", "Escape", 27);
  await sleep(500);

  // Click somewhere neutral to defocus
  await cdpClick(700, 450); // click on title area
  await sleep(500);

  // Step 2: Get exact coordinates of the MAIN category dropdown ("WRITING & TRANSLATION")
  const mainCatCoords = await eval_(`
    (function() {
      // The main category shows "WRITING & TRANSLATION"
      // Find all react-select containers
      const containers = Array.from(document.querySelectorAll('[class*="category-selector"]'));

      // Get the first select container (main category)
      const input = document.querySelector('#react-select-2-input');
      if (input) {
        const container = input.closest('[class*="container"]') || input.closest('[class*="control"]')?.parentElement;
        if (container) {
          const control = container.querySelector('[class*="control"]') || container;
          const rect = control.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: rect.width, h: rect.height });
        }
      }

      // Alternative: find by text content
      const allEls = Array.from(document.querySelectorAll('*'));
      const writingEl = allEls.find(el => el.textContent.trim() === 'Writing & Translation' && el.offsetParent);
      if (writingEl) {
        const rect = writingEl.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: 'found by text' });
      }

      return null;
    })()
  `);
  console.log("Main category coordinates:", mainCatCoords);

  if (mainCatCoords) {
    const { x, y } = JSON.parse(mainCatCoords);
    console.log(`Clicking main category at (${x}, ${y})...`);
    await cdpClick(x, y);
    await sleep(1500);

    // Check what menu appeared
    const menuAfter = await eval_(`
      JSON.stringify({
        menuPortals: Array.from(document.querySelectorAll('[class*="menu-portal"], [class*="MenuPortal"]')).map(m => m.textContent.substring(0, 100)),
        menuLists: Array.from(document.querySelectorAll('[class*="menu-list"], [class*="MenuList"]')).map(m => ({
          count: m.children.length,
          text: m.textContent.substring(0, 200)
        })),
        options2: Array.from(document.querySelectorAll('[id*="react-select-2-option"]')).map(o => o.textContent.trim()).slice(0, 10),
        options3: Array.from(document.querySelectorAll('[id*="react-select-3-option"]')).map(o => o.textContent.trim()).slice(0, 5)
      })
    `);
    console.log("Menu after click:", menuAfter);

    const parsed = JSON.parse(menuAfter);

    // Check if we got main category options (should contain "Programming & Tech", "Graphics & Design", etc.)
    if (parsed.options2.length > 0) {
      console.log("Main category options found! Looking for Programming & Tech...");
      const progIdx = parsed.options2.findIndex(o => o.toLowerCase().includes('programming'));
      if (progIdx >= 0) {
        // Click it
        const optCoords = await eval_(`
          (function() {
            const opt = document.querySelector('[id*="react-select-2-option-${progIdx}"]') ||
                        Array.from(document.querySelectorAll('[id*="react-select-2-option"]'))[${progIdx}];
            if (opt) {
              const rect = opt.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
            return null;
          })()
        `);
        if (optCoords) {
          const { x: ox, y: oy } = JSON.parse(optCoords);
          console.log(`Clicking "Programming & Tech" at (${ox}, ${oy})...`);
          await cdpClick(ox, oy);
          await sleep(2000);
        }
      }
    } else if (parsed.menuLists.length > 0) {
      // Check if the menu has Programming in it
      const menuText = parsed.menuLists.map(m => m.text).join(' ');
      console.log("Menu text sample:", menuText.substring(0, 200));

      if (menuText.toLowerCase().includes('programming')) {
        // Find and click it
        const optCoords = await eval_(`
          (function() {
            const allOpts = Array.from(document.querySelectorAll('[class*="option"]')).filter(o => o.offsetParent !== null);
            const prog = allOpts.find(o => o.textContent.toLowerCase().includes('programming'));
            if (prog) {
              const rect = prog.getBoundingClientRect();
              return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
            return 'not found in ' + allOpts.length + ' visible options';
          })()
        `);
        console.log("Programming option:", optCoords);
        if (optCoords && optCoords.startsWith('{')) {
          const { x: ox, y: oy } = JSON.parse(optCoords);
          await cdpClick(ox, oy);
          await sleep(2000);
        }
      }
    }
  }

  // Step 3: Verify state
  const state = await eval_(`
    JSON.stringify({
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      title: document.querySelector('textarea')?.value
    })
  `);
  console.log("\n=== STATE ===", state);

  // Step 4: If main category changed, handle subcategory
  const cats = JSON.parse(state);
  if (cats.categories[0]?.toLowerCase().includes('programming')) {
    console.log("\nMain category changed! Now selecting subcategory...");
    await sleep(1000);

    // Click subcategory dropdown
    const subCoords = await eval_(`
      (function() {
        const input = document.querySelector('#react-select-3-input');
        if (input) {
          const container = input.closest('[class*="container"]');
          const control = container?.querySelector('[class*="control"]') || container;
          const rect = control.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return null;
      })()
    `);

    if (subCoords) {
      const { x: sx, y: sy } = JSON.parse(subCoords);
      await cdpClick(sx, sy);
      await sleep(1500);

      // Find AI Apps or similar
      const subSelect = await eval_(`
        (function() {
          const options = Array.from(document.querySelectorAll('[id*="react-select-3-option"], [class*="option"]')).filter(o => o.offsetParent !== null);
          const priorities = ['ai app', 'ai agent', 'chatbot', 'ai integration'];
          for (const kw of priorities) {
            const match = options.find(o => o.textContent.toLowerCase().includes(kw));
            if (match) {
              const rect = match.getBoundingClientRect();
              return JSON.stringify({ text: match.textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
            }
          }
          return JSON.stringify({ available: options.map(o => o.textContent.trim()).slice(0, 15) });
        })()
      `);
      console.log("Subcategory target:", subSelect);

      const subParsed = JSON.parse(subSelect);
      if (subParsed.x) {
        await cdpClick(subParsed.x, subParsed.y);
        await sleep(2000);
        console.log("Selected subcategory:", subParsed.text);
      }
    }
  }

  // Final state
  const finalState = await eval_(`
    JSON.stringify({
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      title: document.querySelector('textarea')?.value
    })
  `);
  console.log("\n=== FINAL STATE ===", finalState);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
