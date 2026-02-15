// Check AI engine checkboxes, find programming language, fix tags, save
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

  // ===== PART 1: Check AI engine checkboxes =====
  console.log("=== PART 1: Check AI Engine Checkboxes ===");

  // Check Claude, GPT, and Langchain
  const checkResult = await eval_(`
    (function() {
      const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
      const results = [];

      for (const cb of checkboxes) {
        const label = cb.closest('label')?.textContent?.trim() ||
                     cb.nextElementSibling?.textContent?.trim() ||
                     cb.parentElement?.textContent?.trim() || '';

        const shouldCheck = ['Claude', 'GPT', 'Langchain'].some(target =>
          label.toLowerCase().includes(target.toLowerCase())
        );

        if (shouldCheck && !cb.checked) {
          // Use React-compatible click
          const nativeClickDescriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked');
          cb.checked = true;
          cb.dispatchEvent(new Event('change', { bubbles: true }));
          cb.dispatchEvent(new Event('input', { bubbles: true }));
          // Also try clicking the label
          cb.closest('label')?.click();
          results.push('checked: ' + label);
        } else if (shouldCheck) {
          results.push('already checked: ' + label);
        }
      }

      return JSON.stringify({
        actions: results,
        nowChecked: checkboxes.filter(cb => cb.checked).map(cb =>
          cb.closest('label')?.textContent?.trim() || cb.nextElementSibling?.textContent?.trim() || '?'
        )
      });
    })()
  `);
  console.log("Checkbox result:", checkResult);
  await sleep(500);

  // Verify by clicking via CDP on the checkbox labels (React sometimes needs real clicks)
  const cbCoords = await eval_(`
    (function() {
      const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
      const targets = [];
      for (const cb of checkboxes) {
        const label = cb.closest('label')?.textContent?.trim() || '';
        if (['Claude', 'GPT', 'Langchain'].some(t => label.includes(t)) && !cb.checked) {
          const el = cb.closest('label') || cb;
          el.scrollIntoView({ block: 'center' });
          const rect = el.getBoundingClientRect();
          targets.push({
            label,
            x: Math.round(rect.x + 15),
            y: Math.round(rect.y + rect.height / 2)
          });
        }
      }
      return JSON.stringify(targets);
    })()
  `);
  console.log("Unchecked checkboxes to click:", cbCoords);

  const unchecked = JSON.parse(cbCoords);
  for (const cb of unchecked) {
    console.log(`  Clicking "${cb.label}" at (${cb.x}, ${cb.y})...`);
    await cdpClick(cb.x, cb.y);
    await sleep(400);
  }

  // Verify
  const checkedNow = await eval_(`
    Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(cb => cb.checked)
      .map(cb => cb.closest('label')?.textContent?.trim() || '?')
      .join(', ')
  `);
  console.log("Now checked:", checkedNow);

  // ===== PART 2: Find & set Programming Language =====
  console.log("\n=== PART 2: Programming Language ===");

  // Scroll down to find all form sections
  const langField = await eval_(`
    (function() {
      // Look for any text containing "programming language" in the form
      const allText = document.body.innerText;
      const idx = allText.toLowerCase().indexOf('programming language');
      if (idx >= 0) {
        const snippet = allText.substring(Math.max(0, idx - 50), idx + 200);
        // Find the corresponding DOM element
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let found = null;
        while (walker.nextNode()) {
          if (walker.currentNode.textContent.toLowerCase().includes('programming language')) {
            found = walker.currentNode.parentElement;
            break;
          }
        }
        if (found) {
          found.scrollIntoView({ block: 'center' });
          const container = found.closest('[class*="form-input-group"]') || found.closest('div');
          const inputs = container ? Array.from(container.querySelectorAll('input, select, [class*="select"]')).map(el => ({
            tag: el.tagName,
            type: el.type,
            class: el.className.substring(0, 50),
            id: el.id
          })) : [];
          const checkboxes = container ? Array.from(container.querySelectorAll('input[type="checkbox"]')).map(cb => ({
            label: cb.closest('label')?.textContent?.trim() || '',
            checked: cb.checked
          })) : [];
          return JSON.stringify({
            found: true,
            snippet: snippet.substring(0, 200),
            containerClass: container?.className?.substring(0, 60),
            inputs,
            checkboxes: checkboxes.slice(0, 20)
          });
        }
      }

      return JSON.stringify({ found: false, searchResult: 'text not found on page' });
    })()
  `);
  console.log("Language field:", langField);

  if (langField) {
    const langInfo = JSON.parse(langField);
    if (langInfo.found && langInfo.checkboxes?.length > 0) {
      // It's checkboxes too! Check Python, JavaScript, TypeScript
      const langCheckResult = await eval_(`
        (function() {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let found = null;
          while (walker.nextNode()) {
            if (walker.currentNode.textContent.toLowerCase().includes('programming language')) {
              found = walker.currentNode.parentElement;
              break;
            }
          }
          if (!found) return 'section not found';

          const container = found.closest('[class*="form-input-group"]') || found.closest('div');
          const checkboxes = container ? Array.from(container.querySelectorAll('input[type="checkbox"]')) : [];

          const results = [];
          for (const cb of checkboxes) {
            const label = cb.closest('label')?.textContent?.trim() || '';
            const shouldCheck = ['Python', 'JavaScript', 'TypeScript', 'Node'].some(t =>
              label.toLowerCase().includes(t.toLowerCase())
            );
            if (shouldCheck && !cb.checked) {
              cb.closest('label')?.click();
              results.push('clicked: ' + label);
            }
          }

          return JSON.stringify({
            actions: results,
            allLabels: checkboxes.map(cb => ({
              label: cb.closest('label')?.textContent?.trim() || '',
              checked: cb.checked
            })).slice(0, 20)
          });
        })()
      `);
      console.log("Language checkbox result:", langCheckResult);
      await sleep(500);

      // Also click via CDP for React compatibility
      const langCbCoords = await eval_(`
        (function() {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let found = null;
          while (walker.nextNode()) {
            if (walker.currentNode.textContent.toLowerCase().includes('programming language')) {
              found = walker.currentNode.parentElement;
              break;
            }
          }
          if (!found) return '[]';

          const container = found.closest('[class*="form-input-group"]') || found.closest('div');
          const checkboxes = container ? Array.from(container.querySelectorAll('input[type="checkbox"]')) : [];

          const targets = [];
          for (const cb of checkboxes) {
            const label = cb.closest('label')?.textContent?.trim() || '';
            if (['Python', 'JavaScript', 'TypeScript'].some(t => label.includes(t)) && !cb.checked) {
              const el = cb.closest('label') || cb;
              const rect = el.getBoundingClientRect();
              targets.push({
                label,
                x: Math.round(rect.x + 15),
                y: Math.round(rect.y + rect.height / 2)
              });
            }
          }
          return JSON.stringify(targets);
        })()
      `);

      const langTargets = JSON.parse(langCbCoords);
      for (const t of langTargets) {
        console.log(`  Clicking "${t.label}" at (${t.x}, ${t.y})...`);
        await cdpClick(t.x, t.y);
        await sleep(400);
      }
    }
  }

  // ===== PART 3: Fix Tags =====
  console.log("\n=== PART 3: Fix Search Tags ===");

  // Check current tags
  const currentTags = await eval_(`
    Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim())
  `);
  console.log("Current tags:", currentTags);

  const tagsArray = currentTags ? (Array.isArray(currentTags) ? currentTags : JSON.parse(currentTags || '[]')) : [];
  const needed = ["MCP server", "AI integration", "Claude API", "automation", "chatbot"];
  const missing = needed.filter(t => !tagsArray.includes(t));

  if (missing.length > 0) {
    console.log("Missing tags:", missing);

    // Scroll to tags section
    await eval_(`
      (function() {
        const el = document.querySelector('.react-tags') || document.querySelector('.gig-search-tags-group');
        if (el) el.scrollIntoView({ block: 'center' });
      })()
    `);
    await sleep(300);

    const tagInput = await eval_(`
      (function() {
        const input = document.querySelector('.react-tags input[type="text"]') ||
                     document.querySelector('.gig-search-tags-group input[type="text"]');
        if (input) {
          const rect = input.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return null;
      })()
    `);

    if (tagInput) {
      const { x, y } = JSON.parse(tagInput);
      for (const tag of missing) {
        // Focus and clear
        await cdpClick(x, y);
        await sleep(200);
        await eval_(`
          (function() {
            const input = document.querySelector('.react-tags input[type="text"]');
            if (input) { input.focus(); input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); }
          })()
        `);
        await sleep(100);

        // Type tag
        await typeText(tag);
        await sleep(400);

        // Enter
        await pressKey("Enter", "Enter", 13);
        await sleep(600);
      }
    }
  }

  // Final tag count
  const finalTags = await eval_(`
    Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim()).join(', ')
  `);
  console.log("Final tags:", finalTags);

  // ===== PART 4: Final Check & Save =====
  console.log("\n=== PART 4: Final Check ===");
  const state = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      checkedBoxes: Array.from(document.querySelectorAll('input[type="checkbox"]')).filter(cb => cb.checked).map(cb => cb.closest('label')?.textContent?.trim() || '?'),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim()),
      errors: Array.from(document.querySelectorAll('[class*="error"]')).map(e => e.textContent.trim().substring(0, 80)).filter(t => t.length > 0)
    })
  `);
  console.log("State:", state);

  // Save
  console.log("\n=== Saving... ===");
  const saved = await eval_(`
    (function() {
      const btns = Array.from(document.querySelectorAll('button'));
      const btn = btns.find(b => b.textContent.trim() === 'Save & Preview') ||
                 btns.find(b => b.textContent.trim() === 'Save');
      if (btn) { btn.click(); return 'clicked: ' + btn.textContent.trim(); }
      return 'no save button';
    })()
  `);
  console.log("Save:", saved);
  await sleep(5000);

  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
        .map(e => e.textContent.trim().substring(0, 100))
        .filter(t => t.length > 0)
        .slice(0, 5),
      step: window.location.search
    })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
