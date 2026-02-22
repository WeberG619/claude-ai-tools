// Fix category/subcategory selection for gig #2 - v2
// Click the visible dropdown control, not the hidden input
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Step 1: Inspect the category dropdown structure
  console.log("=== Inspecting Category Dropdown ===");
  let r = await eval_(`
    const catWrapper = document.querySelector('.gig-category-wrapper');
    if (!catWrapper) return JSON.stringify({ error: 'no category wrapper' });

    // Get the visible control div that users click
    const control = catWrapper.querySelector('[class*="control"]');
    const indicator = catWrapper.querySelector('[class*="indicator"]');
    const valueContainer = catWrapper.querySelector('[class*="ValueContainer"], [class*="value-container"]');
    const input = catWrapper.querySelector('input');

    return JSON.stringify({
      controlClass: control?.className?.toString()?.substring(0, 80) || 'none',
      controlRect: control ? {
        x: Math.round(control.getBoundingClientRect().x + control.getBoundingClientRect().width/2),
        y: Math.round(control.getBoundingClientRect().y + control.getBoundingClientRect().height/2)
      } : null,
      indicatorRect: indicator ? {
        x: Math.round(indicator.getBoundingClientRect().x + indicator.getBoundingClientRect().width/2),
        y: Math.round(indicator.getBoundingClientRect().y + indicator.getBoundingClientRect().height/2)
      } : null,
      inputId: input?.id || 'none',
      currentValue: catWrapper.querySelector('[class*="singleValue"], [class*="single-value"]')?.textContent?.trim() || 'empty',
      placeholder: catWrapper.querySelector('[class*="placeholder"]')?.textContent?.trim() || 'none'
    });
  `);
  console.log("Category structure:", r);
  const catStruct = JSON.parse(r);

  if (catStruct.error) {
    console.log("ERROR:", catStruct.error);
    ws.close();
    return;
  }

  // Step 2: Click the control area to open dropdown
  console.log("\n=== Opening Category Dropdown ===");
  const clickTarget = catStruct.controlRect || catStruct.indicatorRect;
  if (clickTarget) {
    console.log(`Clicking control at (${clickTarget.x}, ${clickTarget.y})`);
    await clickAt(send, clickTarget.x, clickTarget.y);
    await sleep(1000);

    // Check if menu opened
    r = await eval_(`
      const menu = document.querySelector('[class*="menu-list"], [class*="menuList"], [id*="react-select"][id*="listbox"]');
      if (menu) {
        const items = Array.from(menu.children).map(el => ({
          text: el.textContent.trim().substring(0, 60),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        })).slice(0, 15);
        return JSON.stringify({ open: true, count: items.length, items });
      }
      // Try broader search
      const anyMenu = document.querySelector('[class*="__menu"]');
      if (anyMenu) {
        return JSON.stringify({ open: true, menuClass: anyMenu.className?.toString()?.substring(0, 80), html: anyMenu.innerHTML.substring(0, 500) });
      }
      return JSON.stringify({ open: false });
    `);
    console.log("Menu state:", r);
    const menuState = JSON.parse(r);

    if (menuState.open && menuState.items) {
      // Find Writing & Translation
      const writingOpt = menuState.items.find(i => i.text.includes('Writing'));
      if (writingOpt) {
        console.log(`Found "Writing" option - clicking at (${writingOpt.x}, ${writingOpt.y})`);
        await clickAt(send, writingOpt.x, writingOpt.y);
        await sleep(2000);
      } else {
        // Type to filter
        console.log("No Writing option visible, typing to filter...");
        await send("Input.insertText", { text: "Writing" });
        await sleep(1500);

        r = await eval_(`
          const menu = document.querySelector('[class*="menu-list"], [class*="menuList"]');
          if (menu) {
            return JSON.stringify(Array.from(menu.children).map(el => ({
              text: el.textContent.trim().substring(0, 60),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            })));
          }
          return '[]';
        `);
        console.log("Filtered options:", r);
        const filtered = JSON.parse(r);
        if (filtered.length > 0) {
          const wt = filtered.find(o => o.text.includes('Writing & Translation')) || filtered[0];
          console.log(`Clicking: ${wt.text}`);
          await clickAt(send, wt.x, wt.y);
          await sleep(2000);
        }
      }
    } else if (!menuState.open) {
      // Menu didn't open - try clicking the dropdown indicator arrow instead
      console.log("Menu didn't open. Trying dropdown indicator...");
      r = await eval_(`
        const catWrapper = document.querySelector('.gig-category-wrapper');
        const svg = catWrapper?.querySelector('svg');
        if (svg) {
          const rect = svg.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'no svg' });
      `);
      console.log("SVG indicator:", r);
      const svgPos = JSON.parse(r);
      if (!svgPos.error) {
        await clickAt(send, svgPos.x, svgPos.y);
        await sleep(1000);

        // Try typing
        await send("Input.insertText", { text: "Writing" });
        await sleep(1500);

        r = await eval_(`
          // Broad search for anything that looks like dropdown options
          const allEls = Array.from(document.querySelectorAll('*'))
            .filter(el => {
              const cls = el.className?.toString() || '';
              return (cls.includes('option') || cls.includes('menu')) && el.offsetParent !== null && el.textContent.includes('Writing');
            })
            .map(el => ({
              text: el.textContent.trim().substring(0, 60),
              class: (el.className?.toString() || '').substring(0, 60),
              tag: el.tagName,
              children: el.children.length,
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
            }))
            .slice(0, 10);
          return JSON.stringify(allEls);
        `);
        console.log("Broad option search:", r);
        const broadResults = JSON.parse(r);
        // Find a leaf-level option
        const leaf = broadResults.find(el => el.children === 0 && el.text.includes('Writing'));
        if (leaf) {
          console.log(`Clicking leaf option: ${leaf.text}`);
          await clickAt(send, leaf.x, leaf.y);
          await sleep(2000);
        }
      }
    }
  }

  // Check category value
  r = await eval_(`return document.querySelector('input[name="gig[category_id]"]')?.value || 'empty'`);
  console.log("\nCategory ID:", r);

  if (r === 'empty' || r === '') {
    // Last resort: try React internals to set category directly
    console.log("\n=== Last Resort: React State Manipulation ===");
    r = await eval_(`
      // Find React fiber on the category wrapper
      const catWrapper = document.querySelector('.gig-category-wrapper');
      const keys = Object.keys(catWrapper || {}).filter(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));

      // Also check what react-select props look like
      const input = document.querySelector('#react-select-2-input');
      const inputKeys = input ? Object.keys(input).filter(k => k.startsWith('__react')) : [];

      // Check for aria-owns on the input which points to the menu
      const ariaOwns = input?.getAttribute('aria-owns') || input?.getAttribute('aria-controls') || 'none';

      return JSON.stringify({
        wrapperReactKeys: keys,
        inputReactKeys: inputKeys,
        ariaOwns: ariaOwns,
        inputRole: input?.getAttribute('role') || 'none',
        inputAriaExpanded: input?.getAttribute('aria-expanded') || 'none'
      });
    `);
    console.log("React internals:", r);

    // Try focusing input and using keyboard events instead
    console.log("\nTrying focus + keyboard approach...");
    r = await eval_(`
      const input = document.querySelector('#react-select-2-input');
      if (input) {
        input.focus();
        const rect = input.getBoundingClientRect();
        // Get the parent control for clicking
        const control = input.closest('[class*="control"]');
        const controlRect = control ? control.getBoundingClientRect() : rect;
        return JSON.stringify({
          inputX: Math.round(rect.x + 5),
          inputY: Math.round(rect.y + rect.height/2),
          controlX: Math.round(controlRect.x + controlRect.width/2),
          controlY: Math.round(controlRect.y + controlRect.height/2),
          controlW: Math.round(controlRect.width),
          controlH: Math.round(controlRect.height)
        });
      }
      return JSON.stringify({ error: 'no input' });
    `);
    console.log("Input position:", r);
    const inputPos = JSON.parse(r);

    if (!inputPos.error) {
      // Click directly on the input element
      await clickAt(send, inputPos.inputX, inputPos.inputY);
      await sleep(500);

      // Type character by character using keyDown/keyUp events
      const text = "Wri";
      for (const ch of text) {
        await send("Input.dispatchKeyEvent", {
          type: "keyDown",
          key: ch,
          text: ch,
          unmodifiedText: ch
        });
        await sleep(50);
        await send("Input.dispatchKeyEvent", {
          type: "keyUp",
          key: ch
        });
        await sleep(100);
      }
      await sleep(2000);

      // Check for menu
      r = await eval_(`
        const menus = Array.from(document.querySelectorAll('[class*="menu"], [id*="listbox"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            class: (el.className?.toString() || '').substring(0, 80),
            id: el.id || '',
            text: el.textContent.trim().substring(0, 200),
            children: el.children.length
          }));
        return JSON.stringify(menus);
      `);
      console.log("Menus after typing:", r);

      // Also check aria-expanded
      r = await eval_(`
        const input = document.querySelector('#react-select-2-input');
        return JSON.stringify({
          ariaExpanded: input?.getAttribute('aria-expanded'),
          ariaActivedescendant: input?.getAttribute('aria-activedescendant') || 'none'
        });
      `);
      console.log("Aria state:", r);
    }
  }

  // Step 3: Try subcategory (only if category was set)
  r = await eval_(`return document.querySelector('input[name="gig[category_id]"]')?.value || 'empty'`);
  if (r !== 'empty' && r !== '') {
    console.log("\n=== Subcategory Selection ===");
    // Similar approach for subcategory...
    r = await eval_(`
      const subWrapper = document.querySelector('.gig-subcategory-wrapper');
      if (!subWrapper) return JSON.stringify({ error: 'no subcategory wrapper' });
      const control = subWrapper.querySelector('[class*="control"]');
      if (control) {
        const rect = control.getBoundingClientRect();
        return JSON.stringify({
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        });
      }
      return JSON.stringify({ error: 'no control' });
    `);
    const subCtrl = JSON.parse(r);
    if (!subCtrl.error) {
      await clickAt(send, subCtrl.x, subCtrl.y);
      await sleep(1000);
      await send("Input.insertText", { text: "Proof" });
      await sleep(1500);

      r = await eval_(`
        const menu = document.querySelector('[class*="menu-list"], [class*="menuList"]');
        if (menu) {
          return JSON.stringify(Array.from(menu.children).map(el => ({
            text: el.textContent.trim().substring(0, 60),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          })));
        }
        return '[]';
      `);
      const subOpts = JSON.parse(r);
      if (subOpts.length > 0) {
        const proof = subOpts.find(o => o.text.includes('Proofreading')) || subOpts[0];
        await clickAt(send, proof.x, proof.y);
        await sleep(2000);
      }
    }
  }

  // Final summary
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || ''
    });
  `);
  console.log("\n=== Final Summary ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
