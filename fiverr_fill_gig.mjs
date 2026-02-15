// Fill Fiverr gig creation form - Data Entry gig
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

async function typeInReactSelect(send, eval_, inputId, searchText) {
  // Focus the react-select input
  await eval_(`
    const el = document.getElementById(${JSON.stringify(inputId)});
    if (el) { el.focus(); el.click(); }
  `);
  await sleep(300);

  // Type character by character
  for (const char of searchText) {
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
    await send("Input.dispatchKeyEvent", { type: "char", text: char });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
    await sleep(50);
  }
  await sleep(1000);

  // Check dropdown options
  const r = await eval_(`
    const options = Array.from(document.querySelectorAll('[class*="option"], [id*="option"], [role="option"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({ text: el.textContent.trim().substring(0, 80), id: el.id || '' }));
    return JSON.stringify(options);
  `);

  const options = JSON.parse(r);
  console.log(`    Options for "${searchText}": ${options.map(o => o.text).join(', ')}`);

  if (options.length > 0) {
    // Find best match
    const match = options.find(o => o.text.toLowerCase().includes(searchText.toLowerCase())) || options[0];
    console.log(`    Selecting: "${match.text}"`);

    // Click the option
    await eval_(`
      const opt = Array.from(document.querySelectorAll('[class*="option"], [id*="option"], [role="option"]'))
        .filter(el => el.offsetParent !== null)
        .find(el => el.textContent.trim().includes(${JSON.stringify(match.text.substring(0, 30))}));
      if (opt) opt.click();
    `);
    await sleep(500);
    return match.text;
  }
  return null;
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Step 1: Fill gig title
  console.log("=== 1. Gig Title ===");
  const gigTitle = "do accurate data entry, Excel spreadsheet work and data processing";

  let r = await eval_(`
    const textarea = document.querySelector('textarea[placeholder*="do something"]');
    if (textarea) {
      textarea.focus();
      textarea.click();
      return 'found textarea';
    }
    return 'textarea not found';
  `);
  console.log(r);

  if (r.includes('found')) {
    // Clear and type
    await eval_(`
      const ta = document.querySelector('textarea[placeholder*="do something"]');
      if (ta) {
        ta.focus();
        ta.select();
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
      }
    `);
    await sleep(200);
    await send("Input.insertText", { text: gigTitle });
    await sleep(500);

    r = await eval_(`
      const ta = document.querySelector('textarea[placeholder*="do something"]');
      const hidden = document.querySelector('input[name="gig[title]"]');
      return JSON.stringify({
        textareaValue: ta?.value?.substring(0, 100),
        hiddenValue: hidden?.value?.substring(0, 100)
      });
    `);
    console.log("Title values:", r);
  }

  // Step 2: Select Category - "Data"
  console.log("\n=== 2. Category ===");
  const catResult = await typeInReactSelect(send, eval_, 'react-select-2-input', 'Data');
  console.log("Category selected:", catResult);
  await sleep(1000);

  // Step 3: Select Subcategory - try "Data Entry" or similar
  console.log("\n=== 3. Subcategory ===");
  // First check what subcategories are available
  r = await eval_(`
    const subInput = document.getElementById('react-select-3-input');
    if (subInput) {
      subInput.focus();
      subInput.click();
      return 'focused subcategory';
    }
    return 'subcategory input not found';
  `);
  console.log(r);
  await sleep(500);

  // Check dropdown options without typing
  r = await eval_(`
    const options = Array.from(document.querySelectorAll('[class*="option"], [id*="option"], [role="option"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 80));
    return JSON.stringify(options);
  `);
  console.log("Available subcategories:", r);

  const subResult = await typeInReactSelect(send, eval_, 'react-select-3-input', 'Data Entry');
  console.log("Subcategory selected:", subResult);
  await sleep(1000);

  // Step 4: Add Tags
  console.log("\n=== 4. Tags ===");
  const tags = ["data entry", "excel", "spreadsheet", "data processing", "typing"];

  for (const tag of tags) {
    console.log(`  Adding tag: "${tag}"`);

    // Find the tag input
    r = await eval_(`
      // The tag input is a plain text input (not react-select)
      const inputs = Array.from(document.querySelectorAll('input[type="text"]'))
        .filter(i => i.offsetParent !== null && !i.id.includes('react-select'));
      // It's likely the one near "Search tags" or "Positive keywords"
      for (const inp of inputs) {
        const parent = inp.closest('[class*="tag"], [class*="Tag"]') || inp.parentElement?.parentElement;
        const nearby = parent?.textContent || '';
        if (nearby.includes('tag') || nearby.includes('keyword') || nearby.includes('Tag')) {
          inp.focus();
          inp.click();
          return JSON.stringify({ found: true, placeholder: inp.placeholder });
        }
      }
      // Fallback: try the last non-react-select text input
      const fallback = inputs.filter(i => !i.id.includes('react-select')).pop();
      if (fallback) {
        fallback.focus();
        fallback.click();
        return JSON.stringify({ found: true, placeholder: fallback.placeholder, fallback: true });
      }
      return JSON.stringify({ found: false, inputCount: inputs.length });
    `);
    console.log(`    Input: ${r}`);

    const inputInfo = JSON.parse(r);
    if (inputInfo.found) {
      await send("Input.insertText", { text: tag });
      await sleep(300);

      // Check if there's a dropdown with suggestions
      r = await eval_(`
        const options = Array.from(document.querySelectorAll('[class*="option"], [role="option"], [class*="suggestion"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 50));
        return JSON.stringify(options);
      `);
      const tagOptions = JSON.parse(r);

      if (tagOptions.length > 0) {
        console.log(`    Suggestions: ${tagOptions.join(', ')}`);
        // Click the first matching option
        await eval_(`
          const opt = Array.from(document.querySelectorAll('[class*="option"], [role="option"], [class*="suggestion"]'))
            .filter(el => el.offsetParent !== null)[0];
          if (opt) opt.click();
        `);
      } else {
        // Press Enter to add the tag
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
      }
      await sleep(500);

      // Press comma or Enter to finalize
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: ",", code: "Comma" });
      await send("Input.dispatchKeyEvent", { type: "char", text: "," });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: ",", code: "Comma" });
      await sleep(300);
    }
  }

  // Check tags added
  r = await eval_(`
    const tagChips = Array.from(document.querySelectorAll('[class*="tag" i][class*="chip" i], [class*="Tag" i]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 30));
    const hiddenTags = document.querySelector('input[name="gig[tag_list]"]')?.value;
    return JSON.stringify({ chips: tagChips, hiddenValue: hiddenTags });
  `);
  console.log("Tags state:", r);

  // Step 5: Check form and click Save & Continue
  console.log("\n=== 5. Form Summary ===");
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      textareaVal: document.querySelector('textarea')?.value?.substring(0, 100) || ''
    });
  `);
  console.log(r);

  // Click Save & Continue
  console.log("\n=== 6. Save & Continue ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Save & Continue') || b.textContent.trim().includes('Save &amp; Continue'));
    if (btn && !btn.disabled) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim(), disabled: btn.disabled });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    console.log(`Clicking "${pos.text}"...`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(5000);

    // Check result
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 2000),
        errors: Array.from(document.querySelectorAll('[class*="error" i], [class*="Error" i], [role="alert"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 100))
          .filter(t => t.length > 3)
      });
    `);
    console.log("After save:", r);
  } else {
    console.log("Save & Continue button not found or disabled");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
