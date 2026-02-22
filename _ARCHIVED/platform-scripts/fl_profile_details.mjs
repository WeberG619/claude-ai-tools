// Fill Freelancer profile details (headline + summary) using CDP keyboard events
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
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

async function typeText(send, eval_, selector, text) {
  // Focus the element
  await eval_(`
    const el = document.querySelector(${JSON.stringify(selector)});
    if (el) { el.focus(); el.click(); }
    return el ? 'focused' : 'not found';
  `);
  await sleep(200);

  // Clear existing content with select all + delete
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 }); // Ctrl+A
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);

  // Type each character using insertText (works with Angular reactive forms)
  for (const char of text) {
    await send("Input.dispatchKeyEvent", {
      type: "keyDown",
      key: char,
      text: char
    });
    await send("Input.dispatchKeyEvent", {
      type: "char",
      text: char
    });
    await send("Input.dispatchKeyEvent", {
      type: "keyUp",
      key: char
    });
    await sleep(15);
  }
  await sleep(200);

  // Verify
  const val = await eval_(`
    const el = document.querySelector(${JSON.stringify(selector)});
    return el ? el.value || el.textContent : 'not found';
  `);
  return val;
}

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com");
  console.log("Connected\n");

  // Check current page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      inputs: Array.from(document.querySelectorAll('input, textarea')).map(i => ({
        tag: i.tagName, type: i.type, placeholder: i.placeholder,
        id: i.id, name: i.name, maxLength: i.maxLength,
        selector: i.tagName.toLowerCase() + (i.type ? '[type="'+i.type+'"]' : '') + (i.placeholder ? '[placeholder*="'+i.placeholder.substring(0,10)+'"]' : '')
      }))
    });
  `);
  console.log("Page:", r);

  // Step 1: Fill headline ("What do you do?" - max 50 chars)
  const headline = "Writer & Data Specialist | AI-Powered";  // 37 chars
  console.log(`\nFilling headline (${headline.length} chars): "${headline}"`);

  // Find the headline input
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'));
    const headlineInput = inputs.find(i => i.offsetParent !== null);
    if (headlineInput) {
      return JSON.stringify({
        found: true,
        tag: headlineInput.tagName,
        type: headlineInput.type,
        placeholder: headlineInput.placeholder,
        id: headlineInput.id,
        value: headlineInput.value
      });
    }
    return JSON.stringify({ found: false });
  `);
  console.log("  Headline input:", r);

  // Type into headline using insertText method (best for Angular)
  await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'));
    const headlineInput = inputs.find(i => i.offsetParent !== null);
    if (headlineInput) { headlineInput.focus(); headlineInput.click(); }
    return 'focused';
  `);
  await sleep(200);

  // Select all and delete first
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);

  // Use insertText for the whole string at once (Angular picks this up)
  await send("Input.insertText", { text: headline });
  await sleep(500);

  // Verify headline
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input'));
    const headlineInput = inputs.find(i => i.offsetParent !== null);
    return headlineInput ? headlineInput.value : 'not found';
  `);
  console.log("  Headline value:", r);

  // Step 2: Fill description/summary (textarea)
  const summary = `Professional writer and data specialist with a focus on delivering high-quality content and accurate data processing. I leverage AI-enhanced tools alongside my expertise to provide fast, precise results.

Services I offer:
- Article writing, blog posts, and content creation
- Technical writing and documentation
- Research reports and analysis
- Data entry, processing, and Excel spreadsheets
- Copywriting, editing, and proofreading
- Resume writing and LinkedIn profile optimization

I combine traditional skills with modern AI-powered workflows to deliver work faster while maintaining exceptional quality. Clear communication and meeting deadlines are my top priorities.`;

  console.log(`\nFilling summary (${summary.length} chars)...`);

  // Focus the textarea
  await eval_(`
    const ta = document.querySelector('textarea');
    if (ta) { ta.focus(); ta.click(); }
    return ta ? 'focused textarea' : 'textarea not found';
  `);
  await sleep(200);

  // Clear and type
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);

  await send("Input.insertText", { text: summary });
  await sleep(500);

  // Verify summary
  r = await eval_(`
    const ta = document.querySelector('textarea');
    return ta ? 'Summary length: ' + ta.value.length + ' chars' : 'textarea not found';
  `);
  console.log("  ", r);

  // Step 3: Click Next
  console.log("\nClicking Next...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("  Clicked Next");
  }

  await sleep(4000);

  // Check new page
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\nNew page:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
