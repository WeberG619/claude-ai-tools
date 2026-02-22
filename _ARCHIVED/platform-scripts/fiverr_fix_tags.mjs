// Find and fill the search tags input, then save
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

  // Step 1: Deep scan page for ALL input fields and their positions
  console.log("=== Step 1: Deep scan for tag/keyword inputs ===");
  const deepScan = await eval_(`
    (function() {
      const inputs = Array.from(document.querySelectorAll('input'));
      const textareas = Array.from(document.querySelectorAll('textarea'));
      const results = {
        inputs: inputs.map(i => {
          const rect = i.getBoundingClientRect();
          return {
            type: i.type,
            name: i.name,
            id: i.id,
            placeholder: i.placeholder,
            value: i.value,
            class: i.className.substring(0, 50),
            visible: rect.width > 0 && rect.height > 0,
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2)
          };
        }).filter(i => i.visible),
        textareas: textareas.map(t => ({
          name: t.name,
          id: t.id,
          value: t.value.substring(0, 40),
          class: t.className.substring(0, 40)
        })),
        // Search for tag-related elements
        tagElements: Array.from(document.querySelectorAll('[class*="tag"], [class*="Tag"]')).map(el => ({
          tag: el.tagName,
          class: el.className.substring(0, 60),
          text: el.textContent.substring(0, 80),
          hasInput: !!el.querySelector('input')
        })).slice(0, 10),
        // Check error details
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [role="alert"]'))
          .map(e => e.textContent.trim().substring(0, 150))
          .filter(t => t.length > 0)
      };
      return JSON.stringify(results);
    })()
  `);
  console.log("Deep scan:", deepScan);

  const scan = JSON.parse(deepScan);

  // Step 2: Scroll down to find the tags section (it might be below viewport)
  console.log("\n=== Step 2: Scroll to tags section ===");
  const scrollResult = await eval_(`
    (function() {
      // Find the search tags group by scrolling to it
      const tagGroup = document.querySelector('.gig-search-tags-group') ||
                      document.querySelector('[class*="search-tag"]') ||
                      document.querySelector('[class*="SearchTag"]');

      if (tagGroup) {
        tagGroup.scrollIntoView({ block: 'center' });
        const rect = tagGroup.getBoundingClientRect();
        return JSON.stringify({
          found: true,
          class: tagGroup.className.substring(0, 60),
          rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
          html: tagGroup.innerHTML.substring(0, 300),
          inputs: Array.from(tagGroup.querySelectorAll('input')).map(i => ({
            type: i.type, placeholder: i.placeholder, name: i.name,
            rect: (() => { const r = i.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
          }))
        });
      }

      // Try finding by label text
      const allLabels = Array.from(document.querySelectorAll('label'));
      const tagLabel = allLabels.find(l => l.textContent.toLowerCase().includes('search tag') || l.textContent.toLowerCase().includes('tag your'));
      if (tagLabel) {
        tagLabel.scrollIntoView({ block: 'center' });
        const container = tagLabel.closest('div');
        const input = container?.querySelector('input');
        return JSON.stringify({
          foundByLabel: true,
          labelText: tagLabel.textContent.trim().substring(0, 60),
          inputFound: !!input,
          inputRect: input ? (() => { const r = input.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })() : null
        });
      }

      // Look for any heading about "tags"
      const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6, [class*="heading"], [class*="title"]'));
      const tagHeading = headings.find(h => h.textContent.toLowerCase().includes('tag'));

      return JSON.stringify({
        found: false,
        tagHeading: tagHeading?.textContent?.trim() || 'none',
        pageText: document.body.innerText.substring(0, 300)
      });
    })()
  `);
  console.log("Scroll result:", scrollResult);
  await sleep(500);

  // Step 3: Now check if we can see the tags after scrolling
  const afterScroll = await eval_(`
    (function() {
      const tagGroup = document.querySelector('.gig-search-tags-group');
      if (!tagGroup) return 'still not found';

      const input = tagGroup.querySelector('input[type="text"]');
      if (input) {
        const rect = input.getBoundingClientRect();
        return JSON.stringify({
          inputVisible: rect.width > 0 && rect.height > 0,
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2),
          placeholder: input.placeholder,
          existingTags: Array.from(tagGroup.querySelectorAll('.tag-item')).map(t => t.textContent.trim())
        });
      }

      // Maybe tags are rendered differently now
      return JSON.stringify({
        groupHTML: tagGroup.innerHTML.substring(0, 500),
        groupText: tagGroup.textContent.substring(0, 200)
      });
    })()
  `);
  console.log("After scroll:", afterScroll);

  // Step 4: Try to add tags
  if (afterScroll && afterScroll.includes('"x"')) {
    const inputCoords = JSON.parse(afterScroll);
    console.log(`\n=== Step 4: Adding tags at (${inputCoords.x}, ${inputCoords.y}) ===`);

    const newTags = ["MCP server", "AI integration", "Claude API", "automation", "chatbot"];
    for (const tag of newTags) {
      // Click input
      await cdpClick(inputCoords.x, inputCoords.y);
      await sleep(200);

      // Focus via JS
      await eval_(`
        (function() {
          const input = document.querySelector('.gig-search-tags-group input[type="text"]');
          if (input) { input.focus(); input.value = ''; }
        })()
      `);
      await sleep(150);

      // Type
      await typeText(tag);
      await sleep(300);

      // Enter
      await pressKey("Enter", "Enter", 13);
      await sleep(500);

      const count = await eval_(`document.querySelectorAll('.gig-search-tags-group .tag-item').length`);
      console.log(`  Added "${tag}" (tags: ${count})`);
    }
  } else {
    // Try a completely different approach - use React state
    console.log("\n=== Step 4: Try React-based tag approach ===");

    // Check if there's a React select for tags too
    const tagSelectInfo = await eval_(`
      (function() {
        // Check all react-select inputs that we haven't used yet
        const allReactSelects = Array.from(document.querySelectorAll('[id*="react-select"][id*="-input"]'));
        return JSON.stringify(allReactSelects.map(input => {
          let fiber = null;
          for (const key of Object.keys(input)) {
            if (key.startsWith('__reactFiber')) { fiber = input[key]; break; }
          }
          let options = [];
          let isMulti = false;
          if (fiber) {
            let current = fiber;
            for (let d = 0; d < 20; d++) {
              const props = current?.memoizedProps;
              if (props?.isMulti !== undefined) isMulti = props.isMulti;
              if (props?.options?.length > 0) {
                options = props.options.slice(0, 3).map(o => typeof o === 'string' ? o : (o.label || JSON.stringify(o).substring(0, 30)));
                break;
              }
              current = current?.return;
            }
          }
          return { id: input.id, isMulti, sampleOptions: options };
        }));
      })()
    `);
    console.log("React select scan:", tagSelectInfo);

    // Maybe it's a simple input that needs React controlled value
    const tryReactInput = await eval_(`
      (function() {
        // Search for any input that's specifically for tags
        const allInputs = Array.from(document.querySelectorAll('input')).filter(i => i.offsetParent !== null);
        const tagInput = allInputs.find(i =>
          i.placeholder?.toLowerCase().includes('tag') ||
          i.name?.toLowerCase().includes('tag') ||
          i.closest('[class*="tag"]')
        );

        if (tagInput) {
          // Set value using React setter
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          nativeInputValueSetter.call(tagInput, 'MCP server');
          tagInput.dispatchEvent(new Event('input', { bubbles: true }));
          tagInput.dispatchEvent(new Event('change', { bubbles: true }));
          // Try submitting with keydown
          tagInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
          return 'set via React setter: ' + tagInput.value;
        }

        return 'no tag input found. All visible inputs: ' + allInputs.map(i => i.placeholder || i.name || i.id || i.type).join(', ');
      })()
    `);
    console.log("React input attempt:", tryReactInput);
  }

  // Step 5: Check what's still missing
  console.log("\n=== Step 5: Check what metadata is missing ===");
  const metaCheck = await eval_(`
    (function() {
      // Check all form fields for completeness
      const result = {
        title: document.querySelector('textarea')?.value || '',
        categories: Array.from(document.querySelectorAll('[class*="singleValue"]')).map(s => s.textContent.trim()),
        tags: Array.from(document.querySelectorAll('.tag-item, [class*="tag-item"]')).map(t => t.textContent.trim()),
        // Look for any "required" markers or error messages
        requiredFields: Array.from(document.querySelectorAll('[class*="required"], [class*="mandatory"], .required'))
          .map(el => el.textContent.trim().substring(0, 60)),
        errorMessages: Array.from(document.querySelectorAll('[class*="error-message"], [class*="errorMessage"], [class*="error"], .error, .field-error'))
          .filter(el => el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim()),
        // Check all visible form sections
        formSections: Array.from(document.querySelectorAll('.form-input-group, [class*="form-group"], [class*="FormGroup"]'))
          .map(s => ({
            label: s.querySelector('label')?.textContent?.trim()?.substring(0, 40) || '',
            hasError: !!s.querySelector('[class*="error"]'),
            hasValue: !!(s.querySelector('input')?.value || s.querySelector('textarea')?.value || s.querySelector('[class*="singleValue"]'))
          }))
      };
      return JSON.stringify(result);
    })()
  `);
  console.log("Metadata check:", metaCheck);

  // Step 6: Try to save again
  console.log("\n=== Step 6: Save attempt ===");
  const saveResult = await eval_(`
    (function() {
      const btns = Array.from(document.querySelectorAll('button'));
      const saveBtn = btns.find(b => b.textContent.trim() === 'Save & Preview') ||
                     btns.find(b => b.textContent.trim() === 'Save');
      if (saveBtn) {
        saveBtn.click();
        return 'clicked: ' + saveBtn.textContent.trim();
      }
      return 'no save button';
    })()
  `);
  console.log("Save:", saveResult);
  await sleep(4000);

  const afterSave = await eval_(`
    JSON.stringify({
      url: window.location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [role="alert"]'))
        .map(e => e.textContent.trim().substring(0, 150))
        .filter(t => t.length > 0 && !t.includes('Skip'))
        .slice(0, 5)
    })
  `);
  console.log("After save:", afterSave);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
