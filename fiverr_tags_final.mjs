// Last attempt at Fiverr tags - use execCommand + Enter
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

  // First fix service type - select "Data Typing"
  console.log("=== Fixing Service Type ===");
  await eval_(`document.getElementById('react-select-4-input')?.focus()`);
  await sleep(200);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowDown", code: "ArrowDown" });
  await sleep(800);

  let r = await eval_(`
    const options = Array.from(document.querySelectorAll('.category-option, [class*="__option"]'))
      .filter(el => el.closest('[class*="__menu"]'));
    const texts = options.map(o => o.textContent.trim());
    // Select "Data Typing" specifically
    const match = options.find(o => o.textContent.trim() === 'Data Typing') || options[1];
    if (match) { match.click(); return 'selected: ' + match.textContent.trim() + ' | all: ' + texts.join(', '); }
    return 'no options: ' + texts.join(', ');
  `);
  console.log(r);
  await sleep(500);

  // Now try tags - get the tag input's React internal state key
  console.log("\n=== Tag Input - React Internals ===");
  r = await eval_(`
    const input = Array.from(document.querySelectorAll('input[type="text"]'))
      .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
      .find(i => i.getBoundingClientRect().width > 10);

    if (!input) return 'tag input not found';

    // Get React fiber key
    const reactKeys = Object.keys(input).filter(k =>
      k.startsWith('__react') || k.startsWith('__REACT')
    );

    // Get event handlers on the input
    const eventProps = Object.keys(input).filter(k =>
      k.startsWith('on') || k.includes('Handler') || k.includes('Event')
    );

    // Get the React props
    let props = {};
    for (const key of reactKeys) {
      try {
        const fiber = input[key];
        if (fiber?.memoizedProps) {
          props = {
            onChange: !!fiber.memoizedProps.onChange,
            onKeyDown: !!fiber.memoizedProps.onKeyDown,
            onKeyUp: !!fiber.memoizedProps.onKeyUp,
            onKeyPress: !!fiber.memoizedProps.onKeyPress,
            onBlur: !!fiber.memoizedProps.onBlur,
            value: fiber.memoizedProps.value,
            placeholder: fiber.memoizedProps.placeholder
          };
        }
      } catch (e) {}
    }

    return JSON.stringify({
      found: true,
      rect: { x: input.getBoundingClientRect().x, y: input.getBoundingClientRect().y, w: input.getBoundingClientRect().width },
      reactKeys,
      eventProps: eventProps.slice(0, 10),
      props,
      currentValue: input.value
    });
  `);
  console.log(r);

  // Clear the tag input
  console.log("\n=== Clearing & Adding Tags ===");
  r = await eval_(`
    const input = Array.from(document.querySelectorAll('input[type="text"]'))
      .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
      .find(i => i.getBoundingClientRect().width > 10);
    if (input) {
      input.scrollIntoView({ block: 'center' });
      input.focus();
      // Triple-click to select all
      input.select();
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      return 'cleared: "' + input.value + '"';
    }
    return 'not found';
  `);
  console.log(r);
  await sleep(300);

  // Try adding tags one at a time with native React event simulation
  const tags = ["data entry", "excel", "spreadsheet", "data processing", "typing"];

  for (const tag of tags) {
    console.log(`\n  Tag: "${tag}"`);

    // Use the React setter to properly update the input value
    r = await eval_(`
      const input = Array.from(document.querySelectorAll('input[type="text"]'))
        .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
        .find(i => i.getBoundingClientRect().y > 200);
      if (!input) return 'not found';

      input.focus();

      // Use native input value setter to bypass React
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeInputValueSetter.call(input, ${JSON.stringify(tag)});

      // Dispatch input event
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));

      return 'set value to: ' + input.value;
    `);
    console.log(`    ${r}`);
    await sleep(500);

    // Now press Enter to commit
    r = await eval_(`
      const input = Array.from(document.querySelectorAll('input[type="text"]'))
        .filter(i => !i.id.includes('react-select') && i.offsetParent !== null)
        .find(i => i.getBoundingClientRect().y > 200);
      if (!input) return 'not found';

      input.focus();

      // Dispatch keydown Enter event
      const enterEvent = new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
      });
      input.dispatchEvent(enterEvent);

      // Also try keypress and keyup
      input.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
      input.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));

      return 'enter dispatched, value now: ' + input.value;
    `);
    console.log(`    ${r}`);
    await sleep(300);

    // Check if tag was added
    r = await eval_(`
      const tags = document.querySelector('input[name="gig[tag_list]"]')?.value || '';
      const chips = Array.from(document.querySelectorAll('[class*="tag-item"], [class*="TagItem"], [class*="chip"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length < 30 && el.textContent.trim().length > 1)
        .map(el => el.textContent.trim());
      // Also check near the tag section
      const tagSection = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          const cls = el.className?.toString() || '';
          return el.offsetParent !== null && (cls.includes('tag-value') || cls.includes('TagValue') || cls.includes('tag-list') || cls.includes('TagList'));
        })
        .map(el => ({ class: el.className.substring(0, 60), text: el.textContent.trim().substring(0, 30) }));
      return JSON.stringify({ hiddenTags: tags, chips, tagSection });
    `);
    console.log(`    State: ${r}`);
  }

  // Final check
  console.log("\n=== Final State ===");
  r = await eval_(`
    const preview = document.body.innerText.substring(
      document.body.innerText.indexOf('Search tags'),
      document.body.innerText.indexOf('Search tags') + 500
    );
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value,
      category: document.querySelector('input[name="gig[category_id]"]')?.value,
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value,
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value,
      tagAreaText: preview
    });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
