// Finish gig 1: set service type, update tags, save
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

  // Step 1: Set service type to "AI Integrations" (value 2736) via React fiber
  console.log("=== Step 1: Set service type ===");
  const serviceResult = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-5-input');
      if (!input) return 'select-5 not found, checking others...';

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
          // Find "AI Integrations" by value 2736
          const target = props.options.find(o => o.value === 2736);
          if (target) {
            props.onChange(target, { action: 'select-option', option: target });
            return 'set service type to AI Integrations (2736)';
          }
          // Fallback: look for any option with "integration" in label
          const fallback = props.options.find(o => typeof o.label === 'string' && o.label.toLowerCase().includes('integration'));
          if (fallback) {
            props.onChange(fallback, { action: 'select-option', option: fallback });
            return 'set service type to: ' + fallback.label;
          }
          return 'target not found. Options: ' + props.options.filter(o => o.value).map(o => o.label + '=' + o.value).join(', ');
        }
        current = current.return;
        depth++;
      }
      return 'no onChange found';
    })()
  `);
  console.log("Service type:", serviceResult);
  await sleep(1500);

  // Step 2: Remove old search tags
  console.log("\n=== Step 2: Remove old search tags ===");
  for (let attempt = 0; attempt < 8; attempt++) {
    const removeOne = await eval_(`
      (function() {
        // Find any tag close button
        const closeBtn = document.querySelector('.gig-search-tags-group .tag-item .close') ||
                        document.querySelector('.gig-search-tags-group .tag-item a') ||
                        document.querySelector('.gig-search-tags-group .tag-item [role="button"]');
        if (closeBtn) {
          const tagText = closeBtn.closest('.tag-item')?.textContent?.trim() || 'unknown';
          closeBtn.click();
          return 'removed: ' + tagText;
        }
        return null;
      })()
    `);
    if (!removeOne) {
      console.log(`All tags removed after ${attempt} iterations`);
      break;
    }
    console.log(removeOne);
    await sleep(400);
  }

  // Step 3: Check current tags state
  const tagState = await eval_(`
    JSON.stringify({
      tags: Array.from(document.querySelectorAll('.gig-search-tags-group .tag-item')).map(t => t.textContent.trim()),
      inputInfo: (() => {
        const input = document.querySelector('.gig-search-tags-group input[type="text"]');
        if (input) {
          const rect = input.getBoundingClientRect();
          return { x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), placeholder: input.placeholder };
        }
        return null;
      })()
    })
  `);
  console.log("Tag state:", tagState);

  // Step 4: Add new tags
  console.log("\n=== Step 4: Add new search tags ===");
  const tagInfo = JSON.parse(tagState);
  const newTags = ["MCP server", "AI integration", "Claude API", "automation", "chatbot"];

  if (tagInfo.inputInfo) {
    for (const tag of newTags) {
      // Click the input area
      await cdpClick(tagInfo.inputInfo.x, tagInfo.inputInfo.y);
      await sleep(200);

      // Focus via JS
      await eval_(`
        (function() {
          const input = document.querySelector('.gig-search-tags-group input[type="text"]');
          if (input) { input.focus(); input.value = ''; }
        })()
      `);
      await sleep(150);

      // Type tag
      await typeText(tag);
      await sleep(300);

      // Press Enter
      await pressKey("Enter", "Enter", 13);
      await sleep(600);

      // Verify
      const count = await eval_(`document.querySelectorAll('.gig-search-tags-group .tag-item').length`);
      console.log(`Added "${tag}" (total tags: ${count})`);
    }
  } else {
    console.log("Tag input not found, skipping tags");
  }

  // Step 5: Update positive keywords section
  console.log("\n=== Step 5: Check positive keywords ===");
  const kwInfo = await eval_(`
    (function() {
      // Look for positive keywords input
      const kwSection = document.querySelector('[class*="positive-keyword"], [class*="PositiveKeyword"]');
      const kwInput = document.querySelector('[class*="positive-keyword"] input, [class*="keyword"] input[type="text"]');

      // Also look at the broader structure
      const allInputs = Array.from(document.querySelectorAll('.gig-search-tags-group input[type="text"]'));
      return JSON.stringify({
        kwSection: kwSection?.textContent?.substring(0, 100) || 'not found',
        kwInput: kwInput ? { placeholder: kwInput.placeholder, id: kwInput.id } : null,
        allTextInputs: allInputs.map(i => ({
          placeholder: i.placeholder,
          name: i.name,
          class: i.className.substring(0, 40),
          rect: (() => { const r = i.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y) }; })()
        }))
      });
    })()
  `);
  console.log("Keywords info:", kwInfo);

  // Step 6: Final verification
  console.log("\n=== Step 6: Final state ===");
  const finalState = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.gig-search-tags-group .tag-item')).map(t => t.textContent.trim()),
      url: window.location.href
    })
  `);
  console.log("Final state:", finalState);

  // Step 7: Save
  console.log("\n=== Step 7: Saving... ===");
  const saved = await eval_(`
    (function() {
      const btns = Array.from(document.querySelectorAll('button'));
      const saveBtn = btns.find(b => b.textContent.trim() === 'Save & Preview') ||
                     btns.find(b => b.textContent.trim() === 'Save');
      if (saveBtn) {
        saveBtn.click();
        return 'clicked: ' + saveBtn.textContent.trim();
      }
      return 'no save button';
    })()
  `);
  console.log("Save:", saved);
  await sleep(4000);

  // Check for errors or navigation
  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], .alert, [role="alert"]')).map(e => e.textContent.trim().substring(0, 100)).filter(t => t.length > 0).slice(0, 5),
      toast: document.querySelector('[class*="toast"], [class*="Toast"], [class*="notification"]')?.textContent?.trim()?.substring(0, 100) || 'none'
    })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
