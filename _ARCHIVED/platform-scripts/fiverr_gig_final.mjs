// Complete Fiverr gig form - service type + tags
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

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Step 1: Check current form state
  console.log("=== Current form state ===");
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      // Find ALL hidden inputs for the gig
      allHidden: Array.from(document.querySelectorAll('input[name^="gig["]'))
        .map(i => i.name + '=' + (i.value || '').substring(0, 50)),
      // Check for service type
      serviceType: document.querySelector('.gig-service-type-wrapper')?.textContent.trim().substring(0, 50)
    });
  `);
  console.log(r);

  // Step 2: Select Service Type if present
  console.log("\n=== 2. Service Type ===");
  r = await eval_(`
    // Find all react-select inputs
    const inputs = Array.from(document.querySelectorAll('input[id^="react-select"]'));
    return JSON.stringify(inputs.map(i => ({ id: i.id, aria: i.getAttribute('aria-label') })));
  `);
  console.log("React-select inputs:", r);

  // There might be a 3rd or 4th react-select for service type
  const reactInputs = JSON.parse(r);
  const serviceTypeInput = reactInputs.find(i => i.id !== 'react-select-2-input' && i.id !== 'react-select-3-input');

  if (serviceTypeInput) {
    console.log(`Found service type input: ${serviceTypeInput.id}`);
    await eval_(`document.getElementById(${JSON.stringify(serviceTypeInput.id)})?.focus()`);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
    await sleep(1000);

    r = await eval_(`
      const options = Array.from(document.querySelectorAll('.category-option, [class*="__option"]'))
        .filter(el => el.closest('[class*="__menu"]'));
      const texts = options.map(o => o.textContent.trim());
      if (options.length > 0) {
        // Select first option or look for something relevant
        const match = options.find(o => o.textContent.toLowerCase().includes('data entry')) ||
                      options.find(o => o.textContent.toLowerCase().includes('entry')) || options[0];
        match.click();
        return 'selected: ' + match.textContent.trim() + ' (from: ' + texts.join(', ') + ')';
      }
      return 'no options: ' + texts.join(', ');
    `);
    console.log(r);
    await sleep(500);
  } else {
    // Try opening the service type wrapper directly
    r = await eval_(`
      const wrapper = document.querySelector('.gig-service-type-wrapper');
      if (wrapper) {
        const input = wrapper.querySelector('input');
        if (input) {
          input.focus();
          return 'focused input in service-type: ' + input.id;
        }
        wrapper.click();
        return 'clicked wrapper';
      }
      return 'no service-type wrapper';
    `);
    console.log(r);

    if (r.includes('focused')) {
      await sleep(200);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
      await sleep(1000);

      r = await eval_(`
        const options = Array.from(document.querySelectorAll('.category-option, [class*="__option"]'))
          .filter(el => el.closest('[class*="__menu"]'));
        const texts = options.map(o => o.textContent.trim());
        if (options.length > 0) {
          options[0].click();
          return 'selected: ' + options[0].textContent.trim() + ' (from: ' + texts.join(', ') + ')';
        }
        return 'no options visible';
      `);
      console.log(r);
    }
  }

  // Step 3: Add Tags - Get the full HTML near the tag section
  console.log("\n=== 3. Tags - Full inspection ===");
  r = await eval_(`
    // Get the outer HTML of the tag section
    const tagSections = Array.from(document.querySelectorAll('*'))
      .filter(el => {
        const cls = el.className?.toString() || '';
        return cls.includes('tag') && (cls.includes('section') || cls.includes('Section') || cls.includes('wrapper') || cls.includes('Wrapper') || cls.includes('container') || cls.includes('Container'));
      })
      .map(el => ({
        class: el.className.toString().substring(0, 100),
        tag: el.tagName,
        html: el.outerHTML.substring(0, 500),
        inputInside: !!el.querySelector('input'),
        inputCount: el.querySelectorAll('input').length
      }));

    // Also directly look for the "Positive keywords" section
    const positiveKw = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.includes('Positive keywords') && el.children.length > 0)
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 100),
        tag: el.tagName,
        innerInputs: Array.from(el.querySelectorAll('input')).map(i => ({
          type: i.type, id: i.id, class: i.className?.substring(0, 60)
        }))
      }));

    return JSON.stringify({ tagSections: tagSections.slice(0, 5), positiveKw: positiveKw.slice(0, 3) });
  `);
  console.log(r);

  // Try to find the exact input element with a broader search
  r = await eval_(`
    // Scroll to tag section first
    const tagLabel = Array.from(document.querySelectorAll('*'))
      .find(el => el.textContent?.trim() === 'Positive keywords' && el.children.length === 0);
    if (tagLabel) tagLabel.scrollIntoView({ block: 'center' });

    // Now find the input
    const allInputs = Array.from(document.querySelectorAll('input'))
      .filter(i => i.type !== 'hidden' && i.type !== 'checkbox');

    return JSON.stringify(allInputs.map(i => ({
      id: i.id, type: i.type, name: i.name,
      class: (i.className?.toString() || '').substring(0, 100),
      rect: {
        x: Math.round(i.getBoundingClientRect().x),
        y: Math.round(i.getBoundingClientRect().y),
        w: Math.round(i.getBoundingClientRect().width),
        h: Math.round(i.getBoundingClientRect().height)
      },
      visible: i.offsetParent !== null
    })));
  `);
  console.log("\nAll non-hidden inputs after scroll:", r);

  // Try a click at the tag input area coordinates
  const inputs = JSON.parse(r);
  const tagInput = inputs.find(i => !i.id.includes('react-select') && i.visible && i.rect.w > 0 && i.rect.y > 200);

  if (tagInput) {
    console.log(`\nFound tag input at (${tagInput.rect.x}, ${tagInput.rect.y}) w=${tagInput.rect.w} h=${tagInput.rect.h}`);

    // Click exactly on the input
    const x = tagInput.rect.x + tagInput.rect.w / 2;
    const y = tagInput.rect.y + tagInput.rect.h / 2;
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    await sleep(300);

    // Clear any existing text
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(200);

    const tags = ["data entry", "excel", "spreadsheet", "data processing", "typing"];

    for (const tag of tags) {
      console.log(`\n  Adding: "${tag}"`);

      // Click the input area
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
      await sleep(200);

      // Type the tag
      for (const char of tag) {
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
        await send("Input.dispatchKeyEvent", { type: "char", text: char });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
        await sleep(30);
      }
      await sleep(800);

      // Check for autocomplete/suggestions
      r = await eval_(`
        const suggestItems = Array.from(document.querySelectorAll('[class*="suggest-item"], [class*="SuggestItem"], [class*="suggestion-item"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({ text: el.textContent.trim().substring(0, 50), class: el.className.substring(0, 80) }));

        // Also check for a list that appeared
        const lists = Array.from(document.querySelectorAll('ul, [role="listbox"]'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 300)
          .map(el => ({
            class: (el.className?.toString() || '').substring(0, 80),
            items: Array.from(el.children).filter(c => c.offsetParent !== null).map(c => c.textContent.trim().substring(0, 50)).slice(0, 5)
          }));

        return JSON.stringify({ suggestItems, lists });
      `);
      console.log(`    Autocomplete: ${r}`);

      const autoResult = JSON.parse(r);

      if (autoResult.suggestItems.length > 0) {
        // Click the suggestion
        await eval_(`
          const item = document.querySelector('[class*="suggest-item"], [class*="SuggestItem"]');
          if (item) item.click();
        `);
        console.log(`    Clicked suggestion: "${autoResult.suggestItems[0].text}"`);
      } else if (autoResult.lists.some(l => l.items.length > 0)) {
        // Click first list item
        const listWithItems = autoResult.lists.find(l => l.items.length > 0);
        await eval_(`
          const lists = Array.from(document.querySelectorAll('ul, [role="listbox"]'))
            .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 300);
          for (const list of lists) {
            const item = list.querySelector('li');
            if (item) { item.click(); break; }
          }
        `);
        console.log(`    Clicked list item: "${listWithItems.items[0]}"`);
      } else {
        // Press Enter
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", keyCode: 13 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", keyCode: 13 });
        console.log("    Pressed Enter");
      }
      await sleep(500);

      // Check if tag was added
      r = await eval_(`document.querySelector('input[name="gig[tag_list]"]')?.value || ''`);
      console.log(`    Hidden tags: "${r}"`);
    }
  } else {
    console.log("Tag input not found in visible inputs!");
  }

  // Final state
  console.log("\n=== Final Form State ===");
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      allHidden: Array.from(document.querySelectorAll('input[name^="gig["]'))
        .map(i => i.name + '=' + (i.value || '').substring(0, 50))
    });
  `);
  console.log(r);

  // Try Save & Continue
  const state = JSON.parse(r);
  if (state.tags) {
    console.log("\n=== Saving ===");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Save & Continue'));
      if (btn) { btn.click(); return 'clicked'; }
      return 'not found';
    `);
    console.log(r);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        errors: Array.from(document.querySelectorAll('[class*="error" i], [role="alert"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 100))
          .filter(t => t.length > 3)
      });
    `);
    console.log("Result:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
