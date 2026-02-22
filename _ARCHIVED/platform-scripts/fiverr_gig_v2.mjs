// Fill Fiverr gig form - proper react-select handling
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

async function selectFromReactSelect(send, eval_, inputId, optionText) {
  // Focus the input
  await eval_(`document.getElementById(${JSON.stringify(inputId)})?.focus()`);
  await sleep(200);

  // Open dropdown with ArrowDown
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
  await sleep(800);

  // Find and click the option
  const r = await eval_(`
    const options = Array.from(document.querySelectorAll('.category-option, [class*="__option"], [class*="option"]'))
      .filter(el => el.offsetParent !== null || el.closest('[class*="__menu"]'));
    const match = options.find(el => el.textContent.trim() === ${JSON.stringify(optionText)}) ||
                  options.find(el => el.textContent.trim().includes(${JSON.stringify(optionText)}));
    if (match) {
      match.click();
      return 'selected: ' + match.textContent.trim();
    }
    return 'not found. available: ' + options.map(o => o.textContent.trim()).join(', ');
  `);
  return r;
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Step 1: Select Category - "Data"
  console.log("=== 1. Selecting Category: Data ===");
  let r = await selectFromReactSelect(send, eval_, 'react-select-2-input', 'Data');
  console.log(r);
  await sleep(1500);

  // Step 2: Select Subcategory
  console.log("\n=== 2. Selecting Subcategory ===");
  // First see what subcategories are available for "Data"
  await eval_(`document.getElementById('react-select-3-input')?.focus()`);
  await sleep(200);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
  await sleep(1000);

  r = await eval_(`
    const options = Array.from(document.querySelectorAll('.category-option, [class*="__option"], [class*="option"]'))
      .filter(el => {
        const menu = el.closest('[class*="__menu"]');
        return menu && menu.offsetParent !== null;
      });
    return JSON.stringify(options.map(o => o.textContent.trim()).slice(0, 20));
  `);
  console.log("Available subcategories:", r);

  // Try to select "Data Entry" or "Data Processing"
  r = await eval_(`
    const options = Array.from(document.querySelectorAll('.category-option, [class*="__option"], [class*="option"]'))
      .filter(el => el.closest('[class*="__menu"]'));
    const match = options.find(el => el.textContent.trim().includes('Data Entry')) ||
                  options.find(el => el.textContent.trim().includes('Data Processing')) ||
                  options.find(el => el.textContent.trim().includes('Data'));
    if (match) {
      match.click();
      return 'selected: ' + match.textContent.trim();
    }
    // If no match, just click the first option
    if (options.length > 0) {
      options[0].click();
      return 'selected first: ' + options[0].textContent.trim();
    }
    return 'no options';
  `);
  console.log(r);
  await sleep(1000);

  // Check hidden values
  r = await eval_(`
    return JSON.stringify({
      category: document.querySelector('input[name="gig[category_id]"]')?.value,
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value
    });
  `);
  console.log("Hidden values:", r);

  // Step 3: Add Tags
  console.log("\n=== 3. Adding Tags ===");
  const tags = ["data entry", "excel", "spreadsheet", "data processing", "typing"];

  // Find the tag input - it's the anonymous input at y~815
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'))
      .filter(i => i.offsetParent !== null && !i.id.includes('react-select') && !i.type.includes('hidden') && !i.type.includes('checkbox'));
    return JSON.stringify(inputs.map(i => ({
      tag: i.tagName, type: i.type, id: i.id, name: i.name,
      class: i.className?.substring(0, 80),
      rect: { y: Math.round(i.getBoundingClientRect().y), w: Math.round(i.getBoundingClientRect().width), h: Math.round(i.getBoundingClientRect().height) },
      placeholder: i.placeholder
    })));
  `);
  console.log("All visible inputs:", r);

  // The tag input is likely the small one near the bottom
  for (const tag of tags) {
    console.log(`\n  Adding tag: "${tag}"`);

    // Click the tag input area
    r = await eval_(`
      // Find the tag section by looking for the nearest input to "Search tags" text
      const inputs = Array.from(document.querySelectorAll('input'))
        .filter(i => !i.id.includes('react-select') && !i.type.includes('hidden') && !i.type.includes('checkbox'));
      // Get the one that's not a react-select and is at the bottom
      const tagInput = inputs.find(i => {
        const rect = i.getBoundingClientRect();
        return rect.y > 700 && rect.width > 0;
      }) || inputs[inputs.length - 1];

      if (tagInput) {
        tagInput.scrollIntoView({ block: 'center' });
        tagInput.focus();
        tagInput.click();
        const rect = tagInput.getBoundingClientRect();
        return JSON.stringify({ found: true, y: rect.y, w: rect.width, h: rect.height });
      }
      return JSON.stringify({ found: false });
    `);
    console.log(`    Input: ${r}`);

    const info = JSON.parse(r);
    if (info.found) {
      // Type the tag
      await send("Input.insertText", { text: tag });
      await sleep(500);

      // Check for autocomplete suggestions
      r = await eval_(`
        const suggestions = Array.from(document.querySelectorAll('[class*="suggestion"], [class*="Suggestion"], [class*="autocomplete"], [role="option"], [role="listbox"] li'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 50));
        return JSON.stringify(suggestions);
      `);
      const suggestions = JSON.parse(r);
      console.log(`    Suggestions: ${suggestions.length > 0 ? suggestions.join(', ') : 'none'}`);

      if (suggestions.length > 0) {
        // Click the first suggestion
        await eval_(`
          const sugg = Array.from(document.querySelectorAll('[class*="suggestion"], [class*="Suggestion"], [class*="autocomplete"], [role="option"], [role="listbox"] li'))
            .filter(el => el.offsetParent !== null)[0];
          if (sugg) sugg.click();
        `);
      } else {
        // Press Enter to add the tag
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
      }
      await sleep(500);
    }
  }

  // Check tags
  r = await eval_(`
    const hiddenTags = document.querySelector('input[name="gig[tag_list]"]')?.value;
    const tagChips = Array.from(document.querySelectorAll('[class*="tag-item"], [class*="TagItem"], [class*="chip"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 30));
    return JSON.stringify({ hiddenTags, tagChips });
  `);
  console.log("\nTags state:", r);

  // Step 4: Verify form
  console.log("\n=== 4. Form Summary ===");
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || ''
    });
  `);
  console.log(r);

  const formState = JSON.parse(r);

  // Step 5: Save & Continue if all fields are filled
  if (formState.title && formState.category && formState.subcategory) {
    console.log("\n=== 5. Save & Continue ===");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Save & Continue'));
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
      }
      return null;
    `);

    if (r) {
      const pos = JSON.parse(r);
      console.log("Clicking Save & Continue...");
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(5000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          title: document.title,
          preview: document.body.innerText.substring(0, 2000),
          errors: Array.from(document.querySelectorAll('[class*="error" i], [role="alert"]'))
            .filter(el => el.offsetParent !== null)
            .map(el => el.textContent.trim().substring(0, 100))
            .filter(t => t.length > 3)
        });
      `);
      const result = JSON.parse(r);
      console.log("URL:", result.url);
      console.log("Errors:", result.errors);
      console.log("Preview:", result.preview.substring(0, 500));
    }
  } else {
    console.log("\nMissing fields — cannot save yet");
    console.log("Missing:", !formState.title ? 'title' : '', !formState.category ? 'category' : '', !formState.subcategory ? 'subcategory' : '');
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
