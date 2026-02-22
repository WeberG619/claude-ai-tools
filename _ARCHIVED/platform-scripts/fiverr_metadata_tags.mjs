// Fix metadata (AI engine, Programming language) and search tags, then save
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

  // ===== PART 1: Fix Gig Metadata (AI engine, Programming language) =====
  console.log("=== PART 1: Fix Gig Metadata ===");

  // Find the metadata section and its dropdowns
  const metaInfo = await eval_(`
    (function() {
      // Find the metadata section
      const sections = Array.from(document.querySelectorAll('[class*="form-input-group"], [class*="metadata"]'));
      const metaSection = sections.find(s => s.textContent.includes('metadata') || s.textContent.includes('AI engine'));

      // Find all checkboxes and dropdowns in the metadata area
      const allCheckboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
      const allDropdowns = Array.from(document.querySelectorAll('select'));

      // Look for specific metadata fields
      const result = {
        checkboxes: allCheckboxes.map(cb => ({
          name: cb.name,
          id: cb.id,
          label: cb.closest('label')?.textContent?.trim()?.substring(0, 40) || cb.nextElementSibling?.textContent?.trim()?.substring(0, 40) || '',
          checked: cb.checked,
          visible: cb.offsetParent !== null
        })).filter(cb => cb.visible),
        dropdowns: allDropdowns.map(sel => ({
          name: sel.name,
          id: sel.id,
          options: Array.from(sel.options).map(o => ({ text: o.text, value: o.value, selected: o.selected })).slice(0, 10),
          visible: sel.offsetParent !== null
        })).filter(s => s.visible),
        // Also check for react-based metadata inputs
        metadataReactSelects: []
      };

      // Check all react-selects not yet handled
      const reactSelects = Array.from(document.querySelectorAll('[id*="react-select"][id*="-input"]'));
      for (const input of reactSelects) {
        if (['react-select-2-input', 'react-select-3-input', 'react-select-5-input'].includes(input.id)) continue;

        let fiber = null;
        for (const key of Object.keys(input)) {
          if (key.startsWith('__reactFiber')) { fiber = input[key]; break; }
        }
        if (!fiber) continue;

        let current = fiber;
        for (let d = 0; d < 30; d++) {
          const props = current?.memoizedProps;
          if (props?.options?.length > 0) {
            result.metadataReactSelects.push({
              id: input.id,
              isMulti: !!props.isMulti,
              options: props.options.slice(0, 10).map(o =>
                typeof o === 'object' ? { label: o.label, value: o.value } : o
              ),
              value: props.value,
              depth: d
            });
            break;
          }
          current = current?.return;
        }
      }

      // Also look for chip/tag-based metadata
      const chipSections = Array.from(document.querySelectorAll('[class*="chip"], [class*="Chip"]'));
      result.chipSections = chipSections.slice(0, 5).map(c => ({
        text: c.textContent.trim().substring(0, 40),
        class: c.className.substring(0, 40),
        parent: c.parentElement?.textContent?.trim()?.substring(0, 40)
      }));

      return JSON.stringify(result);
    })()
  `);
  console.log("Metadata fields:", metaInfo);

  const meta = JSON.parse(metaInfo);

  // Handle react-based metadata dropdowns
  if (meta.metadataReactSelects.length > 0) {
    for (const sel of meta.metadataReactSelects) {
      console.log(`\nHandling ${sel.id} (${sel.isMulti ? 'multi' : 'single'} select, ${sel.options.length} options)`);
      console.log("  Options:", sel.options.map(o => o.label || o).join(", "));

      // Determine what to select based on the options available
      let target = null;
      const optLabels = sel.options.map(o => (o.label || '').toLowerCase());

      if (optLabels.some(l => l.includes('python') || l.includes('javascript') || l.includes('node'))) {
        // This is a Programming Language field
        // Select Python and JavaScript/Node if multi-select
        if (sel.isMulti) {
          const targets = sel.options.filter(o => {
            const l = (o.label || '').toLowerCase();
            return l.includes('python') || l.includes('javascript') || l.includes('typescript') || l.includes('node');
          });
          if (targets.length > 0) {
            const selectCode = `
              (function() {
                const input = document.querySelector('#${sel.id}');
                let fiber = null;
                for (const key of Object.keys(input)) {
                  if (key.startsWith('__reactFiber')) { fiber = input[key]; break; }
                }
                let current = fiber;
                for (let d = 0; d < 30; d++) {
                  const props = current?.memoizedProps;
                  if (props?.onChange && props?.options?.length > 0) {
                    const targets = props.options.filter(o => {
                      const l = (o.label || '').toLowerCase();
                      return l.includes('python') || l.includes('javascript') || l.includes('typescript') || l.includes('node');
                    });
                    if (targets.length > 0) {
                      for (const t of targets) {
                        props.onChange([...(props.value || []), t], { action: 'select-option', option: t });
                      }
                      return 'selected: ' + targets.map(t => t.label).join(', ');
                    }
                  }
                  current = current?.return;
                }
                return 'failed';
              })()
            `;
            const r = await eval_(selectCode);
            console.log("  Result:", r);
            await sleep(500);
          }
        } else {
          target = sel.options.find(o => (o.label || '').toLowerCase().includes('python'));
        }
      } else if (optLabels.some(l => l.includes('chatgpt') || l.includes('claude') || l.includes('gpt') || l.includes('openai') || l.includes('llama'))) {
        // This is AI engine field
        if (sel.isMulti) {
          const selectCode = `
            (function() {
              const input = document.querySelector('#${sel.id}');
              let fiber = null;
              for (const key of Object.keys(input)) {
                if (key.startsWith('__reactFiber')) { fiber = input[key]; break; }
              }
              let current = fiber;
              for (let d = 0; d < 30; d++) {
                const props = current?.memoizedProps;
                if (props?.onChange && props?.options?.length > 0) {
                  const targets = props.options.filter(o => {
                    const l = (o.label || '').toLowerCase();
                    return l.includes('claude') || l.includes('chatgpt') || l.includes('gpt') || l.includes('openai') || l.includes('custom');
                  });
                  if (targets.length > 0) {
                    const newValue = [...(props.value || []), ...targets];
                    props.onChange(newValue, { action: 'select-option', option: targets[0] });
                    return 'selected: ' + targets.map(t => t.label).join(', ');
                  }
                  return 'no AI match. Available: ' + props.options.map(o => o.label).join(', ');
                }
                current = current?.return;
              }
              return 'failed';
            })()
          `;
          const r = await eval_(selectCode);
          console.log("  Result:", r);
          await sleep(500);
        }
      } else {
        // Unknown field - select first non-placeholder option
        console.log("  Unknown field, selecting first option...");
        target = sel.options.find(o => o.value != null && o.value !== '');
      }

      if (target && !sel.isMulti) {
        const selectCode = `
          (function() {
            const input = document.querySelector('#${sel.id}');
            let fiber = null;
            for (const key of Object.keys(input)) {
              if (key.startsWith('__reactFiber')) { fiber = input[key]; break; }
            }
            let current = fiber;
            for (let d = 0; d < 30; d++) {
              const props = current?.memoizedProps;
              if (props?.onChange && props?.options?.length > 0) {
                const target = props.options.find(o => o.value === ${JSON.stringify(target.value)});
                if (target) {
                  props.onChange(target, { action: 'select-option', option: target });
                  return 'selected: ' + target.label;
                }
              }
              current = current?.return;
            }
            return 'failed';
          })()
        `;
        const r = await eval_(selectCode);
        console.log("  Result:", r);
        await sleep(500);
      }
    }
  }

  // Handle regular HTML dropdowns
  if (meta.dropdowns.length > 0) {
    for (const dd of meta.dropdowns) {
      console.log(`\nHandling dropdown: ${dd.name || dd.id} (${dd.options.length} options)`);
      // Select appropriate value
      const selectValue = dd.options.find(o => o.text.toLowerCase().includes('python') || o.text.toLowerCase().includes('chatgpt') || o.text.toLowerCase().includes('ai'));
      if (selectValue) {
        await eval_(`
          (function() {
            const sel = document.querySelector('#${dd.id}') || document.querySelector('[name="${dd.name}"]');
            if (sel) {
              sel.value = ${JSON.stringify(selectValue.value)};
              sel.dispatchEvent(new Event('change', { bubbles: true }));
              return 'selected: ' + sel.value;
            }
            return 'not found';
          })()
        `);
      }
    }
  }

  // ===== PART 2: Fix Search Tags =====
  console.log("\n\n=== PART 2: Fix Search Tags ===");

  // Remove old tags using the react-tags__selected-tag buttons
  console.log("Removing old tags...");
  for (let i = 0; i < 10; i++) {
    const removed = await eval_(`
      (function() {
        const tag = document.querySelector('.react-tags__selected-tag');
        if (tag) {
          const text = tag.textContent.trim();
          tag.click(); // clicking the tag button should remove it
          return text;
        }
        return null;
      })()
    `);
    if (!removed) {
      console.log(`  All tags removed (${i} total)`);
      break;
    }
    console.log(`  Removed: "${removed}"`);
    await sleep(300);
  }

  // Find the react-tags input and add new tags
  console.log("\nAdding new tags...");
  const tagInputCoords = await eval_(`
    (function() {
      const input = document.querySelector('.react-tags input') ||
                   document.querySelector('.gig-search-tags-group input[type="text"]');
      if (input) {
        input.scrollIntoView({ block: 'center' });
        const rect = input.getBoundingClientRect();
        return JSON.stringify({
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          class: input.className.substring(0, 40)
        });
      }
      return null;
    })()
  `);
  console.log("Tag input:", tagInputCoords);

  if (tagInputCoords) {
    const { x, y } = JSON.parse(tagInputCoords);
    const newTags = ["MCP server", "AI integration", "Claude API", "automation", "chatbot"];

    for (const tag of newTags) {
      // Click and focus the tag input
      await cdpClick(x, y);
      await sleep(200);

      // Also focus via JS with React-compatible value setting
      await eval_(`
        (function() {
          const input = document.querySelector('.react-tags input') ||
                       document.querySelector('.gig-search-tags-group input[type="text"]');
          if (input) {
            input.focus();
            // Clear existing value
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(input, '');
            input.dispatchEvent(new Event('input', { bubbles: true }));
          }
        })()
      `);
      await sleep(100);

      // Type the tag text via CDP
      await typeText(tag);
      await sleep(400);

      // Press Enter to submit
      await pressKey("Enter", "Enter", 13);
      await sleep(600);

      // Verify
      const tags = await eval_(`
        Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim()).join(', ')
      `);
      console.log(`  Added "${tag}" → [${tags}]`);
    }
  }

  // ===== PART 3: Verify & Save =====
  console.log("\n\n=== PART 3: Verify & Save ===");
  const finalState = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim()),
      errors: Array.from(document.querySelectorAll('[class*="error"]')).map(e => e.textContent.trim().substring(0, 80)).filter(t => t.length > 0)
    })
  `);
  console.log("Final state:", finalState);

  // Save
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
      pageTitle: document.title
    })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
