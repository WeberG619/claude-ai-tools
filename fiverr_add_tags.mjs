// Fix Fiverr tag entry - investigate and add tags properly
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

  // First clear any existing text in the tag input
  console.log("=== Clearing existing tag input ===");
  let r = await eval_(`
    const input = Array.from(document.querySelectorAll('input[type="text"]'))
      .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
      .find(i => i.getBoundingClientRect().y > 500);
    if (input) {
      input.focus();
      input.select();
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      return 'cleared, value: ' + input.value;
    }
    return 'not found';
  `);
  console.log(r);
  await sleep(300);

  // Investigate the tag input's parent structure
  console.log("\n=== Tag input DOM structure ===");
  r = await eval_(`
    const input = Array.from(document.querySelectorAll('input[type="text"]'))
      .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
      .find(i => i.getBoundingClientRect().y > 500);
    if (!input) return 'not found';

    let html = [];
    let el = input;
    for (let i = 0; i < 5; i++) {
      el = el.parentElement;
      if (!el) break;
      html.push({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 120),
        id: el.id,
        childCount: el.children.length,
        dataAttrs: Array.from(el.attributes).filter(a => a.name.startsWith('data-')).map(a => a.name + '=' + a.value.substring(0, 30))
      });
    }

    // Also look for sibling elements (tag chips, etc.)
    const container = input.closest('[class*="tag"], [class*="Tag"], [class*="chip"], [class*="Chip"]') || input.parentElement?.parentElement;
    const siblings = container ? Array.from(container.children).map(c => ({
      tag: c.tagName, class: (c.className?.toString() || '').substring(0, 80), text: c.textContent?.trim().substring(0, 30)
    })) : [];

    // Check for React fiber/props
    const reactKey = Object.keys(input).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance') || k.startsWith('__reactProps'));

    return JSON.stringify({
      parents: html,
      siblings,
      reactKey: reactKey || 'none',
      inputEvents: input.getAttribute('data-testid') || input.getAttribute('data-tag') || ''
    });
  `);
  console.log(r);

  // Try different approaches to add tags
  const tags = ["data entry", "excel", "spreadsheet", "data processing", "typing"];

  for (let i = 0; i < tags.length; i++) {
    const tag = tags[i];
    console.log(`\n=== Tag ${i+1}: "${tag}" ===`);

    // Focus the input
    await eval_(`
      const input = Array.from(document.querySelectorAll('input[type="text"]'))
        .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
        .find(i => i.getBoundingClientRect().y > 500);
      if (input) { input.focus(); input.click(); }
    `);
    await sleep(200);

    // Type character by character with key events
    for (const char of tag) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
      await send("Input.dispatchKeyEvent", { type: "char", text: char });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
      await sleep(30);
    }
    await sleep(1000);

    // Check for autocomplete
    r = await eval_(`
      const suggestions = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          if (!el.offsetParent) return false;
          const cls = (el.className?.toString() || '');
          return cls.includes('suggest') || cls.includes('Suggest') ||
                 cls.includes('autocomplete') || cls.includes('AutoComplete') ||
                 cls.includes('dropdown') || cls.includes('Dropdown') ||
                 el.getAttribute('role') === 'option' || el.getAttribute('role') === 'listbox';
        })
        .map(el => ({
          class: (el.className?.toString() || '').substring(0, 80),
          text: el.textContent?.trim().substring(0, 50),
          tag: el.tagName,
          role: el.getAttribute('role')
        }));
      return JSON.stringify(suggestions.slice(0, 10));
    `);
    console.log(`  Autocomplete: ${r}`);

    const suggestions = JSON.parse(r);
    if (suggestions.length > 0) {
      // Click the first suggestion
      const firstSugg = suggestions[0];
      console.log(`  Clicking suggestion: "${firstSugg.text}"`);
      await eval_(`
        const el = Array.from(document.querySelectorAll('*'))
          .filter(e => e.offsetParent !== null)
          .find(e => {
            const cls = (e.className?.toString() || '');
            return (cls.includes('suggest') || cls.includes('Suggest') || cls.includes('autocomplete') || cls.includes('dropdown') || e.getAttribute('role') === 'option') &&
                   e.textContent?.trim().includes(${JSON.stringify(firstSugg.text?.substring(0, 20) || '')});
          });
        if (el) {
          el.click();
          return 'clicked';
        }
        return 'not found';
      `);
      await sleep(500);
    } else {
      // Try pressing Enter to commit the tag
      console.log("  No suggestions, pressing Enter...");
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", keyCode: 13, which: 13 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", keyCode: 13, which: 13 });
      await sleep(500);

      // Check if tag was added
      r = await eval_(`
        const tags = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
        const input = Array.from(document.querySelectorAll('input[type="text"]'))
          .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
          .find(i => i.getBoundingClientRect().y > 500);
        return JSON.stringify({ tags, inputValue: input?.value || '' });
      `);
      console.log(`  After Enter: ${r}`);

      const afterEnter = JSON.parse(r);
      if (!afterEnter.tags && afterEnter.inputValue) {
        // Enter didn't work - try comma
        console.log("  Enter didn't work, trying comma...");
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: ",", code: "Comma" });
        await send("Input.dispatchKeyEvent", { type: "char", text: "," });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: ",", code: "Comma" });
        await sleep(500);

        r = await eval_(`
          const tags = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
          return tags;
        `);
        console.log(`  After comma: tags="${r}"`);
      }

      if (!r) {
        // Try Tab
        console.log("  Trying Tab...");
        // Focus back first
        await eval_(`
          const input = Array.from(document.querySelectorAll('input[type="text"]'))
            .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
            .find(i => i.getBoundingClientRect().y > 500);
          if (input) input.focus();
        `);
        await sleep(100);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
        await sleep(500);

        r = await eval_(`document.querySelector('input[name="gig[tag_list]"]')?.value || ''`);
        console.log(`  After Tab: tags="${r}"`);
      }
    }

    // Check current tag state
    r = await eval_(`
      const tags = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
      const chipEls = Array.from(document.querySelectorAll('span, div'))
        .filter(el => {
          const cls = el.className?.toString() || '';
          return el.offsetParent !== null && (cls.includes('tag') || cls.includes('Tag') || cls.includes('chip') || cls.includes('Chip')) &&
                 el.textContent.trim().length > 1 && el.textContent.trim().length < 30 &&
                 !cls.includes('container') && !cls.includes('Container');
        })
        .map(el => el.textContent.trim().substring(0, 30));
      return JSON.stringify({ hiddenTags: tags, chips: chipEls.slice(0, 10) });
    `);
    console.log(`  State: ${r}`);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
