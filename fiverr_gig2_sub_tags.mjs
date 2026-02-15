// Verify subcategory and set tags for gig #2
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

  // Check current state
  let r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      catLabel: document.querySelector('.gig-category-wrapper [class*="singleValue"]')?.textContent?.trim() || '',
      subLabel: document.querySelector('.gig-subcategory-wrapper [class*="singleValue"]')?.textContent?.trim() || ''
    });
  `);
  console.log("Current state:", r);
  const state = JSON.parse(r);

  // Check if subcategory needs changing to Proofreading & Editing
  if (state.subLabel && !state.subLabel.includes('Proofreading')) {
    console.log(`Subcategory is "${state.subLabel}" - need to change to Proofreading & Editing`);

    // Open subcategory dropdown
    r = await eval_(`
      const subWrapper = document.querySelector('.gig-subcategory-wrapper');
      const control = subWrapper?.querySelector('[class*="control"]');
      if (control) {
        const rect = control.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no control' });
    `);
    const subCtrl = JSON.parse(r);
    if (!subCtrl.error) {
      await clickAt(send, subCtrl.x, subCtrl.y);
      await sleep(1000);

      // Check menu options
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
      console.log("Subcategory options:", r);
      const subOpts = JSON.parse(r);
      const proof = subOpts.find(o => o.text.includes('Proofreading'));
      if (proof) {
        console.log(`Selecting: ${proof.text}`);
        await clickAt(send, proof.x, proof.y);
        await sleep(2000);
      }
    }
  } else {
    console.log(`Subcategory OK: "${state.subLabel}"`);
  }

  // Now handle tags
  console.log("\n=== Adding Tags ===");
  const tags = ["proofreading", "editing", "rewriting", "content writing", "grammar check"];

  for (const tag of tags) {
    // Check current tag count
    r = await eval_(`
      const selected = document.querySelectorAll('.react-tags__selected-tag, [class*="tag-item"]');
      return selected.length;
    `);
    console.log(`Tags so far: ${r}`);
    if (parseInt(r) >= 5) { console.log("5 tags reached"); break; }

    // Find and click tag input
    r = await eval_(`
      const input = document.querySelector('.react-tags__search-input input, input[placeholder*="tag"]');
      if (input) {
        input.focus();
        input.value = '';
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(input, '');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        const rect = input.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no tag input' });
    `);
    const tagInput = JSON.parse(r);
    if (tagInput.error) {
      console.log("No tag input found");
      // Try to find it differently
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            id: el.id || '',
            name: el.name || '',
            placeholder: el.placeholder || '',
            class: (el.className?.toString() || '').substring(0, 60),
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(inputs);
      `);
      console.log("All visible inputs:", r);
      break;
    }

    await clickAt(send, tagInput.x, tagInput.y);
    await sleep(300);

    // Type the tag using insertText
    await send("Input.insertText", { text: tag });
    await sleep(1200);

    // Check for suggestions
    r = await eval_(`
      const suggestions = Array.from(document.querySelectorAll('.react-tags__suggestions li, [class*="suggestion"] li'));
      if (suggestions.length > 0) {
        const first = suggestions[0];
        const text = first.textContent.trim().substring(0, 40);
        const rect = first.getBoundingClientRect();
        return JSON.stringify({
          found: true,
          text: text,
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        });
      }
      return JSON.stringify({ found: false });
    `);
    const suggestion = JSON.parse(r);

    if (suggestion.found) {
      console.log(`"${tag}" -> clicking suggestion: "${suggestion.text}"`);
      await clickAt(send, suggestion.x, suggestion.y);
    } else {
      console.log(`"${tag}" -> no suggestion, pressing Enter`);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
      await sleep(50);
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
    }
    await sleep(600);
  }

  // Verify tags
  r = await eval_(`
    const tagList = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
    const visibleTags = Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="tag-item"]'))
      .map(el => el.textContent.trim().substring(0, 30));
    return JSON.stringify({ tagList, visibleTags });
  `);
  console.log("\nTag verification:", r);

  // Final state check
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      catLabel: document.querySelector('.gig-category-wrapper [class*="singleValue"]')?.textContent?.trim() || '',
      subLabel: document.querySelector('.gig-subcategory-wrapper [class*="singleValue"]')?.textContent?.trim() || ''
    });
  `);
  console.log("\n=== Final State ===");
  console.log(r);
  const final = JSON.parse(r);

  // Save & Continue if all fields are filled
  if (final.title && final.category && final.subcategory && final.tags) {
    console.log("\nAll fields filled! Clicking Save & Continue...");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Save & Continue');
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btn.disabled });
      }
      return JSON.stringify({ error: 'no button' });
    `);
    console.log("Save button:", r);
    const saveBtn = JSON.parse(r);

    if (!saveBtn.error && !saveBtn.disabled) {
      await clickAt(send, saveBtn.x, saveBtn.y);
      await sleep(5000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          body: (document.body?.innerText || '').substring(0, 500)
        });
      `);
      console.log("After save:", r);
    }
  } else {
    console.log("\nMissing fields:");
    if (!final.title) console.log("  - title");
    if (!final.category) console.log("  - category");
    if (!final.subcategory) console.log("  - subcategory");
    if (!final.tags) console.log("  - tags");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
