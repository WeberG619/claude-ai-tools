// Find programming language checkboxes and debug tag input
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

  // ===== PART 1: Map the entire metadata section =====
  console.log("=== PART 1: Map metadata sections ===");
  const metaMap = await eval_(`
    (function() {
      const metaGroup = document.querySelector('.gig-metadata-group');
      if (!metaGroup) return 'no metadata group found';

      // Find all tab/accordion headers
      const headers = Array.from(metaGroup.querySelectorAll('.meta-header, [class*="header"], li'));
      const result = {
        headers: headers.map(h => ({
          text: h.textContent.trim().substring(0, 40),
          class: h.className.substring(0, 40),
          isSelected: h.classList.contains('selected')
        })),
        // Get all checkbox groups
        multiSelects: Array.from(metaGroup.querySelectorAll('.meta-multi-select')).map(ms => {
          const cbs = Array.from(ms.querySelectorAll('input[type="checkbox"]'));
          const heading = ms.previousElementSibling?.textContent?.trim() || ms.closest('li')?.querySelector('.meta-header')?.textContent?.trim() || '';
          return {
            heading,
            class: ms.className,
            checkboxCount: cbs.length,
            options: cbs.slice(0, 5).map(cb => cb.closest('label')?.textContent?.trim() || '?'),
            checkedCount: cbs.filter(cb => cb.checked).length
          };
        }),
        // Full structure as tabs
        tabs: Array.from(metaGroup.querySelectorAll('li')).map(li => ({
          text: li.querySelector('.meta-header')?.textContent?.trim() || li.textContent.trim().substring(0, 40),
          class: li.className.substring(0, 30),
          isSelected: li.classList.contains('selected'),
          hasCheckboxes: li.querySelectorAll('input[type="checkbox"]').length
        }))
      };
      return JSON.stringify(result);
    })()
  `);
  console.log("Metadata map:", metaMap);

  const meta = JSON.parse(metaMap);

  // Check if there's a second tab for Programming Language
  const langTab = meta.tabs?.find(t => t.text.toLowerCase().includes('programming'));
  if (langTab) {
    console.log("\nFound Programming Language tab:", langTab);

    // Click the Programming Language tab header to expand it
    const clickTab = await eval_(`
      (function() {
        const tabs = Array.from(document.querySelectorAll('.gig-metadata-group li'));
        const langTab = tabs.find(t => t.textContent.toLowerCase().includes('programming'));
        if (langTab) {
          const header = langTab.querySelector('.meta-header') || langTab;
          header.click();
          header.scrollIntoView({ block: 'center' });
          return 'clicked programming language tab';
        }
        return 'tab not found';
      })()
    `);
    console.log("Click tab:", clickTab);
    await sleep(800);

    // Now list the programming language checkboxes
    const langCheckboxes = await eval_(`
      (function() {
        const tabs = Array.from(document.querySelectorAll('.gig-metadata-group li'));
        const langTab = tabs.find(t => t.textContent.toLowerCase().includes('programming'));
        if (!langTab) return '[]';

        const cbs = Array.from(langTab.querySelectorAll('input[type="checkbox"]'));
        return JSON.stringify(cbs.map(cb => ({
          label: cb.closest('label')?.textContent?.trim() || '',
          checked: cb.checked,
          visible: cb.offsetParent !== null
        })));
      })()
    `);
    console.log("Programming language options:", langCheckboxes);

    // Click Python and JavaScript checkboxes via CDP
    const langOptions = JSON.parse(langCheckboxes);
    const toCheck = langOptions.filter(o =>
      !o.checked && ['Python', 'JavaScript', 'TypeScript', 'Node'].some(t =>
        o.label.toLowerCase().includes(t.toLowerCase())
      )
    );

    if (toCheck.length > 0) {
      // Get coordinates for each
      const langCoords = await eval_(`
        (function() {
          const tabs = Array.from(document.querySelectorAll('.gig-metadata-group li'));
          const langTab = tabs.find(t => t.textContent.toLowerCase().includes('programming'));
          if (!langTab) return '[]';

          const cbs = Array.from(langTab.querySelectorAll('input[type="checkbox"]'));
          const targets = [];
          for (const cb of cbs) {
            const label = cb.closest('label')?.textContent?.trim() || '';
            if (!cb.checked && ['Python', 'JavaScript', 'TypeScript'].some(t => label.includes(t))) {
              const el = cb.closest('label') || cb;
              const rect = el.getBoundingClientRect();
              targets.push({
                label,
                x: Math.round(rect.x + 15),
                y: Math.round(rect.y + rect.height / 2),
                visible: rect.width > 0
              });
            }
          }
          return JSON.stringify(targets);
        })()
      `);
      console.log("Language checkboxes to click:", langCoords);

      const langTargets = JSON.parse(langCoords);
      for (const t of langTargets) {
        if (t.visible) {
          console.log(`  Clicking "${t.label}" at (${t.x}, ${t.y})...`);
          await cdpClick(t.x, t.y);
          await sleep(400);
        }
      }
    } else {
      console.log("No unchecked language options to select, or Python/JS not available");
      // Just select the first few if nothing is checked
      if (langOptions.filter(o => o.checked).length === 0) {
        console.log("No languages checked! Checking first 3...");
        const firstThree = await eval_(`
          (function() {
            const tabs = Array.from(document.querySelectorAll('.gig-metadata-group li'));
            const langTab = tabs.find(t => t.textContent.toLowerCase().includes('programming'));
            if (!langTab) return '[]';

            const cbs = Array.from(langTab.querySelectorAll('input[type="checkbox"]'));
            const targets = [];
            for (let i = 0; i < Math.min(3, cbs.length); i++) {
              const cb = cbs[i];
              const el = cb.closest('label') || cb;
              const rect = el.getBoundingClientRect();
              if (rect.width > 0) {
                targets.push({
                  label: el.textContent.trim(),
                  x: Math.round(rect.x + 15),
                  y: Math.round(rect.y + rect.height / 2)
                });
              }
            }
            return JSON.stringify(targets);
          })()
        `);
        const ft = JSON.parse(firstThree);
        for (const t of ft) {
          console.log(`  Clicking "${t.label}" at (${t.x}, ${t.y})...`);
          await cdpClick(t.x, t.y);
          await sleep(400);
        }
      }
    }
  } else {
    console.log("No Programming Language tab found. Available tabs:", meta.tabs?.map(t => t.text).join(", "));
  }

  // Verify metadata
  await sleep(500);
  const metaVerify = await eval_(`
    JSON.stringify({
      allChecked: Array.from(document.querySelectorAll('.gig-metadata-group input[type="checkbox"]'))
        .filter(cb => cb.checked)
        .map(cb => cb.closest('label')?.textContent?.trim() || '?'),
      errors: Array.from(document.querySelectorAll('[class*="error"]'))
        .map(e => e.textContent.trim().substring(0, 80))
        .filter(t => t.length > 0)
    })
  `);
  console.log("\nMetadata verification:", metaVerify);

  // ===== PART 2: Debug and fix tags =====
  console.log("\n=== PART 2: Fix Tags ===");

  // Scroll to tags
  await eval_(`document.querySelector('.gig-search-tags-group')?.scrollIntoView({ block: 'center' })`);
  await sleep(300);

  // Check react-tags internal state
  const tagDebug = await eval_(`
    (function() {
      const reactTags = document.querySelector('.react-tags');
      if (!reactTags) return 'react-tags not found';

      // Check React fiber for react-tags component
      let fiber = null;
      for (const key of Object.keys(reactTags)) {
        if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
          fiber = reactTags[key];
          break;
        }
      }
      if (!fiber) return 'no fiber on react-tags';

      let current = fiber;
      let depth = 0;
      let found = [];
      while (current && depth < 30) {
        const props = current.memoizedProps;
        if (props) {
          const keys = Object.keys(props);
          const interesting = keys.filter(k =>
            k === 'tags' || k === 'suggestions' || k === 'onAddition' || k === 'onDelete' ||
            k === 'handleAddition' || k === 'handleDelete' || k === 'addTag' || k === 'onAdd'
          );
          if (interesting.length > 0) {
            found.push({
              depth,
              keys: interesting,
              tags: props.tags?.map(t => typeof t === 'object' ? (t.name || t.label || t.text) : t),
              hasOnAddition: typeof props.onAddition === 'function',
              hasHandleAddition: typeof props.handleAddition === 'function',
              hasOnAdd: typeof props.onAdd === 'function'
            });
          }
        }
        current = current.return;
        depth++;
      }
      return JSON.stringify(found);
    })()
  `);
  console.log("Tag debug:", tagDebug);

  // Try to add tags via React fiber onAddition handler
  const tagFiber = JSON.parse(tagDebug || '[]');
  if (tagFiber.length > 0) {
    const handler = tagFiber.find(f => f.hasOnAddition || f.hasHandleAddition || f.hasOnAdd);
    if (handler) {
      console.log("Found tag handler at depth", handler.depth, "with keys:", handler.keys);

      const addTagResult = await eval_(`
        (function() {
          const reactTags = document.querySelector('.react-tags');
          let fiber = null;
          for (const key of Object.keys(reactTags)) {
            if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
              fiber = reactTags[key];
              break;
            }
          }

          let current = fiber;
          for (let d = 0; d < 30; d++) {
            const props = current?.memoizedProps;
            if (props && (props.onAddition || props.handleAddition || props.onAdd)) {
              const addFn = props.onAddition || props.handleAddition || props.onAdd;
              const tagsToAdd = [
                { id: 'mcp-server', name: 'MCP server' },
                { id: 'ai-integration', name: 'AI integration' },
                { id: 'claude-api', name: 'Claude API' },
                { id: 'automation', name: 'automation' }
              ];

              const results = [];
              for (const tag of tagsToAdd) {
                try {
                  addFn(tag);
                  results.push('added: ' + tag.name);
                } catch(e) {
                  results.push('error adding ' + tag.name + ': ' + e.message);
                }
              }
              return JSON.stringify(results);
            }
            current = current?.return;
          }
          return 'no handler found';
        })()
      `);
      console.log("Add tags via fiber:", addTagResult);
      await sleep(1000);
    }
  }

  // Verify final tag state
  const finalTags = await eval_(`
    Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim())
  `);
  console.log("Final tags:", finalTags);

  // ===== PART 3: Save =====
  console.log("\n=== PART 3: Final state & save ===");
  const finalState = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      checkedMeta: Array.from(document.querySelectorAll('.gig-metadata-group input[type="checkbox"]')).filter(cb => cb.checked).map(cb => cb.closest('label')?.textContent?.trim()),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag')).map(t => t.textContent.trim()),
      errors: Array.from(document.querySelectorAll('[class*="error"]')).map(e => e.textContent.trim().substring(0, 80)).filter(t => t.length > 0)
    })
  `);
  console.log("Final:", finalState);

  const f = JSON.parse(finalState);
  if (f.errors.length === 0 || !f.errors.some(e => e.includes('metadata'))) {
    console.log("\nNo metadata error! Saving...");
    await eval_(`
      (function() {
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Save & Preview') ||
                   Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Save');
        if (btn) btn.click();
      })()
    `);
    await sleep(5000);
    const afterSave = await eval_(`window.location.href`);
    console.log("After save URL:", afterSave);
  } else {
    console.log("\nStill has errors:", f.errors);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
