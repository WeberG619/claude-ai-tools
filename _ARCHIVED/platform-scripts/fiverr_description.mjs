// Fill Fiverr Description & FAQ (Step 3) and save
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Check current page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
      bodyPreview: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("Current page:", r);

  // Inspect the description page form
  console.log("\n=== Form Inspection ===");
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, textarea, select, [contenteditable]'))
      .filter(el => el.offsetParent !== null || el.type === 'hidden')
      .map(el => ({
        tag: el.tagName,
        type: el.type || (el.getAttribute('contenteditable') ? 'contenteditable' : ''),
        name: el.name || '',
        id: el.id || '',
        placeholder: (el.placeholder || '').substring(0, 50),
        value: (el.value || el.textContent || '').substring(0, 60),
        class: (el.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height),
        visible: el.offsetParent !== null
      }));
    return JSON.stringify(inputs.filter(i => i.visible || i.name.includes('description')));
  `);
  console.log(r);

  // Fill the description
  console.log("\n=== Filling Description ===");
  const description = `Are you looking for accurate and reliable data entry services? You've come to the right place!

I provide professional data entry and Excel spreadsheet services with a focus on accuracy and quick turnaround.

What I offer:
- Data entry from any source (PDF, images, handwritten documents, websites)
- Excel spreadsheet creation, formatting, and data organization
- Data cleaning, deduplication, and validation
- Copy-paste work with 99.9% accuracy
- Converting data between formats (PDF to Excel, Word to Excel, etc.)
- Data processing and analysis

Why choose me:
- Fast and accurate work
- Attention to detail
- Quick communication and updates
- Revisions until you're satisfied

Simply send me your data or documents, and I'll handle the rest. Contact me before ordering for custom requirements!`;

  // Find the description textarea/editor
  r = await eval_(`
    // Look for the main description editor
    const textarea = document.querySelector('textarea[name*="description"]') ||
      document.querySelector('.description-wrapper textarea') ||
      Array.from(document.querySelectorAll('textarea'))
        .filter(t => t.offsetParent !== null)
        .find(t => t.getBoundingClientRect().height > 100);

    if (textarea) {
      textarea.scrollIntoView({ block: 'center' });
      textarea.focus();
      return JSON.stringify({
        found: 'textarea',
        tag: textarea.tagName,
        name: textarea.name || '',
        class: (textarea.className?.toString() || '').substring(0, 60),
        h: Math.round(textarea.getBoundingClientRect().height)
      });
    }

    // Look for contenteditable div
    const editableDiv = document.querySelector('[contenteditable="true"]');
    if (editableDiv) {
      editableDiv.scrollIntoView({ block: 'center' });
      editableDiv.focus();
      return JSON.stringify({
        found: 'contenteditable',
        tag: editableDiv.tagName,
        class: (editableDiv.className?.toString() || '').substring(0, 60)
      });
    }

    return JSON.stringify({ found: 'none' });
  `);
  console.log("Description editor:", r);

  const editorInfo = JSON.parse(r);

  if (editorInfo.found === 'textarea') {
    // Focus and type into textarea
    await eval_(`
      const textarea = document.querySelector('textarea[name*="description"]') ||
        Array.from(document.querySelectorAll('textarea'))
          .filter(t => t.offsetParent !== null)
          .find(t => t.getBoundingClientRect().height > 100);
      if (textarea) {
        textarea.focus();
        textarea.click();
      }
    `);
    await sleep(300);

    // Select all and delete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
    await sleep(100);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(200);

    // Type the description
    await send("Input.insertText", { text: description });
    await sleep(500);

    // Verify
    r = await eval_(`
      const textarea = document.querySelector('textarea[name*="description"]') ||
        Array.from(document.querySelectorAll('textarea'))
          .filter(t => t.offsetParent !== null)
          .find(t => t.getBoundingClientRect().height > 100);
      return (textarea?.value || '').substring(0, 100);
    `);
    console.log("Description set:", r);
  } else if (editorInfo.found === 'contenteditable') {
    // Type into contenteditable
    await send("Input.insertText", { text: description });
    await sleep(500);
  }

  // Check character count
  r = await eval_(`
    const charCount = document.querySelector('[class*="char-count"], [class*="character"]');
    const descValue = document.querySelector('input[name="gig[description]"]')?.value?.length ||
      document.querySelector('textarea')?.value?.length || 0;
    return JSON.stringify({
      charCountText: charCount?.textContent?.trim() || '',
      descLength: descValue
    });
  `);
  console.log("Char count:", r);

  // Check for FAQ section
  console.log("\n=== FAQ Section ===");
  r = await eval_(`
    const faqArea = document.body?.innerText?.includes('Frequently Asked Questions') ||
                    document.body?.innerText?.includes('FAQ');
    const addFaqBtn = Array.from(document.querySelectorAll('button, a'))
      .filter(el => el.offsetParent !== null)
      .find(el => el.textContent.includes('Add FAQ') || el.textContent.includes('Add a FAQ'));

    return JSON.stringify({
      hasFaqSection: faqArea,
      addFaqBtn: addFaqBtn ? {
        text: addFaqBtn.textContent.trim().substring(0, 30),
        x: Math.round(addFaqBtn.getBoundingClientRect().x + addFaqBtn.getBoundingClientRect().width/2),
        y: Math.round(addFaqBtn.getBoundingClientRect().y + addFaqBtn.getBoundingClientRect().height/2)
      } : null
    });
  `);
  console.log(r);

  // FAQ is optional - skip it for now and save

  // Click Save & Continue
  console.log("\n=== Saving ===");
  r = await eval_(`
    const btn = document.querySelector('.btn-submit') ||
      Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Save & Continue'));
    if (btn) { btn.scrollIntoView({ block: 'center' }); btn.click(); }
    return btn ? 'clicked' : 'not found';
  `);
  console.log("Save:", r);
  await sleep(5000);

  // Check result
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim() || '',
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="validation"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 100)),
      bodyPreview: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("After save:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
