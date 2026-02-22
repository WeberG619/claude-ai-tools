// Gallery upload - fresh reload then upload to #image only
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
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Reload page to clear any stale errors
  console.log("Reloading page...");
  await eval_(`location.reload()`);
  await sleep(5000);
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
  console.log("Reconnected after reload");

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard')
    });
  `);
  console.log("State:", r);
  await sleep(2000);

  // Enable DOM
  await send("DOM.enable");

  // Find the exact gallery structure
  r = await eval_(`
    const sections = Array.from(document.querySelectorAll('.gallery-section'));
    return JSON.stringify(sections.map(s => ({
      class: s.className,
      label: s.querySelector('label, h4, .section-title')?.textContent?.trim()?.substring(0, 40) || '',
      fileInput: s.querySelector('input[type="file"]')?.id || 'none',
      placeholders: s.querySelectorAll('.gallery-item-placeholder').length
    })));
  `);
  console.log("Gallery sections:", r);

  // Get document for DOM operations
  const docResult = await send("DOM.getDocument", { depth: 0 });
  const rootNodeId = docResult.root.nodeId;

  // Upload to #image input
  console.log("\n=== Uploading image ===");
  const imgInput = await send("DOM.querySelector", {
    nodeId: rootNodeId,
    selector: '#image'
  });
  console.log("Image input nodeId:", imgInput.nodeId);

  if (imgInput.nodeId > 0) {
    await send("DOM.setFileInputFiles", {
      nodeId: imgInput.nodeId,
      files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
    });
    console.log("File dispatched to #image");

    // Wait for upload processing
    for (let i = 0; i < 10; i++) {
      await sleep(2000);
      r = await eval_(`
        const errors = Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
          .map(el => el.textContent.trim().substring(0, 100));
        const uploadedItems = Array.from(document.querySelectorAll('.gallery-item-placeholder'))
          .filter(el => el.querySelector('img') || el.classList.contains('black-border'))
          .map(el => ({
            class: el.className.substring(0, 60),
            hasImg: !!el.querySelector('img'),
            imgSrc: el.querySelector('img')?.src?.substring(0, 80) || ''
          }));
        const progress = document.querySelector('[class*="progress"], [class*="uploading"]');
        return JSON.stringify({ errors, uploadedItems, hasProgress: !!progress, tick: ${i} });
      `);
      console.log(`  Check ${i}:`, r);
      const check = JSON.parse(r);
      if (check.errors.length === 0 && check.uploadedItems.some(item => item.hasImg)) break;
      if (check.errors.length > 0) break;
    }
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise(r => setTimeout(r, 500));
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error) {
    console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
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
      console.log("Navigating to wizard=5...");
      await eval_(`window.location.href = location.href.replace(/wizard=4/, 'wizard=5').replace(/&tab=\\w+/, '')`);
      await sleep(5000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
      r = await eval_(`return JSON.stringify({ url: location.href, wizard: new URL(location.href).searchParams.get('wizard') })`);
      console.log("Nav to wizard=5:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
