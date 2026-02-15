// Add Fiverr tags via CDP - target right monitor Chrome
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

  // Find the tag input - it's the only non-react-select text input with content
  let r = await eval_(`
    const allInputs = Array.from(document.querySelectorAll('input[type="text"]'));
    return JSON.stringify(allInputs.map((el, i) => ({
      index: i,
      id: el.id,
      value: el.value.substring(0, 60),
      width: Math.round(el.getBoundingClientRect().width),
      y: Math.round(el.getBoundingClientRect().y),
      visible: el.offsetParent !== null,
      isReactSelect: el.id.includes('react-select')
    })));
  `);
  console.log("All text inputs:", r);

  const inputs = JSON.parse(r);
  // The tag input is the one that is NOT react-select, is visible, and has garbled content
  const tagInput = inputs.find(i => !i.isReactSelect && i.visible && i.value.length > 5);
  // Or if not found by value, find by position (it's below the service type dropdowns)
  const tagInputAlt = inputs.find(i => !i.isReactSelect && i.visible && i.width > 200);

  const target = tagInput || tagInputAlt;
  if (!target) {
    console.log("Tag input not found!");
    ws.close();
    return;
  }

  console.log(`\nFound tag input: index=${target.index}, value="${target.value}", width=${target.width}, y=${target.y}`);

  // Step 1: Focus the input and clear it completely
  console.log("\n=== Clearing tag input ===");
  await eval_(`
    const inputs = document.querySelectorAll('input[type="text"]');
    const el = inputs[${target.index}];
    el.scrollIntoView({ block: 'center' });
    el.focus();
    el.click();
  `);
  await sleep(300);

  // Use CDP to select all and delete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", windowsVirtualKeyCode: 65, modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", windowsVirtualKeyCode: 65 });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete", windowsVirtualKeyCode: 46 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete", windowsVirtualKeyCode: 46 });
  await sleep(300);

  // Also try Backspace
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace", windowsVirtualKeyCode: 8 });
  await sleep(200);

  // Check if cleared
  r = await eval_(`
    const inputs = document.querySelectorAll('input[type="text"]');
    return inputs[${target.index}]?.value || 'N/A';
  `);
  console.log("After clear attempt:", JSON.stringify(r));

  // If not cleared, try using React's native setter to force clear
  if (r && r.length > 5) {
    console.log("Force clearing via native setter...");
    await eval_(`
      const inputs = document.querySelectorAll('input[type="text"]');
      const el = inputs[${target.index}];
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(el, '');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    `);
    await sleep(300);

    r = await eval_(`document.querySelectorAll('input[type="text"]')[${target.index}]?.value`);
    console.log("After force clear:", JSON.stringify(r));
  }

  // Step 2: Add each tag
  for (const tag of tags) {
    console.log(`\n--- Adding: "${tag}" ---`);

    // Focus the input
    await eval_(`
      const el = document.querySelectorAll('input[type="text"]')[${target.index}];
      el.focus();
      el.click();
    `);
    await sleep(200);

    // Type via insertText
    await send("Input.insertText", { text: tag });
    await sleep(1000);

    // Check for autocomplete suggestions
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('li, [role="option"], [class*="suggestion"], [class*="option"]'))
        .filter(el => {
          if (!el.offsetParent) return false;
          const rect = el.getBoundingClientRect();
          return rect.y > 200 && rect.height > 10 && rect.height < 100;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items);
    `);
    const suggestions = JSON.parse(r);
    console.log("Suggestions:", suggestions.map(s => s.text));

    if (suggestions.length > 0 && !suggestions[0].text.includes('No matches')) {
      // Click the best matching suggestion
      const match = suggestions.find(s => s.text.toLowerCase().includes(tag.toLowerCase())) || suggestions[0];
      console.log(`Clicking: "${match.text}"`);
      await send("Input.dispatchMouseEvent", {
        type: "mousePressed", x: match.x, y: match.y, button: "left", clickCount: 1
      });
      await sleep(50);
      await send("Input.dispatchMouseEvent", {
        type: "mouseReleased", x: match.x, y: match.y, button: "left", clickCount: 1
      });
      await sleep(500);
    } else {
      // Press Enter to commit the tag
      console.log("Pressing Enter...");
      await send("Input.dispatchKeyEvent", {
        type: "keyDown", key: "Enter", code: "Enter",
        windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
      });
      await send("Input.dispatchKeyEvent", {
        type: "keyUp", key: "Enter", code: "Enter",
        windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13
      });
      await sleep(500);
    }

    // Check state
    r = await eval_(`
      const tagList = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
      const inputVal = document.querySelectorAll('input[type="text"]')[${target.index}]?.value || '';
      // Look for tag chips/pills
      const chips = Array.from(document.querySelectorAll('span, div'))
        .filter(el => {
          const cls = el.className?.toString() || '';
          const style = window.getComputedStyle(el);
          return el.offsetParent !== null &&
                 el.textContent.trim().length > 1 &&
                 el.textContent.trim().length < 25 &&
                 (cls.includes('tag') || cls.includes('Tag') || cls.includes('chip') || cls.includes('pill')) &&
                 el.querySelector('button, [class*="close"], [class*="remove"]');
        })
        .map(el => el.textContent.trim());
      return JSON.stringify({ tagList, inputVal: inputVal.substring(0, 40), chips });
    `);
    console.log("State:", r);
  }

  // Final verification
  console.log("\n\n=== FINAL STATE ===");
  r = await eval_(`
    return JSON.stringify({
      tagList: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      title: document.querySelector('textarea')?.value || '',
      allGig: Array.from(document.querySelectorAll('input[name^="gig["]'))
        .map(i => i.name + '=' + (i.value || '').substring(0, 40))
    });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
