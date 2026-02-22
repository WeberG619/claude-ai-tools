// Add tags to Fiverr gig - clean approach with insertText
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

  // Step 1: Find and scroll to the tag input
  console.log("=== Finding tag input ===");
  let r = await eval_(`
    const input = Array.from(document.querySelectorAll('input[type="text"]'))
      .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
      .find(i => i.getBoundingClientRect().width > 100);
    if (input) {
      input.scrollIntoView({ block: 'center' });
      return JSON.stringify({
        found: true,
        value: input.value.substring(0, 60),
        rect: {
          x: Math.round(input.getBoundingClientRect().x + input.getBoundingClientRect().width/2),
          y: Math.round(input.getBoundingClientRect().y + input.getBoundingClientRect().height/2),
          w: Math.round(input.getBoundingClientRect().width)
        }
      });
    }
    return JSON.stringify({ found: false });
  `);
  console.log("Tag input:", r);

  const inputInfo = JSON.parse(r);
  if (!inputInfo.found) {
    console.log("Tag input not found!");
    ws.close();
    return;
  }

  // Step 2: Click the input to focus
  console.log("\n=== Clearing and focusing input ===");
  await send("Input.dispatchMouseEvent", {
    type: "mousePressed", x: inputInfo.rect.x, y: inputInfo.rect.y,
    button: "left", clickCount: 1
  });
  await sleep(50);
  await send("Input.dispatchMouseEvent", {
    type: "mouseReleased", x: inputInfo.rect.x, y: inputInfo.rect.y,
    button: "left", clickCount: 1
  });
  await sleep(300);

  // Select all and delete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 }); // Ctrl+A
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
  await sleep(100);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(300);

  // Verify cleared
  r = await eval_(`
    const input = Array.from(document.querySelectorAll('input[type="text"]'))
      .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
      .find(i => i.getBoundingClientRect().width > 100);
    return input?.value || 'not found';
  `);
  console.log("After clear:", JSON.stringify(r));

  // Step 3: Add each tag one at a time
  for (const tag of tags) {
    console.log(`\n--- Adding tag: "${tag}" ---`);

    // Click input
    await send("Input.dispatchMouseEvent", {
      type: "mousePressed", x: inputInfo.rect.x, y: inputInfo.rect.y,
      button: "left", clickCount: 1
    });
    await sleep(50);
    await send("Input.dispatchMouseEvent", {
      type: "mouseReleased", x: inputInfo.rect.x, y: inputInfo.rect.y,
      button: "left", clickCount: 1
    });
    await sleep(200);

    // Type using insertText (single operation, no double chars)
    await send("Input.insertText", { text: tag });
    await sleep(800);

    // Check for suggestions/autocomplete
    r = await eval_(`
      const suggestions = Array.from(document.querySelectorAll('li, [class*="suggestion"], [class*="option"], [role="option"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 700)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          rect: { x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
                  y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }
        }));
      return JSON.stringify(suggestions);
    `);
    const suggestions = JSON.parse(r);
    console.log("Suggestions:", suggestions.map(s => s.text));

    if (suggestions.length > 0) {
      // Click the first suggestion
      const s = suggestions[0];
      console.log(`Clicking suggestion: "${s.text}"`);
      await send("Input.dispatchMouseEvent", {
        type: "mousePressed", x: s.rect.x, y: s.rect.y,
        button: "left", clickCount: 1
      });
      await sleep(50);
      await send("Input.dispatchMouseEvent", {
        type: "mouseReleased", x: s.rect.x, y: s.rect.y,
        button: "left", clickCount: 1
      });
    } else {
      // No suggestions - try pressing comma, then Enter
      console.log("No suggestions, pressing comma...");
      await send("Input.dispatchKeyEvent", {
        type: "keyDown", key: ",", code: "Comma", keyCode: 188
      });
      await send("Input.dispatchKeyEvent", { type: "char", text: "," });
      await send("Input.dispatchKeyEvent", {
        type: "keyUp", key: ",", code: "Comma", keyCode: 188
      });
      await sleep(300);

      // Also try Enter
      await send("Input.dispatchKeyEvent", {
        type: "keyDown", key: "Enter", code: "Enter", keyCode: 13
      });
      await send("Input.dispatchKeyEvent", {
        type: "keyUp", key: "Enter", code: "Enter", keyCode: 13
      });
    }
    await sleep(500);

    // Check if tag was added
    r = await eval_(`
      const tagList = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
      const chips = Array.from(document.querySelectorAll('[class*="tag"]'))
        .filter(el => {
          const cls = el.className?.toString() || '';
          return el.offsetParent !== null &&
                 (cls.includes('tag-item') || cls.includes('TagItem') || cls.includes('tag-value') || cls.includes('TagValue')) &&
                 el.textContent.trim().length > 1 && el.textContent.trim().length < 30;
        })
        .map(el => el.textContent.trim());
      const input = Array.from(document.querySelectorAll('input[type="text"]'))
        .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
        .find(i => i.getBoundingClientRect().width > 50);
      return JSON.stringify({ tagList, chips, inputValue: input?.value?.substring(0, 50) || '' });
    `);
    console.log("State:", r);
  }

  // Final check
  console.log("\n=== Final State ===");
  r = await eval_(`
    return JSON.stringify({
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      title: document.querySelector('input[name="gig[title]"]')?.value || document.querySelector('textarea')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      serviceType: document.querySelector('input[name="gig[service_type_id]"]')?.value || '',
      allGigInputs: Array.from(document.querySelectorAll('input[name^="gig["]'))
        .map(i => i.name + '=' + (i.value || '').substring(0, 50))
    });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
