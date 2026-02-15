// Gallery upload - click placeholder to trigger file dialog
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  const events = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
    if (msg.method) {
      events.push(msg);
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
  return { ws, send, eval_, events };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  // Reload the page first
  let { ws, send, eval_, events } = await connectToPage("manage_gigs");
  console.log("Connected");

  // Reload to get fresh state
  await eval_(`location.reload()`);
  await sleep(5000);
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_, events } = await connectToPage("manage_gigs"));
  console.log("Reconnected after reload\n");

  await send("DOM.enable");
  await send("Page.enable");
  await send("Page.setInterceptFileChooserDialog", { enabled: true });

  // Find all file inputs
  let r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input[type="file"]'));
    return JSON.stringify(inputs.map((el, i) => ({
      idx: i,
      id: el.id,
      parentClass: el.closest('.gallery-section')?.className || '',
    })));
  `);
  console.log("File inputs:", r);

  // Find portfolio section placeholder
  r = await eval_(`
    const portfolio = document.querySelector('.portfolio-section');
    if (!portfolio) return JSON.stringify({ error: 'no portfolio' });
    const ph = portfolio.querySelector('.gallery-item-placeholder');
    if (!ph) return JSON.stringify({ error: 'no placeholder' });
    ph.scrollIntoView({ block: 'center' });
    const rect = ph.getBoundingClientRect();
    return JSON.stringify({
      x: Math.round(rect.x + rect.width/2),
      y: Math.round(rect.y + rect.height/2),
      w: Math.round(rect.width),
      h: Math.round(rect.height),
      text: ph.textContent.trim().substring(0, 50)
    });
  `);
  console.log("Placeholder:", r);
  const ph = JSON.parse(r);

  if (ph.error) {
    console.log("ERROR:", ph.error);
    ws.close();
    return;
  }

  // Wait for file chooser event
  function waitForFileChooser(timeoutMs = 5000) {
    return new Promise((resolve) => {
      const startLen = events.length;
      const check = setInterval(() => {
        for (let i = startLen; i < events.length; i++) {
          if (events[i].method === 'Page.fileChooserOpened') {
            clearInterval(check);
            resolve(events[i]);
            return;
          }
        }
      }, 100);
      setTimeout(() => { clearInterval(check); resolve(null); }, timeoutMs);
    });
  }

  // Try 1: Click on the placeholder
  console.log(`\nClicking placeholder at (${ph.x}, ${ph.y})...`);
  const fc1Promise = waitForFileChooser(5000);
  await clickAt(send, ph.x, ph.y);
  let fc = await fc1Promise;

  if (!fc) {
    console.log("No file chooser from placeholder click.");

    // Try 2: Click the "Drag & drop" or "Browse" text area
    r = await eval_(`
      const portfolio = document.querySelector('.portfolio-section');
      const spans = Array.from(portfolio.querySelectorAll('span, a, b, strong'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length < 40)
        .map(el => ({
          text: el.textContent.trim(),
          tag: el.tagName,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(spans);
    `);
    console.log("Spans in portfolio:", r);
    const spans = JSON.parse(r);
    const browseSpan = spans.find(s => s.text === 'Browse' || s.text.includes('Browse'));

    if (browseSpan) {
      console.log(`Clicking Browse span at (${browseSpan.x}, ${browseSpan.y})...`);
      const fc2Promise = waitForFileChooser(5000);
      await clickAt(send, browseSpan.x, browseSpan.y);
      fc = await fc2Promise;
    }
  }

  if (!fc) {
    console.log("No file chooser from Browse click either.");

    // Try 3: Use JS to click the file input
    r = await eval_(`
      const fileInput = document.querySelector('.portfolio-section input[type="file"]');
      if (fileInput) return fileInput.id || 'no-id';
      return 'not found';
    `);
    console.log("Portfolio file input id:", r);

    if (r !== 'not found') {
      console.log("Clicking file input via JS...");
      const fc3Promise = waitForFileChooser(5000);
      await eval_(`
        const fi = document.querySelector('.portfolio-section input[type="file"]');
        if (fi) fi.click();
        return 'clicked';
      `);
      fc = await fc3Promise;
    }
  }

  if (!fc) {
    console.log("No file chooser from any method.");
    // Last resort: use DOM.setFileInputFiles directly
    console.log("\nTrying DOM.setFileInputFiles as last resort...");
    const docResult = await send("DOM.getDocument", { depth: 0 });
    const rootNodeId = docResult.root.nodeId;

    const node = await send("DOM.querySelector", {
      nodeId: rootNodeId,
      selector: '.portfolio-section input[type="file"]'
    });
    console.log("Node ID:", node.nodeId);

    if (node.nodeId > 0) {
      await send("DOM.setFileInputFiles", {
        nodeId: node.nodeId,
        files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
      });
      console.log("File set directly");
      await sleep(5000);
    }
  } else {
    console.log("File chooser opened! Accepting file...");
    await send("Page.handleFileChooser", {
      action: "accept",
      files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
    });
    console.log("File accepted!");
    await sleep(8000);
  }

  // Check result
  r = await eval_(`
    const portfolio = document.querySelector('.portfolio-section');
    const allImgs = portfolio ? Array.from(portfolio.querySelectorAll('img'))
      .filter(el => el.src && el.src.length > 10)
      .map(el => ({ src: el.src.substring(0, 100), w: el.offsetWidth })) : [];
    const items = portfolio ? Array.from(portfolio.querySelectorAll('.gallery-item-placeholder'))
      .map(el => ({
        class: el.className.substring(0, 60),
        hasImg: !!el.querySelector('img[src]'),
        bg: el.style?.backgroundImage?.substring(0, 80) || ''
      })) : [];
    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify({ allImgs, items, errors });
  `);
  console.log("\nResult:", r);

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error) {
    await sleep(500);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(10000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors
      });
    `);
    console.log("After save:", r);

    const state = JSON.parse(r);
    if (state.wizard === '4' && state.errors.length === 0) {
      await eval_(`window.location.href = location.href.replace(/wizard=4/, 'wizard=5').replace(/&tab=\\w+/, '')`);
      await sleep(5000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
      r = await eval_(`return JSON.stringify({ url: location.href, wizard: new URL(location.href).searchParams.get('wizard') })`);
      console.log("Navigated:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
