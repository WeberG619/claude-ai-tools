// Fix headline on Freelancer profile - clear properly and enter short text
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

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com");
  console.log("Connected\n");

  // Step 1: Clear headline using DOM + Angular ngModel approach
  console.log("Clearing headline...");
  let r = await eval_(`
    const input = document.getElementById('inputHeadline');
    if (!input) return 'not found';

    // Get Angular ref and use setValue
    const ngModel = input.__ngContext__ || input.ng;

    // Clear via native input setter (bypasses Angular's value tracking)
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeInputValueSetter.call(input, '');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));

    return 'cleared, value: "' + input.value + '"';
  `);
  console.log("  ", r);
  await sleep(300);

  // Focus and use keyboard to type
  await eval_(`
    const input = document.getElementById('inputHeadline');
    input.focus();
    input.click();
    return 'focused';
  `);
  await sleep(200);

  // Triple-click to select all text in the field
  r = await eval_(`
    const input = document.getElementById('inputHeadline');
    const rect = input.getBoundingClientRect();
    return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
  `);
  const headlinePos = JSON.parse(r);

  // Triple click to select all
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: headlinePos.x, y: headlinePos.y, button: "left", clickCount: 3 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: headlinePos.x, y: headlinePos.y, button: "left", clickCount: 3 });
  await sleep(200);

  // Delete selected text
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(200);

  // Check it's clear
  r = await eval_(`
    return document.getElementById('inputHeadline').value;
  `);
  console.log("  After clear:", JSON.stringify(r));

  // Now type headline using insertText
  const headline = "Writer & Data Specialist | AI Tools";  // 35 chars
  console.log(`\nTyping headline (${headline.length} chars): "${headline}"`);
  await send("Input.insertText", { text: headline });
  await sleep(300);

  r = await eval_(`
    return document.getElementById('inputHeadline').value;
  `);
  console.log("  Headline value:", JSON.stringify(r));
  console.log("  Length:", r.length);

  // Step 2: Now fill the summary textarea
  console.log("\nFilling summary...");

  // Focus summary textarea
  r = await eval_(`
    const ta = document.getElementById('inputSummary');
    const rect = ta.getBoundingClientRect();
    return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
  `);
  const summaryPos = JSON.parse(r);

  // Triple click to select all in textarea
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x: summaryPos.x, y: summaryPos.y, button: "left", clickCount: 3 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: summaryPos.x, y: summaryPos.y, button: "left", clickCount: 3 });
  await sleep(200);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(200);

  // Also Ctrl+A + Delete for good measure
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(200);

  const summary = `Professional writer and data specialist delivering high-quality content and accurate data processing. I use AI-enhanced tools alongside my expertise for fast, precise results.

Services I offer:
- Article writing, blog posts, and content creation
- Technical writing and documentation
- Research reports and analysis
- Data entry, processing, and Excel spreadsheets
- Copywriting, editing, and proofreading
- Resume writing and LinkedIn profile optimization

I combine traditional skills with modern AI-powered workflows to deliver work faster while maintaining exceptional quality.`;

  await send("Input.insertText", { text: summary });
  await sleep(500);

  r = await eval_(`
    const ta = document.getElementById('inputSummary');
    return ta ? 'Length: ' + ta.value.length : 'not found';
  `);
  console.log("  Summary:", r);

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

  await sleep(5000);

  // Check result
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\n=== Result ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
