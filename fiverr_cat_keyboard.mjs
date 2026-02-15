// Change Fiverr category using keyboard navigation via CDP Input domain
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connect() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com") && t.url.includes("edit") && t.type === "page");
  if (!tab) throw new Error("No Fiverr edit tab found. Current tabs: " + tabs.filter(t=>t.type==="page").map(t=>t.url).join(", "));
  console.log(`Connected: ${tab.url}`);
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
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (r.exceptionDetails) {
      console.error("JS Error:", JSON.stringify(r.exceptionDetails).substring(0, 300));
      return null;
    }
    return r.result?.value;
  };

  // Send a real keyboard event via CDP Input domain
  async function pressKey(key, code, keyCode) {
    await send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key,
      code,
      windowsVirtualKeyCode: keyCode,
      nativeVirtualKeyCode: keyCode
    });
    await sleep(50);
    await send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key,
      code,
      windowsVirtualKeyCode: keyCode,
      nativeVirtualKeyCode: keyCode
    });
  }

  async function typeText(text) {
    for (const char of text) {
      await send("Input.dispatchKeyEvent", {
        type: "keyDown",
        key: char,
        text: char,
        unmodifiedText: char
      });
      await send("Input.dispatchKeyEvent", {
        type: "keyUp",
        key: char
      });
      await sleep(80);
    }
  }

  return { ws, send, eval_, pressKey, typeText };
}

async function main() {
  const { ws, send, eval_, pressKey, typeText } = await connect();

  // Focus the main category input
  console.log("=== Focusing category dropdown ===");
  await eval_(`
    (function() {
      const input = document.querySelector('#react-select-2-input');
      if (input) input.focus();
      return input ? 'focused' : 'not found';
    })()
  `);
  await sleep(500);

  // Clear any existing text in the input
  await pressKey("Backspace", "Backspace", 8);
  await pressKey("Backspace", "Backspace", 8);
  await sleep(300);

  // Open dropdown with ArrowDown
  console.log("Opening dropdown with ArrowDown...");
  await pressKey("ArrowDown", "ArrowDown", 40);
  await sleep(1000);

  // Check if options appeared
  let options = await eval_(`
    JSON.stringify(
      Array.from(document.querySelectorAll('[id*="react-select-2-option"]')).map(o => o.textContent.trim()).slice(0, 20)
    )
  `);
  console.log("Options after ArrowDown:", options);

  if (!options || options === '[]') {
    // Try Space to open
    console.log("Trying Space key...");
    await pressKey(" ", "Space", 32);
    await sleep(1000);
    options = await eval_(`
      JSON.stringify(
        Array.from(document.querySelectorAll('[id*="react-select-2-option"]')).map(o => o.textContent.trim()).slice(0, 20)
      )
    `);
    console.log("Options after Space:", options);
  }

  if (!options || options === '[]') {
    // Try typing to search
    console.log("Typing 'Prog' to search...");
    await typeText("Prog");
    await sleep(1500);
    options = await eval_(`
      JSON.stringify(
        Array.from(document.querySelectorAll('[id*="react-select"][id*="option"]')).map(o => o.textContent.trim()).slice(0, 20)
      )
    `);
    console.log("Options after typing:", options);
  }

  // Find which option is "Programming & Tech" and navigate to it
  const parsed = JSON.parse(options || '[]');
  if (parsed.length > 0) {
    const targetIdx = parsed.findIndex(o => o.toLowerCase().includes('programming'));
    if (targetIdx >= 0) {
      console.log(`"Programming & Tech" is at index ${targetIdx}. Navigating...`);
      // Navigate down to it
      for (let i = 0; i <= targetIdx; i++) {
        await pressKey("ArrowDown", "ArrowDown", 40);
        await sleep(200);
      }
      // Check which option is focused
      const focused = await eval_(`
        (function() {
          const focused = document.querySelector('[id*="react-select-2-option"][class*="focused"]') ||
                          document.querySelector('[id*="react-select-2-option"][aria-selected="true"]');
          return focused ? focused.textContent.trim() : 'none focused';
        })()
      `);
      console.log("Focused option:", focused);

      // Press Enter to select
      console.log("Pressing Enter to select...");
      await pressKey("Enter", "Enter", 13);
      await sleep(2000);
    } else {
      console.log("Programming & Tech not found in options. Trying to type it...");
      // Clear and type
      await pressKey("Backspace", "Backspace", 8);
      await pressKey("Backspace", "Backspace", 8);
      await pressKey("Backspace", "Backspace", 8);
      await pressKey("Backspace", "Backspace", 8);
      await typeText("Programming");
      await sleep(1500);

      const filtered = await eval_(`
        JSON.stringify(
          Array.from(document.querySelectorAll('[id*="react-select"][id*="option"]')).map(o => o.textContent.trim())
        )
      `);
      console.log("Filtered:", filtered);

      // Select first match
      await pressKey("Enter", "Enter", 13);
      await sleep(2000);
    }
  } else {
    console.log("No options appeared. Trying direct type + enter...");
    await typeText("Programming");
    await sleep(1500);
    await pressKey("Enter", "Enter", 13);
    await sleep(2000);
  }

  // Verify main category changed
  const catState = await eval_(`
    JSON.stringify({
      singleValues: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      bodySnippet: document.body.innerText.substring(
        Math.max(0, document.body.innerText.indexOf('Category')),
        document.body.innerText.indexOf('Category') + 150
      )
    })
  `);
  console.log("\nCategory state after selection:", catState);

  // Now handle subcategory
  console.log("\n=== Handling subcategory ===");
  await sleep(1000);

  // Focus subcategory
  await eval_(`
    (function() {
      const input = document.querySelector('#react-select-3-input');
      if (input) input.focus();
      return input ? 'sub focused' : 'sub not found';
    })()
  `);
  await sleep(500);

  // Open with arrow down
  await pressKey("ArrowDown", "ArrowDown", 40);
  await sleep(1000);

  const subOptions = await eval_(`
    JSON.stringify(
      Array.from(document.querySelectorAll('[id*="react-select-3-option"]')).map(o => o.textContent.trim()).slice(0, 20)
    )
  `);
  console.log("Subcategory options:", subOptions);

  if (subOptions && subOptions !== '[]') {
    const subParsed = JSON.parse(subOptions);
    // Look for AI-related option
    const priorities = ['ai app', 'ai agent', 'chatbot', 'ai service', 'software', 'web app', 'api'];
    let targetSub = -1;
    for (const kw of priorities) {
      targetSub = subParsed.findIndex(o => o.toLowerCase().includes(kw));
      if (targetSub >= 0) break;
    }

    if (targetSub >= 0) {
      console.log(`Target subcategory at index ${targetSub}: "${subParsed[targetSub]}"`);
      for (let i = 0; i <= targetSub; i++) {
        await pressKey("ArrowDown", "ArrowDown", 40);
        await sleep(200);
      }
      await pressKey("Enter", "Enter", 13);
      await sleep(2000);
    } else {
      // Type to filter
      await typeText("AI");
      await sleep(1500);
      await pressKey("Enter", "Enter", 13);
      await sleep(2000);
    }
  } else {
    // Type to search
    await typeText("AI");
    await sleep(1500);
    const subFiltered = await eval_(`
      JSON.stringify(
        Array.from(document.querySelectorAll('[id*="react-select"][id*="option"]')).map(o => o.textContent.trim())
      )
    `);
    console.log("Sub filtered:", subFiltered);
    await pressKey("Enter", "Enter", 13);
    await sleep(2000);
  }

  // Final verification
  const finalState = await eval_(`
    JSON.stringify({
      title: document.querySelector('textarea')?.value,
      categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
      url: window.location.href
    })
  `);
  console.log("\n=== FINAL STATE ===");
  console.log(finalState);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
