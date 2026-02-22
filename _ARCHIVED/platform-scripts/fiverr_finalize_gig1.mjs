// Finalize gig 1: Switch to AI Development subcategory, set service type, update tags, save
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

  // Step 1: Switch subcategory to "AI Development" (520) via React fiber
  console.log("=== Step 1: Switch subcategory to AI Development ===");
  const subSwitch = await eval_(`
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
          const target = props.options.find(o => o.value === 520);
          if (target) {
            props.onChange(target, { action: 'select-option', option: target });
            return 'switched to: ' + target.label;
          }
          return 'value 520 not found in options';
        }
        current = current.return;
        depth++;
      }
      return 'no onChange found';
    })()
  `);
  console.log("Subcategory:", subSwitch);
  await sleep(2000);

  // Step 2: Handle service type selector (react-select-5)
  console.log("\n=== Step 2: Set service type ===");
  const serviceResult = await eval_(`
    (function() {
      const input = document.querySelector('#react-select-5-input');
      if (!input) return 'service type input not found - checking for alternatives...';

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
          const optionLabels = props.options.map(o => o.label || (typeof o === 'string' ? o : JSON.stringify(o).substring(0, 50)));
          return JSON.stringify({
            options: props.options.map(o => ({ label: o.label, value: o.value })),
            currentValue: props.value,
            depth
          });
        }
        current = current.return;
        depth++;
      }
      return 'no options found after ' + depth;
    })()
  `);
  console.log("Service type info:", serviceResult);

  // If service type options are available, try to select one
  if (serviceResult && serviceResult.startsWith('{')) {
    const stParsed = JSON.parse(serviceResult);
    console.log("Service type options:", stParsed.options?.map(o => o.label));

    // Look for AI-related service type
    if (stParsed.options) {
      const aiService = stParsed.options.find(o =>
        o.label && (
          o.label.toLowerCase().includes('ai') ||
          o.label.toLowerCase().includes('custom') ||
          o.label.toLowerCase().includes('integration')
        )
      );
      if (aiService) {
        console.log(`Selecting service type: "${aiService.label}"...`);
        const setService = await eval_(`
          (function() {
            const input = document.querySelector('#react-select-5-input');
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
                const target = props.options.find(o => o.value === ${JSON.stringify(aiService.value)});
                if (target) {
                  props.onChange(target, { action: 'select-option', option: target });
                  return 'set service type: ' + (target.label || target.value);
                }
              }
              current = current.return;
              depth++;
            }
            return 'failed';
          })()
        `);
        console.log("Set service:", setService);
        await sleep(1500);
      }
    }
  } else {
    // Check if subcategory change created new selectors
    await sleep(2000);
    const newSelects = await eval_(`
      JSON.stringify({
        select4: !!document.querySelector('#react-select-4-input'),
        select5: !!document.querySelector('#react-select-5-input'),
        select6: !!document.querySelector('#react-select-6-input'),
        allSelects: Array.from(document.querySelectorAll('[id*="react-select"][id*="-input"]')).map(i => i.id),
        allSingleValues: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim())
      })
    `);
    console.log("Updated selectors:", newSelects);
  }

  // Step 3: Update search tags - remove old ones and add new ones
  console.log("\n=== Step 3: Update search tags ===");

  // First remove existing tags
  const removeResult = await eval_(`
    (function() {
      // Find tag remove buttons (X icons next to each tag)
      const removeButtons = Array.from(document.querySelectorAll('[class*="tag"] [class*="remove"], [class*="tag"] [class*="close"], [class*="tag"] button, [class*="tag"] svg'));
      // Also try the more specific Fiverr tag structure
      const tagItems = Array.from(document.querySelectorAll('.gig-search-tags-group .tag-item, [class*="search-tag"] .tag-item, [class*="tag-list"] li, [class*="tag-list"] [class*="item"]'));

      // Try clicking all remove/close buttons for tags
      let removed = 0;
      const allRemovable = Array.from(document.querySelectorAll('[class*="tag"] [role="button"], [class*="tag"] .close, [class*="tag-item"] [class*="remove"], a.close, .tag-item .close'));

      if (allRemovable.length === 0) {
        // Try alternative: find by text content of known old tags
        const oldTags = ['resume writer', 'cv', 'LinkedIn', 'career'];
        const allButtons = Array.from(document.querySelectorAll('button, [role="button"], a'));
        for (const btn of allButtons) {
          if (btn.querySelector('svg') && btn.closest('[class*="tag"]')) {
            btn.click();
            removed++;
          }
        }
      } else {
        for (const btn of allRemovable) {
          btn.click();
          removed++;
        }
      }

      return JSON.stringify({
        removed,
        removeButtonsFound: removeButtons.length,
        tagItemsFound: tagItems.length,
        allRemovableFound: allRemovable.length,
        remainingTags: Array.from(document.querySelectorAll('[class*="tag-item"], [class*="tag-list"] li')).map(t => t.textContent.trim()).slice(0, 10)
      });
    })()
  `);
  console.log("Remove old tags:", removeResult);
  await sleep(1000);

  // Find the tag input and check its structure
  const tagInputInfo = await eval_(`
    (function() {
      // Common tag input patterns
      const tagInput = document.querySelector('.gig-search-tags-group input') ||
                       document.querySelector('[class*="tag"] input[type="text"]') ||
                       document.querySelector('[placeholder*="tag"]') ||
                       document.querySelector('[placeholder*="keyword"]');

      if (tagInput) {
        return JSON.stringify({
          placeholder: tagInput.placeholder,
          value: tagInput.value,
          type: tagInput.type,
          id: tagInput.id,
          class: tagInput.className.substring(0, 60),
          rect: (() => {
            const r = tagInput.getBoundingClientRect();
            return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) };
          })()
        });
      }

      // Check for tag area structure
      const tagArea = document.querySelector('.gig-search-tags-group, [class*="search-tag"]');
      if (tagArea) {
        return JSON.stringify({
          type: 'area_found',
          html: tagArea.innerHTML.substring(0, 300),
          inputs: Array.from(tagArea.querySelectorAll('input')).map(i => ({
            placeholder: i.placeholder,
            id: i.id,
            type: i.type
          }))
        });
      }

      return 'no tag input found';
    })()
  `);
  console.log("Tag input:", tagInputInfo);

  // If we found the tag input, remove old tags and add new ones
  if (tagInputInfo && tagInputInfo.includes('rect')) {
    const tagInfo = JSON.parse(tagInputInfo);

    // First try to remove old tags by clicking their X buttons
    const removeOld = await eval_(`
      (function() {
        let removed = 0;
        // Keep clicking remove buttons until none are left
        for (let attempt = 0; attempt < 10; attempt++) {
          const removeBtn = document.querySelector('.gig-search-tags-group .tag-item .close') ||
                           document.querySelector('.gig-search-tags-group [class*="remove"]') ||
                           document.querySelector('.gig-search-tags-group .tag-item button') ||
                           document.querySelector('.gig-search-tags-group .tag-item svg')?.closest('a, button, [role="button"]');
          if (removeBtn) {
            removeBtn.click();
            removed++;
          } else break;
        }
        return 'removed ' + removed + ' tags. Remaining: ' + Array.from(document.querySelectorAll('.gig-search-tags-group .tag-item')).map(t => t.textContent.trim()).join(', ');
      })()
    `);
    console.log("Removed old:", removeOld);
    await sleep(500);

    // Now add new tags by clicking the input and typing + Enter
    const newTags = ["MCP server", "AI integration", "Claude API", "automation", "chatbot"];
    for (const tag of newTags) {
      // Click the tag input
      await cdpClick(tagInfo.rect.x, tagInfo.rect.y);
      await sleep(300);

      // Focus it via JS too
      await eval_(`
        (function() {
          const input = document.querySelector('.gig-search-tags-group input') ||
                       document.querySelector('[class*="tag"] input[type="text"]');
          if (input) { input.focus(); input.value = ''; }
        })()
      `);
      await sleep(200);

      // Type the tag
      await typeText(tag);
      await sleep(300);

      // Press Enter to submit the tag
      await pressKey("Enter", "Enter", 13);
      await sleep(500);
    }

    // Verify tags
    const tagsAfter = await eval_(`
      JSON.stringify(
        Array.from(document.querySelectorAll('.gig-search-tags-group .tag-item, [class*="tag-list"] li')).map(t => t.textContent.trim())
      )
    `);
    console.log("Tags after adding:", tagsAfter);
  }

  // Step 4: Final state check before saving
  console.log("\n=== Step 4: Final state check ===");
  const finalCheck = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.gig-search-tags-group .tag-item')).map(t => t.textContent.trim()),
      positiveKeywords: Array.from(document.querySelectorAll('[class*="positive-keyword"], [class*="keyword-item"]')).map(k => k.textContent.trim())
    })
  `);
  console.log("Final check:", finalCheck);

  // Step 5: Click Save & Continue
  console.log("\n=== Step 5: Save ===");
  const saveResult = await eval_(`
    (function() {
      const btns = Array.from(document.querySelectorAll('button'));
      // Prefer "Save & Continue" over just "Save"
      const saveContinue = btns.find(b => b.textContent.trim().toLowerCase().includes('save') && b.textContent.trim().toLowerCase().includes('continue'));
      const save = btns.find(b => b.textContent.trim() === 'Save');

      const target = saveContinue || save;
      if (target) {
        target.click();
        return 'clicked: ' + target.textContent.trim();
      }
      return 'no save button found';
    })()
  `);
  console.log("Save:", saveResult);
  await sleep(3000);

  // Check what page we're on after save
  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      title: document.title,
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], .alert')).map(e => e.textContent.trim().substring(0, 80)).slice(0, 5)
    })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
