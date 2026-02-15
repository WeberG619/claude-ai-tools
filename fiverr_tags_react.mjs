// Add Fiverr tags - react-tags component at input index 3
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

  const tags = ["data entry", "excel", "spreadsheet", "data processing", "typing"];

  // The tag input is at index 3, parent class "react-tags__search-input"
  const INPUT_SELECTOR = '.react-tags__search-input input';

  // Step 1: Clear the garbled text
  console.log("=== Clearing tag input ===");

  // Use React's internal setter to clear
  let r = await eval_(`
    const el = document.querySelector('${INPUT_SELECTOR}');
    if (!el) return 'NOT FOUND';
    el.scrollIntoView({ block: 'center' });
    el.focus();

    // Get React fiber to find the onChange handler
    const reactKey = Object.keys(el).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
    const propsKey = Object.keys(el).find(k => k.startsWith('__reactProps'));

    return JSON.stringify({
      found: true,
      value: el.value.substring(0, 60),
      reactKey: reactKey || 'none',
      propsKey: propsKey || 'none',
      hasOnChange: !!(el[propsKey]?.onChange)
    });
  `);
  console.log("Input:", r);

  // Focus and clear via CDP
  await eval_(`document.querySelector('${INPUT_SELECTOR}').focus()`);
  await sleep(200);

  // Select all + delete via CDP keystrokes
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(500);

  r = await eval_(`return document.querySelector('${INPUT_SELECTOR}')?.value || ''`);
  console.log("After Ctrl+A+Backspace:", JSON.stringify(r));

  // If still not cleared, keep pressing backspace
  if (r && r.length > 0) {
    console.log("Pressing backspace repeatedly...");
    for (let i = 0; i < 200; i++) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    }
    await sleep(300);
    r = await eval_(`return document.querySelector('${INPUT_SELECTOR}')?.value || ''`);
    console.log("After 200 backspaces:", JSON.stringify(r));
  }

  // Step 2: Add each tag
  for (const tag of tags) {
    console.log(`\n--- Adding: "${tag}" ---`);

    // Focus
    await eval_(`document.querySelector('${INPUT_SELECTOR}')?.focus()`);
    await sleep(200);

    // Type via insertText
    await send("Input.insertText", { text: tag });
    await sleep(1000);

    // Check current input value
    r = await eval_(`return document.querySelector('${INPUT_SELECTOR}')?.value || ''`);
    console.log("Input value after type:", JSON.stringify(r));

    // Check for suggestions
    r = await eval_(`
      const suggestions = Array.from(document.querySelectorAll('.react-tags__suggestions li, [class*="suggestion"] li, [role="option"], [role="listbox"] li'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          class: (el.className?.toString() || '').substring(0, 60)
        }));
      return JSON.stringify(suggestions);
    `);
    const suggestions = JSON.parse(r);
    console.log("Suggestions:", suggestions.map(s => `"${s.text}"`));

    if (suggestions.length > 0) {
      // Click the best match
      const match = suggestions.find(s => s.text.toLowerCase() === tag.toLowerCase()) ||
                    suggestions.find(s => s.text.toLowerCase().includes(tag.toLowerCase())) ||
                    suggestions[0];
      console.log(`Clicking suggestion: "${match.text}" at (${match.x}, ${match.y})`);
      await send("Input.dispatchMouseEvent", {
        type: "mousePressed", x: match.x, y: match.y, button: "left", clickCount: 1
      });
      await sleep(50);
      await send("Input.dispatchMouseEvent", {
        type: "mouseReleased", x: match.x, y: match.y, button: "left", clickCount: 1
      });
    } else {
      // Try Enter to commit
      console.log("No suggestions, pressing Enter...");
      await send("Input.dispatchKeyEvent", {
        type: "keyDown", key: "Enter", code: "Enter",
        windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
      });
      await send("Input.dispatchKeyEvent", {
        type: "keyUp", key: "Enter", code: "Enter",
        windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
      });
    }
    await sleep(500);

    // Check if tag was committed
    r = await eval_(`
      const tagList = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
      const chips = Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="react-tags__selected"]'))
        .map(el => el.textContent.trim().replace(/×/g, '').trim())
        .filter(t => t.length > 0);
      const inputVal = document.querySelector('${INPUT_SELECTOR}')?.value || '';
      return JSON.stringify({ tagList, chips, inputVal: inputVal.substring(0, 30) });
    `);
    console.log("Result:", r);
  }

  // Final state
  console.log("\n\n=== FINAL STATE ===");
  r = await eval_(`
    return JSON.stringify({
      tagList: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      allGig: Array.from(document.querySelectorAll('input[name^="gig["]'))
        .map(i => i.name + '=' + (i.value || '').substring(0, 50)),
      chips: Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="react-tags__selected"]'))
        .map(el => el.textContent.trim()),
      error: document.querySelector('.gig-upcrate-validation-error')?.textContent?.trim() || ''
    });
  `);
  console.log(r);

  const final = JSON.parse(r);
  if (final.tagList && !final.error) {
    console.log("\nTags committed! Clicking Save & Continue...");
    await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Save & Continue'));
      if (btn) { btn.scrollIntoView({ block: 'center' }); btn.click(); }
    `);
    await sleep(5000);
    r = await eval_(`return JSON.stringify({ url: location.href, preview: document.body?.innerText?.substring(0, 500) })`);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
